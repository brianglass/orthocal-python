"""One-time LLM segmentation pass over antiochian.org fixed-menaion data.

This is stage 2 of the antiochian.org ingestion project (stage 1:
ingest_antiochian.py harvests raw JSON over a 412-day Paschal-cycle window).
This stage:

  1. Loads the harvested raw JSON, deduplicating to one record per calendar
     (month, day) -- the fixed-menaion content doesn't depend on which
     year's data we happened to sample.
  2. Sends each (month, day)'s raw `feastDayDescription` through Claude to
     (a) identify and strip any leading Paschal-cycle/moveable label (a
     Sunday designation, a Triodion/Pentecostarion day name -- incidental
     to whichever year we harvested from, not real menaion content for
     that date), and (b) split the remaining comma-separated text into
     individual saint/commemoration entries.
  3. Segmentation is hard to do with a regex: individual saints' own titles
     routinely contain internal commas ("Proterios, Archbishop of
     Alexandria"), and group commemorations embed name-lists with their
     own commas ("5 Nuns beheaded in Persia: Thecla, Mariamne, ..."). Every
     few-shot example below is a real string pulled from a cached
     antiochian.org response during development, with a manually verified
     correct split.

Meant to run ONCE against the full harvested dataset (~366 unique calendar
dates) with the output saved permanently -- not re-run on every ingestion
cycle. Uses the Batches API (50% cheaper, no latency requirement since this
is fully offline batch work).
"""

import glob
import json
from pathlib import Path

import anthropic

CACHE_DIR = Path(__file__).parent / 'data' / 'antiochian_raw'
OUTPUT_PATH = Path(__file__).parent / 'data' / 'antiochian_fixed_saints.json'
BATCH_ID_PATH = Path(__file__).parent / 'data' / 'antiochian_segmentation_batch_id.txt'

