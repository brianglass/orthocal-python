# Saint entity model refactor

## Background

GitHub issue #146 reported that modern (post-1900) saints appear 13 days
late, or missing entirely, when viewing the site in Julian-calendar mode --
e.g. St. John (Maximovich) of Shanghai shows up on Julian-labeled "July 2"
(civil July 15) instead of civil July 2, where ROCOR/Old-Calendar practice
actually observes him.

## Root cause

`Day.__init__` (`calendarium/liturgics/day.py`) computes `self.month`/`self.day`
differently per calendar mode:

- Gregorian mode: the requested civil date, directly.
- Julian mode: that civil date reinterpreted under the Julian calendar's own
  numbering (`datetools.gregorian_to_julian`) -- "what date does the Julian
  calendar currently read."

Every fixed-date query (`Day` table and `Commemoration.objects.filter(month=
self.month, day=self.day)`) is keyed off that single pair. This is exactly
right for the traditional Menaion, where a date like "Dec 25" is
fundamentally an Old-Style-native label that both calendars correctly
reinterpret. It breaks for modern saints whose commemoration is recorded in
New-Style terms (a death or glorification is a historical fact dated using
the globally-standard Gregorian calendar) -- both New- and Old-Calendar
jurisdictions observe the same real civil day each year for these, but the
app blindly reinterprets the stored NS key as if it were OS-native, shifting
it 13 days later in Julian mode.

## Scope, confirmed empirically

Searched the whole dataset for the `"(... OC)"` cross-reference annotation
the issue reporter pointed to as the tell (present in `Commemoration.title`
for entries the original data curator already knew were New-Style-dated).
Found **17 `Commemoration` rows**, all modern 20th-century figures (Nikolai
Velimirovich, Alexis Toth, Sophrony of Essex, Seraphim Rose, Paisios, etc.),
zero in the `Day` table via the same text pattern.

**But pattern-matching on the annotation text is not sufficient** -- found
two confirmed additional instances in `Day` with no annotation at all to
flag them:

- **St. Alexis Toth (May 7, `tradition=slavic`)** -- the exact same saint
  also has a `Commemoration` row at the same date carrying `"(April 24 OC)"`.
  Two independent records for one person, connected by nothing but a
  fuzzy-matched string, so the flag existed on one and not the other.
- **St. Herman of Alaska (Aug 9, `tradition=slavic`)** -- confirmed via OCA
  this is specifically his 1970 glorification date, not his 1837 repose. A
  20th-century canonization ceremony is definitionally NS-dated, with zero
  textual signal marking it as such.

Two more (John Kochurov, Oct 31; Raphael of Brooklyn, Feb 27) are genuinely
ambiguous -- both die in the 1915-1917 window right at the Julian/Gregorian
civil-calendar switch, and OCA's own pages don't resolve which calendar
convention their listed date uses. Flagged, not yet resolved.

Also found, unrelated to the calendar bug but from the same investigation:
**St. Luke of Simferopol is entirely absent** from both `Day` and
`Commemoration` (confirmed via OCA he belongs on June 11) -- a missing-data
gap, not a date-logic bug.

## Why a per-row FK/flag isn't the full answer

The Herman of Alaska case is the clearest argument for going further than
"`Commemoration` gets a `ForeignKey` to `Day`, plus a `new_style` flag on
`Day`": he has **two separate, disconnected `Day` rows** (Dec 13 repose, Aug
9 glorification) with nothing structurally tying them together as the same
person's two occasions. A flag per `Day` row can't express "this saint has
one OS-native occasion and one NS-native occasion" as connected facts about
one identity -- there's no identity to hang either fact off of.

This also directly explains a problem already accepted as deferred in
project memory: `Day.saints` (terse), `Commemoration.title` (formal
hagiographic style), and `Reading.desc` (a third, independent style)
currently describe the same person with zero shared identity, patched
one-off via `Commemoration.alt_title` string-matching rather than solved.

## Source-structure finding: this is new modeling work, not recovery

Checked the original abbamoses.com scrape (`~/src/abbamoses`, site no longer
live) before assuming a `Saint` entity could be mechanically extracted from
existing structure. It can't: `scrape.py` parsed one HTML page per month,
each a flat `<dl>` of dates with commemoration titles and story blocks --
no per-saint pages, no cross-linking between a saint's multiple occasions
anywhere in the source. Any saint-identity link (e.g. recognizing that Aug 9
and Dec 13 are the same Herman) will be inference we build, not extraction --
a real, non-trivial matching project, not a mechanical schema migration.

