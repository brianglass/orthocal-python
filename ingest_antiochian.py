"""Prototype ingestion client for the antiochian.org LiturgicalDay API.

This is exploratory tooling, not a production management command yet. It is
deliberately conservative about request volume: every request is separated by
a delay (default 2s), responses are cached to disk so re-runs don't re-hit the
API, and the __main__ block below only pulls a small, hand-picked set of dates
rather than walking a full year.

The main open research question this script is meant to help answer: does the
antiochian.org data distinguish paschal-cycle (moveable) commemorations from
fixed-calendar (menaion) ones, the way this project's own `models.Day` does
via `pdist` vs `month`/`day`? The API only exposes an absolute calendar date
per itemId, so as far as I can tell there's no explicit flag -- we can only
infer the split by cross-referencing dates where we already know (from our
own Paschalion math) whether interesting overlap occurs, e.g. Annunciation
landing inside Great Lent.
"""

import glob
import json
import re
import time
from datetime import date, timedelta
from enum import IntEnum
from pathlib import Path
from urllib.parse import urljoin

import requests

from bible import books as bible_books

CLIENT_ID = 'antiochian_api'
CLIENT_SECRET = 'TAxhx@9tH(l^MgQ9FWE8}T@NWUT9U)'
HOST = 'www.antiochian.org'

CACHE_DIR = Path(__file__).parent / 'data' / 'antiochian_raw'


class Antiochian(requests.Session):
    base_url = 'https://www.antiochian.org/'
    token_endpoint = urljoin(base_url, '/connect/token')
    liturgical_endpoint = urljoin(base_url, '/api/antiochian/LiturgicalDay/{}')

    def __init__(self, *args, delay=2.0, **kwargs):
        super().__init__(*args, **kwargs)
        self.headers['Host'] = HOST
        self.delay = delay
        self.id_anchor = None
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def authenticate(self):
        response = self.post(self.token_endpoint, data={
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'grant_type': 'client_credentials',
        })
        response.raise_for_status()
        token_data = response.json()
        self.headers['Authorization'] = f'Bearer {token_data["access_token"]}'

        # Anchor itemId 0 to today's date so we can compute item ids for
        # arbitrary dates without walking the sequence one day at a time.
        day = self._fetch_item(0)
        anchor_dt = date.fromisoformat(day['originalCalendarDate'])
        self.id_anchor = anchor_dt, day['itemId']

    def _cache_path(self, dt):
        return CACHE_DIR / f'{dt.isoformat()}.json'

    def _fetch_item(self, item_id):
        url = self.liturgical_endpoint.format(item_id)
        response = self.get(url)
        response.raise_for_status()
        time.sleep(self.delay)
        return response.json()['liturgicalDay']

    def get_liturgical_day(self, dt):
        """Fetch (and cache) the liturgical day for a given date.Date."""

        cache_path = self._cache_path(dt)
        if cache_path.exists():
            return json.loads(cache_path.read_text())

        if self.id_anchor is None:
            raise RuntimeError('Call authenticate() first')

        anchor_dt, anchor_id = self.id_anchor
        item_id = anchor_id + (dt - anchor_dt).days

        day = self._fetch_item(item_id)
        cache_path.write_text(json.dumps(day, indent=2))
        return day


def describe(day):
    return (
        f"{day['originalCalendarDate']}  {day['feastDayTitle']!r}\n"
        f"    fast: {day['fastDesignation']!r}\n"
        f"    desc: {day['feastDayDescription'][:160]!r}"
    )


class DietaryAllowance(IntEnum):
    """A clean, monotonic (strict -> fully free) dietary ladder.

    calendarium.datetools.FastExceptions mixes real dietary rungs with
    app-internal bookkeeping values (e.g. indices 1/3 and 2/4 are textually
    identical -- they're the same rung reached via different weekday-
    adjustment code paths in Day._apply_fasting_adjustments) and a couple of
    meta values that aren't dietary rungs at all (0 is a "no annotation"
    sentinel, 10 "No overrides" is a flag). This enum is the clean version:
    exactly one member per distinct dietary state, ordered by permissiveness.

    WineOilCaviar is Slavic-only (the Lazarus Saturday caviar exception) and
    is unreachable from parse_fast_designation, since antiochian.org's Greek
    tradition doesn't distinguish it from plain WineAndOil -- confirmed
    empirically: their Lazarus Saturday response omits caviar entirely.
    """

    Strict        = 0   # abstain from everything
    WineOnly      = 1   # wine allowed, no oil (e.g. Great and Holy Saturday)
    WineAndOil    = 2   # wine and oil allowed
    WineOilCaviar = 3   # + caviar; Slavic-only, see docstring
    FishWineOil   = 4   # fish, wine, and oil allowed
    MeatFast      = 5   # only meat excluded (e.g. Cheesefare week)
    FastFree      = 6   # everything allowed, including meat