MODEL = 'claude-opus-4-8'

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "moveable_designation": {
            "type": "string",
            "description": (
                "The Paschal-cycle/moveable label this description begins with "
                "(a Sunday designation, a Triodion or Pentecostarion day name, "
                "e.g. 'Cheesefare Monday', '6th Sunday of Luke', 'Holy Ascension'), "
                "exactly as written but with normal capitalization. Empty string "
                "if the description has no such label (either it's an ordinary "
                "weekday with no leading label at all, or the leading item is "
                "itself a fixed-calendar feast like the Annunciation or Dormition, "
                "not a moveable one)."
            ),
        },
        "fixed_commemorations": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "The individual fixed-menaion commemorations for this calendar "
                "date, with moveable_designation (if any) removed. Each array "
                "element is one commemoration, exactly as it appears in the "
                "source text -- including any internal commas that are part of "
                "that commemoration's own name/title/epithet or an internal "
                "name-list. Do not drop, merge, or reword any commemoration."
            ),
        },
    },
    "required": ["moveable_designation", "fixed_commemorations"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """You are helping ingest data from the antiochian.org liturgical calendar API into a database of fixed-menaion commemorations (saints and feasts assigned to a specific calendar month/day, independent of the movable Paschal cycle).

Each request gives you one day's raw feastDayTitle and feastDayDescription from that API. Your job:

1. Determine whether feastDayDescription begins with a Paschal-cycle/moveable label -- a Sunday designation ("6th Sunday of Luke", "2nd Tuesday after Pentecost"), or a named Triodion/Pentecostarion day ("Cheesefare Monday", "Forgiveness Sunday", "Lazarus Saturday", "Holy Friday", "Holy Ascension", "Renewal Tuesday", "Clean Monday", etc). If so, extract it as moveable_designation and remove it from the commemoration list. If the description has no such label -- either because it's a plain weekday with nothing prepended, or because the leading item is itself a FIXED feast (e.g. "Annunciation of the Theotokos", "The Dormition of our Most Holy Lady...") rather than a moveable one -- set moveable_designation to an empty string and keep the fixed feast (if any) in the commemoration list.

2. Split the remaining text into individual commemorations. THE TEXT IS COMMA-SEPARATED, BUT COMMAS ARE AMBIGUOUS: a comma can separate two different commemorations, OR it can be internal punctuation within a single commemoration's own name (a title/office like ", Archbishop of X" or ", Bishop of Y" following a saint's name, a kinship phrase like ", sister of Z", or a colon-introduced list of names belonging to one group commemoration like "5 Nuns beheaded in Persia: Thecla, Mariamne, Martha, Mary, & Enmatha"). Do not naively split on every comma -- read each candidate split point and decide whether it starts a genuinely new commemoration or continues the previous one.

Below are real examples, each with a manually verified correct answer.

--- Example 1 ---
feastDayTitle: FRIDAY OF THE 2ND WEEK
feastDayDescription: The Holy Hieromartyr Cyprian and the Virgin Martyr Justina, Theophilus the Confessor
Output: {"moveable_designation": "", "fixed_commemorations": ["The Holy Hieromartyr Cyprian and the Virgin Martyr Justina", "Theophilus the Confessor"]}

--- Example 2 ---
feastDayTitle: 6TH SUNDAY OF LUKE
feastDayDescription: 6th Sunday of Luke, The Holy Great Martyr Demetrius the Myrrh-streamer, Commemoration of the Great Earthquake in Constantinople (740), Eata of Hexham
Output: {"moveable_designation": "6th Sunday of Luke", "fixed_commemorations": ["The Holy Great Martyr Demetrius the Myrrh-streamer", "Commemoration of the Great Earthquake in Constantinople (740)", "Eata of Hexham"]}

--- Example 3 (comma-ambiguity: a title/office following a name is NOT a new entry; note the label isn't echoed in the description at all here, so nothing is stripped) ---
feastDayTitle: FIRST MONDAY OF LENT - CLEAN MONDAY
feastDayDescription: Polycarp the Holy Martyr & Bishop of Smyrna, Proterios, Archbishop of Alexandria, Gorgonia the Righteous, sister of Gregory the Theologian, Damian the New Martyr of Mount Athos, Boswell, Abbot of Melrose Abbey, John the Harvester of Calabria
Output: {"moveable_designation": "", "fixed_commemorations": ["Polycarp the Holy Martyr & Bishop of Smyrna", "Proterios, Archbishop of Alexandria", "Gorgonia the Righteous, sister of Gregory the Theologian", "Damian the New Martyr of Mount Athos", "Boswell, Abbot of Melrose Abbey", "John the Harvester of Calabria"]}

--- Example 4 (comma-ambiguity: a colon-introduced internal name-list is NOT multiple entries; again the label isn't echoed, so moveable_designation is empty) ---
feastDayTitle: 2ND TUESDAY AFTER PENTECOST
feastDayDescription: Cyril, Patriarch of Alexandria, 3 Virgin-martyrs of Chios, 5 Nuns beheaded in Persia: Thecla, Mariamne, Martha, Mary, & Enmatha, Righteous Father Columba of Iona, Righteous Father Cyril of Belozersk
Output: {"moveable_designation": "", "fixed_commemorations": ["Cyril, Patriarch of Alexandria", "3 Virgin-martyrs of Chios", "5 Nuns beheaded in Persia: Thecla, Mariamne, Martha, Mary, & Enmatha", "Righteous Father Columba of Iona", "Righteous Father Cyril of Belozersk"]}

--- Example 5 (a FIXED feast, not moveable -- nothing to strip) ---
feastDayTitle: THE DORMITION OF OUR MOST HOLY LADY THE THEOTOKOS AND EVER VIRGIN MARY
feastDayDescription: The Dormition of our Most Holy Lady the Theotokos and Ever Virgin Mary
Output: {"moveable_designation": "", "fixed_commemorations": ["The Dormition of our Most Holy Lady the Theotokos and Ever Virgin Mary"]}

--- Example 6 (a FIXED feast landing during Lent is still not moveable) ---
feastDayTitle: ANNUNCIATION OF THE THEOTOKOS
feastDayDescription: Annunciation of the Theotokos
Output: {"moveable_designation": "", "fixed_commemorations": ["Annunciation of the Theotokos"]}

Respond with only the JSON object matching the schema -- no other text."""


def _user_message(title, description):
    return f'feastDayTitle: {title}\nfeastDayDescription: {description}'


def load_unique_calendar_days(preferred_year=None):
    """Load cached raw JSON and dedupe to one record per (month, day).

    The fixed-menaion axis doesn't depend on which year we sampled, so any
    occurrence works; prefer `preferred_year` when a (month, day) appears
    more than once (it will, since the harvested window is ~412 days).
    """

    by_key = {}
    for path in sorted(glob.glob(str(CACHE_DIR / '*.json'))):
        day = json.loads(Path(path).read_text())
        dt = day['originalCalendarDate']  # 'YYYY-MM-DD'
        year, month, date_ = (int(p) for p in dt.split('-'))
        key = (month, date_)

        if key not in by_key or (preferred_year and year == preferred_year):
            by_key[key] = day

    return by_key


def build_batch_requests(days_by_key):
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request

    requests = []
    for (month, date_), day in days_by_key.items():
        custom_id = f'{month:02d}-{date_:02d}'
        requests.append(Request(
            custom_id=custom_id,
            params=MessageCreateParamsNonStreaming(
                model=MODEL,
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                messages=[{
                    'role': 'user',
                    'content': _user_message(day['feastDayTitle'], day['feastDayDescription']),
                }],
                output_config={'format': {'type': 'json_schema', 'schema': RESPONSE_SCHEMA}},
            ),
        ))

    return requests


def submit_batch():
    days_by_key = load_unique_calendar_days()
    requests = build_batch_requests(days_by_key)

    print(f'Submitting a batch of {len(requests)} unique calendar days...')

    client = anthropic.Anthropic()
    batch = client.messages.batches.create(requests=requests)

    BATCH_ID_PATH.write_text(batch.id)
    print(f'Batch created: {batch.id} (saved to {BATCH_ID_PATH})')
    print(f'Status: {batch.processing_status}')
    return batch.id


def collect_results(batch_id=None):
    batch_id = batch_id or BATCH_ID_PATH.read_text().strip()
    client = anthropic.Anthropic()

    batch = client.messages.batches.retrieve(batch_id)
    if batch.processing_status != 'ended':
        print(f'Batch {batch_id} is still {batch.processing_status}; not ready yet.')
        return

    results = {}
    errors = []
    for result in client.messages.batches.results(batch_id):
        if result.result.type == 'succeeded':
            msg = result.result.message
            text = next(b.text for b in msg.content if b.type == 'text')
            results[result.custom_id] = json.loads(text)
        else:
            errors.append((result.custom_id, result.result.type))

    OUTPUT_PATH.write_text(json.dumps(results, indent=2, sort_keys=True))
    print(f'Saved {len(results)} segmented days to {OUTPUT_PATH}')
    if errors:
        print(f'{len(errors)} failed: {errors}')


def selftest_against_known_examples():
    """Synchronous (non-batch) sanity check against the exact examples baked
    into the few-shot prompt, run BEFORE committing to the full batch. Costs
    a handful of live calls -- not part of the one-time bulk segmentation."""

    known = [
        ('FRIDAY OF THE 2ND WEEK',
         'The Holy Hieromartyr Cyprian and the Virgin Martyr Justina, Theophilus the Confessor'),
        ('6TH SUNDAY OF LUKE',
         '6th Sunday of Luke, The Holy Great Martyr Demetrius the Myrrh-streamer, '
         'Commemoration of the Great Earthquake in Constantinople (740), Eata of Hexham'),
        ('FIRST MONDAY OF LENT - CLEAN MONDAY',
         'Polycarp the Holy Martyr & Bishop of Smyrna, Proterios, Archbishop of Alexandria, '
         'Gorgonia the Righteous, sister of Gregory the Theologian, Damian the New Martyr of '
         'Mount Athos, Boswell, Abbot of Melrose Abbey, John the Harvester of Calabria'),
        ('2ND TUESDAY AFTER PENTECOST',
         'Cyril, Patriarch of Alexandria, 3 Virgin-martyrs of Chios, 5 Nuns beheaded in '
         'Persia: Thecla, Mariamne, Martha, Mary, & Enmatha, Righteous Father Columba of '
         'Iona, Righteous Father Cyril of Belozersk'),
    ]

    client = anthropic.Anthropic()
    for title, description in known:
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[{'role': 'user', 'content': _user_message(title, description)}],
            output_config={'format': {'type': 'json_schema', 'schema': RESPONSE_SCHEMA}},
        )
        text = next(b.text for b in response.content if b.type == 'text')
        parsed = json.loads(text)
        print(f'--- {title} ---')
        print(json.dumps(parsed, indent=2))
        print()


if __name__ == '__main__':
    import sys

    if '--test' in sys.argv:
        selftest_against_known_examples()
    elif '--submit' in sys.argv:
        submit_batch()
    elif '--collect' in sys.argv:
        collect_results()
    else:
        print('Usage: python3 ingest_antiochian_segment.py [--test|--submit|--collect]')