## Proposed schema

```
Saint(name, story, ...)
DayCommemoration(day=FK(Day), saint=FK(Saint), rank=int, new_style=bool, ordering)
Day.story  # feast-level narrative, non-saint content (great feasts etc.)
```

- `Day` <-> `Saint` many-to-many via `DayCommemoration`, not a straight FK,
  because 81% of the 370 distinct (month, day) slots in `Commemoration` have
  more than one commemoration on them (max 6), and because a single saint
  can appear on multiple `Day` slots (repose, translation of relics,
  synaxis, glorification).
- `rank` and `new_style` live on the through-table (`DayCommemoration`), not
  on `Saint` or `Day` alone -- both are facts about a specific *occurrence*,
  not the person or the calendar slot in general. A saint's main feast and
  translation-of-relics occasion routinely differ in rank; the same saint
  can have one OS-native occasion and one NS-native occasion.
- Story text lives on `Saint` (one canonical biography, reused across all
  of that saint's occasion-links -- matches how the abbamoses prose itself
  reads, e.g. St. Basil's story cross-references "his sister St Macrina
  (July 19)" inline, treating the person as the durable thing) plus a
  separate, much smaller `Day.story` for non-saint content, rather than a
  third join-table shape.

### Rank recovery (fast-follow, same matching pass)

Paul Kachur's `daSlevel` field (investigated earlier this session, see
`docs/greek-fasting.md`'s sibling investigation into his repo) is a
per-row field using the same typikon-symbol scale as `feast_level`,
empirically never exceeding rank 4 (`{0: 715, 2: 52, 3: 40, 4: 25}` across
his dataset). This is the same per-occurrence shape as the proposed `rank`
field above -- recovering it doesn't add a separate matching pass, just one
more attribute carried along once a `Commemoration`/`Day.saints` entry is
matched to its row in `days.sql`.

`Commemoration.high_rank` (currently a plain boolean, sourced from the `†`
dagger symbol on the original abbamoses HTML -- see `scrape.py`) becomes a
computed property (`rank >= N`) instead of an independently-maintained
boolean. `N` should be derived empirically by checking what `daSlevel`
values the entries currently marked `high_rank=True` actually have, rather
than guessed.

## Cost / scale, measured before committing to this

- 909 total `Commemoration` rows, 370 distinct (month, day) slots, 299 of
  those (81%) with more than one row.
- Only 347 of 909 (38%) currently have an `alt_title` match to a `Day` entry
  (from a one-time 2018-era GPT-3.5 pass in `match_saints.py`) -- the
  remaining 562 are either genuinely additive (a full story with no terse
  `Day.saints` summary) or missed matches from an imperfect first attempt.
- Only 6 real production consumers of `Day.saints` outside scratch scripts:
  `alexa/speech.py`, `calendarium/ical.py`, and 5 templates (`oembed_calendar`,
  `calendar_embed`, `calendar_day`, `feed_description`, `readings`) -- all go
  through `liturgics/day.py`'s `_collect_commemorations`, which builds the
  final `self.saints` list of display strings. If that output shape is
  preserved, none of the 6 need to change -- only how the list gets
  assembled internally. This caps the rewire cost significantly.

## Staged plan

1. Schema + migration for `Saint` and the `DayCommemoration` through-table.
2. Populate `Saint` rows and links -- start from the already-trusted 347
   `alt_title` matches and `Day.saints` entries as a reliable base layer,
   then a fresh matching pass over the remaining ~562 unmatched
   `Commemoration` rows *and* a cross-date pass to find same-saint,
   different-occasion pairs like Herman's. Confidence-tiered, reviewed
   before anything commits -- not a bulk auto-import.
3. Rewire `_collect_commemorations` to build `self.saints` from the new
   relational structure. Bounded per the consumer count above.
4. Fast-follow: recover `daSlevel` rank data during the same matching pass;
   derive the `high_rank` cutoff empirically against the dagger-sourced
   boolean.
5. Only then, fix issue #146 -- `new_style` becomes a one-line check on the
   through-table row instead of pattern-matching annotation text.

## Status

Design agreed (2026-07-28). Not yet started. Isolated on branch
`saint-model-refactor` until thoroughly tested -- not to be merged to `main`
until each stage above is complete and verified.