# Maps a clean rung back onto calendarium.datetools.FastExceptions' existing
# indices, so parsed antiochian.org data can populate the current model
# field without any changes to Day._apply_fasting_adjustments or the
# FastExceptions tuple itself. Where FastExceptions has duplicate text at two
# indices (1/3, 2/4) the lower index is used as the canonical target.
DIETARY_ALLOWANCE_TO_FAST_EXCEPTION = {
    DietaryAllowance.Strict:        9,   # "Strict Fast"
    DietaryAllowance.WineOnly:      5,   # "Wine is Allowed"
    DietaryAllowance.WineAndOil:    1,   # "Wine and Oil are Allowed"
    DietaryAllowance.WineOilCaviar: 6,   # "Wine, Oil and Caviar are Allowed"
    DietaryAllowance.FishWineOil:   2,   # "Fish, Wine and Oil are Allowed"
    DietaryAllowance.MeatFast:      7,   # "Meat Fast"
    DietaryAllowance.FastFree:      11,  # "Fast Free"
}

# Normalizes the food-category tokens that appear after "ABSTAIN FROM" in an
# antiochian.org fastDesignation string.
_CATEGORY_ALIASES = {
    'MEAT': 'meat',
    'FISH': 'fish',
    'DAIRY': 'dairy',
    'EGGS': 'eggs',
    'WINE': 'wine',
    'OLIVE OIL': 'oil',
    'OIL': 'oil',
}

# Every exclusion set actually observed from the live API (see the
# conversation this script grew out of -- each entry below was fetched and
# verified against a real date, not guessed).
_EXCLUSION_SET_TO_RUNG = {
    frozenset():                                        DietaryAllowance.FastFree,
    frozenset({'meat'}):                                 DietaryAllowance.MeatFast,
    frozenset({'meat', 'dairy', 'eggs'}):                DietaryAllowance.FishWineOil,
    frozenset({'meat', 'fish', 'dairy', 'eggs'}):        DietaryAllowance.WineAndOil,
    frozenset({'meat', 'fish', 'dairy', 'eggs', 'oil'}): DietaryAllowance.WineOnly,
    frozenset({'meat', 'fish', 'dairy', 'eggs', 'wine', 'oil'}): DietaryAllowance.Strict,
}


def parse_fast_designation(text):
    """Parse an antiochian.org `fastDesignation` string into a DietaryAllowance.

    Raises ValueError on anything outside the vocabulary confirmed above,
    rather than guessing -- an unrecognized combination should surface loudly
    during ingestion so it can be checked against a real date, not silently
    mismapped.
    """

    text = text.strip().upper()

    if text == 'NO FAST':
        return DietaryAllowance.FastFree

    prefix = 'ABSTAIN FROM '
    if not text.startswith(prefix):
        raise ValueError(f'Unrecognized fast designation: {text!r}')

    try:
        excluded = frozenset(
            _CATEGORY_ALIASES[item.strip()]
            for item in text[len(prefix):].split(',')
        )
    except KeyError as e:
        raise ValueError(f'Unrecognized food category {e.args[0]!r} in {text!r}')

    try:
        return _EXCLUSION_SET_TO_RUNG[excluded]
    except KeyError:
        raise ValueError(f'Unrecognized exclusion combination {sorted(excluded)} (from {text!r})')


def fast_exception_for(fast_designation_text):
    """Parse straight through to the legacy FastExceptions index."""
    return DIETARY_ALLOWANCE_TO_FAST_EXCEPTION[parse_fast_designation(fast_designation_text)]


def selftest_parser():
    """Offline check against every phrase actually observed from the live API."""

    known = {
        'NO FAST':                                                     DietaryAllowance.FastFree,
        'ABSTAIN FROM MEAT':                                           DietaryAllowance.MeatFast,
        'ABSTAIN FROM MEAT, DAIRY, EGGS':                              DietaryAllowance.FishWineOil,
        'ABSTAIN FROM MEAT, FISH, DAIRY, EGGS':                        DietaryAllowance.WineAndOil,
        'ABSTAIN FROM MEAT, FISH, DAIRY, EGGS, OLIVE OIL':             DietaryAllowance.WineOnly,
        'ABSTAIN FROM MEAT, FISH, DAIRY, EGGS, WINE, OLIVE OIL':       DietaryAllowance.Strict,
    }

    for text, expected in known.items():
        actual = parse_fast_designation(text)
        assert actual == expected, f'{text!r}: expected {expected!r}, got {actual!r}'
        index = DIETARY_ALLOWANCE_TO_FAST_EXCEPTION[actual]
        print(f'OK  {text:55s} -> {actual.name:14s} (fast_exception={index})')

    print('All vocabulary self-checks passed.')


_ORDINAL_TO_DIGIT = {'FIRST': '1', 'SECOND': '2', 'THIRD': '3'}

_ACTS_RE = re.compile(r"^ACTS OF THE APOSTLES$")
# e.g. "ST. PAUL'S SECOND LETTER TO TIMOTHY", "ST. PAUL'S LETTER TO THE ROMANS"
_PAULINE_RE = re.compile(r"^ST\. PAUL'S(?: (FIRST|SECOND|THIRD))? LETTER TO(?: THE)? ([A-Z]+)$")
# e.g. "ST. JOHN'S THIRD UNIVERSAL LETTER", "ST. JUDE'S UNIVERSAL LETTER"
_CATHOLIC_RE = re.compile(r"^ST\. ([A-Z]+)'S(?: (FIRST|SECOND|THIRD))? UNIVERSAL LETTER$")

# The citation always starts with a bare chapter number followed by ':' or
# '.' -- this is what separates the book preamble from the range itself.
_CITATION_SPLIT_RE = re.compile(r'^(.*?)\s+(\d+[:.].*)$')


def _normalize_book_preamble(preamble):
    """Reduce an antiochian.org book preamble to a name bible.books.normalize_book_name
    recognizes. Most readings (Genesis, Isaiah, Matthew, Luke, John, ...) are
    already bare book names and pass through untouched; only the verbose
    liturgical epistle preambles need translating."""

    preamble = preamble.strip()

    if _ACTS_RE.match(preamble):
        return 'Acts'

    if m := _PAULINE_RE.match(preamble):
        ordinal, book = m.groups()
        return f'{_ORDINAL_TO_DIGIT[ordinal]} {book.title()}' if ordinal else book.title()

    if m := _CATHOLIC_RE.match(preamble):
        book, ordinal = m.groups()
        return f'{_ORDINAL_TO_DIGIT[ordinal]} {book.title()}' if ordinal else book.title()

    return preamble.title()


def parse_reading_citation(title):
    """Convert an antiochian.org reading title into a reference string that
    bible.models.Verse.objects.lookup_reference already knows how to parse.

    lookup_reference (see bible/models.py's ref_re and range_re) already
    handles everything on the *range* side that shows up in this data:
    cross-chapter ranges ("10:31-11:12"), ';'-separated multiple passages
    ("15:17-27; 16:1-2"), and ','-separated same-chapter verse lists that
    inherit the preceding chapter ("26:1, 12-20"). The only real gap is
    antiochian.org's verbose liturgical book preambles (e.g. "ST. PAUL'S
    SECOND LETTER TO TIMOTHY", "ACTS OF THE APOSTLES"), which this function
    normalizes down to a plain book name before handing the whole string to
    lookup_reference unchanged.

    Raises ValueError -- rather than guessing -- for anything that doesn't
    match the citation shape or resolve to a known book, so an unrecognized
    format surfaces during ingestion instead of silently mismapping.
    """

    title = ' '.join(title.split())
    m = _CITATION_SPLIT_RE.match(title)
    if not m:
        raise ValueError(f'No chapter:verse citation found in {title!r}')

    preamble, citation = m.groups()
    book = _normalize_book_preamble(preamble)

    if not bible_books.normalize_book_name(book):
        raise ValueError(f'Unrecognized book {preamble!r} (from {title!r})')

    return f'{book} {citation}'


def selftest_reading_citations():
    """Offline check against every reading title actually observed from the
    live API and cached under data/antiochian_raw/."""

    cache_dir = Path(__file__).parent / 'data' / 'antiochian_raw'
    titles = []
    for path in sorted(glob.glob(str(cache_dir / '*.json'))):
        day = json.loads(Path(path).read_text())
        for n in (1, 2, 3):
            if title := day.get(f'reading{n}Title'):
                titles.append(title)

    if not titles:
        print('No cached antiochian_raw/*.json files found -- nothing to check. '
              'Run with --explore first to populate the cache.')
        return

    for title in titles:
        citation = parse_reading_citation(title)
        print(f'OK  {title:55s} -> {citation}')

    print(f'All {len(titles)} cached reading citations parsed successfully.')


def harvest_paschal_window(reference_year, delay=5.0):
    """One-time full harvest, not a recurring job (see module docstring).

    Fetches every real calendar date needed to cover both axes this project
    keys data by:

      - The fixed/menaion axis (month, day): covered simply by fetching a
        full calendar year, since `reference_year` is a plain Gregorian year.
      - The Paschal-cycle axis (pdist): this project's own Reading table
        spans pdist -133 to +279 (412 days, confirmed against the live DB,
        not just the code comment) -- wider than one calendar year and
        straddling the two adjacent years around Pascha. Fetching that
        window guarantees every pdist value has a real date.

    Pascha is computed the same way this project already does it
    (dateutil.easter, method=2 -- see calendarium/datetools.py's
    compute_pascha_jdn), not re-derived independently, so the reference
    date lines up with this project's own Paschalion.

    This does NOT split fixed vs. paschal content or segment saint names --
    that's a later stage (see the claude-api-driven segmentation pass this
    was scoped alongside). This stage only fetches and caches raw JSON to
    data/antiochian_raw/, one file per date. Re-running it is safe and cheap
    since already-cached dates are skipped without hitting the network.
    """

    from dateutil.easter import easter

    pascha = easter(reference_year, method=2)

    window_start = pascha - timedelta(days=133)
    window_end = pascha + timedelta(days=279)
    dates = [window_start + timedelta(days=i) for i in range((window_end - window_start).days + 1)]

    # Feb 29 only recurs every 4 years, so the window above -- built around a
    # single reference year's Pascha -- won't necessarily include a leap day.
    # Supplement with one from a nearby past leap year (safely within
    # antiochian.org's data horizon, unlike guessing at a future one).
    if not any(d.month == 2 and d.day == 29 for d in dates):
        dates.append(date(2024, 2, 29))

    print(f'Pascha {reference_year}: {pascha}')
    print(f'Window: {window_start} to {window_end} ({len(dates)} dates)')

    client = Antiochian(delay=delay)
    client.authenticate()

    total = len(dates)
    fetched_new = 0
    cached_hits = 0
    errors = []

    for i, d in enumerate(dates, 1):
        already_cached = client._cache_path(d).exists()
        try:
            client.get_liturgical_day(d)
            if already_cached:
                cached_hits += 1
            else:
                fetched_new += 1
        except Exception as e:
            errors.append((d, str(e)))
            print(f'  ERROR {d}: {e}')

        if i % 25 == 0 or i == total:
            print(f'{i}/{total}  (new fetches: {fetched_new}, cache hits: {cached_hits}, errors: {len(errors)})', flush=True)

    print(f'\nDone. {fetched_new} new fetches, {cached_hits} served from cache, {len(errors)} errors.')
    if errors:
        print('Failed dates:')
        for d, msg in errors:
            print(f'  {d}: {msg}')


def explore_dates():
    """Network reconnaissance against antiochian.org. Rate-limited (see the
    Antiochian class's default delay) and only touches a small, deliberately
    chosen set of dates -- not a full-year walk."""

    client = Antiochian(delay=2.0)
    client.authenticate()

    # 1. Fixed, high-rank, never-overlaps-Lent feast across 3 years with
    #    different Pascha dates. Expect near-identical output every year --
    #    confirms this content is purely calendar-locked (menaion).
    print('--- Dormition of the Theotokos (fixed, Aug 15) across years ---')
    for year in (2024, 2025, 2026):
        print(describe(client.get_liturgical_day(date(year, 8, 15))))

    # 2. Pure moveable feast (Ascension = Pascha + 39 days), fetched on the
    #    *actual* calendar date it falls on each of those same years. Expect
    #    "Ascension" regardless of the (different) calendar date -- confirms
    #    paschal-cycle content follows Pascha, not the fixed calendar.
    print('\n--- Ascension (moveable, Pascha+39) across years ---')
    for pascha in (date(2024, 5, 5), date(2025, 4, 20), date(2026, 4, 12)):
        print(describe(client.get_liturgical_day(pascha + timedelta(days=39))))

    # 3. Boring fixed control far from Pascha in every year -- sanity check
    #    that a plain menaion day is stable and uninteresting.
    print('\n--- St. Demetrius (fixed, Oct 26), boring control ---')
    for year in (2024, 2025):
        print(describe(client.get_liturgical_day(date(year, 10, 26))))

    # 4. The interesting case: Annunciation (fixed, March 25) landing on a
    #    Lenten weekday. This repo's own Year.floats has a whole
    #    Weekday-keyed match statement for exactly this collision (moved
    #    paremias, etc. -- see calendarium/liturgics/year.py). Does
    #    antiochian.org's feastDayDescription fold the two together the way
    #    our own composite Day does (pdist query | month/day query), or does
    #    one clobber the other?
    print('\n--- Annunciation overlapping Great Lent ---')
    print('2026-03-25 falls on a Wednesday of Lent (ann_pdist=-18):')
    print(describe(client.get_liturgical_day(date(2026, 3, 25))))


if __name__ == '__main__':
    import sys

    if '--explore' in sys.argv:
        explore_dates()
    elif '--harvest' in sys.argv:
        # python3 ingest_antiochian.py --harvest [year]
        year = int(sys.argv[sys.argv.index('--harvest') + 1]) if len(sys.argv) > sys.argv.index('--harvest') + 1 else 2026
        harvest_paschal_window(year)
    else:
        selftest_parser()
        print()
        selftest_reading_citations()
