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
4. Fast-follow: recover `daSlevel` rank data during the same matching pass.
   (Done -- the planned `high_rank` derivation from `rank` didn't hold up
   empirically; kept as two independent fields instead, see below.)
5. Only then, fix issue #146 -- `new_style` becomes a one-line check on the
   through-table row instead of pattern-matching annotation text.

## Status

Design agreed (2026-07-28). Isolated on branch `saint-model-refactor` until
thoroughly tested -- not to be merged to `main` until each stage above is
complete and verified.

**Stage 1 done** -- `Saint`/`DayCommemoration` schema added (additive only,
`Commemoration` untouched), plus `Day.story`. 114/114 tests pass.

Along the way, ran a completeness audit of the current `Commemoration` data
against the original abbamoses.com scrape (`~/src/abbamoses/stories.json`):
of 930 entries, only 18 had no reasonable match against current data, and
only one of those had real story content (the rest were bare Forefeast/
Leavetaking labels already covered elsewhere under different wording).
Added that one (Blessed Matrona of Moscow) -- then found and corrected a
mistake in that same add, see Stage 2 below.

**Stage 2 done** -- populated `Saint`/`DayCommemoration` from the existing
`Commemoration` data (900 dated rows -> 900 `DayCommemoration` rows across
897 `Saint` rows; 371 matched existing `Day.saints`/`feast_name` text, 529
additive). Manually reviewed all 23 flagged `alt_title` mismatches and all
30 newly-found same-date candidates individually rather than trusting score
thresholds -- found the existing `alt_title` data has real problems (not
just Brian's suspicion, confirmed): 3 rows had the literal string `"No
match"`/`"No match found"` saved as if it were a real value (one of which
actually had a real match available), 3 were correct matches gone stale
from this session's own earlier spelling fixes (Anthusa->Arethusa,
Prussa->Prusa x2, Habbakuk->Habakkuk), 3 were correct matches with an
unrelated second Day entry wrongly concatenated onto them, and 3 were
genuine wrong-entity matches (Atticus of Constantinople matched to an
unrelated movable-feast label; Lucian of Antioch matched to an unrelated
council reference; "Eutyches (1st c.)" conflated with the unrelated
"Eutychius" patriarch) -- all cleared to additive.

**Two data errors caught and fixed during Stage 2's population**, both
confirmed via OCA and ROCOR (holytrinityorthodox.com) before touching
anything:

- Blessed Matrona of Moscow, added in Stage 1 at April 19, turned out to be
  a duplicate on the wrong day -- deleted. Both OCA and ROCOR anchor her to
  civil May 2 only; ROCOR's own Julian-native calendar page confirms "May
  2, 2024 (April 19, O.S.)" is one real day, and neither source lists her
  on civil April 19. She's now a third confirmed instance (with Alexis Toth
  and Herman's glorification) of a modern commemoration needing
  `new_style=True` treatment rather than the ordinary OS-reinterpretation
  every traditional Menaion entry gets -- interesting that this one was
  found from the opposite direction (an OS-labeled "April 19" that turned
  out to need civil anchoring, rather than an NS-labeled date needing it).
- The "canonization (1970) of St Herman of Alaska" Commemoration row was
  dated July 27 in the source data -- OCA's July 27 page shows four
  entirely unrelated saints. Repointed to August 9 (his confirmed
  Glorification date, matching the existing `Day` row).

**Deliberately not populated in this pass**: 9 `Commemoration` rows with
`day=None` (Sunday of the Holy Fathers of the Seven/Seventh Ecumenical
Councils, Sunday before/after Nativity, Sunday of the Holy Forefathers,
plus a few Feb/March entries of unclear date) -- these need `pdist`-based
linking to a floating `Day` row, not fixed month/day matching. Flagged as a
follow-up, not blocking.

**Also noticed, not yet investigated**: one organic cross-date name
collision survived the population as-is -- "St Emilia (375), mother of
Sts Macrina, Basil the Great and Gregory of Nyssa..." links to both 1/1
and 5/8. Unclear yet whether this is a genuine abbamoses-source duplicate
(the same entry appearing under two headings) or something else. Low
priority.

## Stage 3: rewire `_collect_commemorations`

Done. `calendarium/liturgics/day.py` no longer reads `Day.saints` or queries
`Commemoration` directly -- `self.saints`/`self.minimal_saints`/`self.stories`
are now built entirely from `Saint`/`DayCommemoration`. `Day.saints` (the
JSONField) is left in the model/DB for now as a safety net, unused by any
code -- removing it is a separate, final cleanup once this has run in
production for a while.

**A full re-population was needed, not just a query rewrite**, once it
became clear `DayCommemoration` (populated *from* `Commemoration` in Stage
2) wasn't a strict superset of `Day.saints`: 154 `Day.saints` entries (91
`common` + 4 `slavic` + 59 `greek`) had no `DayCommemoration` counterpart at
all. The 59 `greek` ones are structural and expected -- `Commemoration`/
abbamoses is entirely Slavic-sourced, so Greek-tagged rows were never going
to match a story. The 95 `common`/`slavic` ones were genuine gaps. Brian
chose full replacement (option 1 of 2 offered) over a narrower rewire that
would have left `Day.saints` as an ongoing second source of truth.

Rebuilt the population as two ordered passes plus a schema addition
(`DayCommemoration.day_native`, `BooleanField`) rather than overloading
`ordering` with dual meaning:

- **Pass 1 (day-native)**: iterate `Day.saints` directly (already-correct
  text, per all of this session's fixes) for every `Day` row across all
  three traditions. For each name, search that date's `Commemoration` rows
  for a matching story via fuzzy word-overlap -- checking *both* the
  title and, critically, the row's pre-existing (Stage-2-verified)
  `alt_title`, since a fresh title-only match kept falling just short of
  threshold on real matches that differ only by epithet (e.g. "Theodosius
  the Cenobiarch" vs. Day's "Theodosius the Great") -- alt_title reuse
  recovered 87 of these. `ordering` = the name's list position, so display
  order exactly matches the old `Day.saints`-based behavior.
- **Pass 1b (feast_name matches)**: some terse text lives in `Day.feast_name`
  instead of `.saints` entirely (e.g. Jan 1 "Circumcision of Our Lord; St
  Basil the Great", or Alexis Toth's whole entry) -- these are already
  shown via `self.feasts`, so mirror the old alt_title-containment
  behavior: consume the story (so it doesn't *also* show up as a
  standalone additive duplicate) but exclude it from the saints name-list
  via an `ordering=-1` sentinel, which `day.py` explicitly skips when
  building the name list.
- **Pass 2 (additive)**: whatever `Commemoration` rows remain unconsumed
  get their own `Saint` entity, linked to that date's default `Day` row,
  `day_native=False`.

**A real, pre-existing bug in the old code was caught and *not* preserved,
after review**: the old `_add_supplemental_commemorations` only
deduplicated a story against the terse list when the row already had an
`alt_title` (i.e., a subset a 2018-era GPT-3.5 pass happened to match) --
anything without one got appended unconditionally, even when it duplicated
an existing name under fuller phrasing (e.g. Jan 9 showed both "Hieromartyr
Philip, Metropolitan of Moscow" *and* "Saint Philip, Metropolitan of Moscow
(1569)" as separate entries). The new code catches these correctly. Updated
the two affected golden test fixtures (`last_bday.json`, `january.json`)
to reflect the corrected (deduplicated) output after manually verifying
each diff was a legitimate improvement, not a content loss.

**Transliteration-variant duplicates, reviewed and mostly fixed** (a
full-year duplicate scan initially found 5; fuzzy word-overlap matching
can't catch same-person duplicates that differ only by transliteration,
with zero shared tokens). All other pairs the scan flagged turned out to
be genuinely different saints sharing a name element (e.g. two distinct
St. Peters of Damascus, centuries apart) -- correctly left alone.

Merged 4 of the 5 into their day-native `Saint` after individually
verifying identity (not just name resemblance) -- Meletius/Meletios
(Archbishop of Antioch), Sophronius/Sophronios (Patriarch of Jerusalem),
Zachariah/Zacharias the Recluse, and Herman/Germanus of Kazan. The last one
Brian specifically questioned ("Are you sure St. Herman is the same as St.
Germanus?") -- verified via the story's own content (successor to St.
Gurias, first Archbishop of Kazan; killed by Ivan the Terrible, 1568) cross-
checked independently against OCA (same Gurias connection, same see, same
era) before merging. "Herman" is the common Slavic/OCA rendering of the
Greek Γερμανός (Germanos); "Germanus" is abbamoses's Latinized form of the
same name -- same pattern as the other three pairs. A defensive assert
(`day_native.story` must be empty before merging) caught a real mistake in
the initial pairing: John Calabytes/Kalyvites (1/15) is *not* a duplicate
at all -- the day-native entry's story is about Paul of Thebes only and
never mentions John; John's own biography (a Constantinople senator's son)
lives entirely in the other entry. These are two different people
co-commemorated the same day under one compound title, both stories
needed -- left unmerged.

For each of the 4 genuine merges: the additive entry's story moved onto
the day-native `Saint` (which had none), then the additive `Saint`/
`DayCommemoration` was deleted. 114/114 tests still pass.

## Fast-follow: `daSlevel` rank recovery

Done, with one revised conclusion. Parsed Paul Kachur's `days.sql` again
(117 rows with `daSlevel > 0`, distribution `{2: 52, 3: 40, 4: 25}` as
found earlier this session) and fuzzy-matched each against the current
`Saint`/`DayCommemoration` data the same way as the rest of this refactor
(title + `alt_title`, score >= 0.4). All 117 source rows matched with zero
misses, setting `rank` on 181 `DayCommemoration` rows (some source rows
list multiple co-commemorated saints).

**The planned `high_rank = rank >= N` computed property doesn't hold up**,
and after checking rather than assuming, that's not because the rank scale
runs the opposite direction from expected (Brian's hypothesis, worth
checking but not what's happening here) -- `lib/core.REFERENCE.txt`
explicitly documents `daSlevel` as sharing `daFlevel`'s scale (increasing
= more liturgically elaborate), and real examples support that direction:
`slevel=4` includes some of the most major saints in the calendar
(Seraphim of Sarov, Cyril "Teacher of the Slavs", Nino of Georgia), while
`slevel=2` has real weight too (Athanasius the Great, Macarius the Great) --
not a clean "4 important, 2 minor" split either direction.

Cross-tabulating rank against `Commemoration.high_rank` (the dagger-sourced
boolean) shows no usable correlation at all: rank=2 is 31% `high_rank=True`,
rank=3 is 33%, rank=4 (nominally the *most* liturgically elaborate) is only
19% -- flat-to-inverted, not a threshold waiting to be found. Best
explanation: `daSlevel` reflects the typikon's own service-structure symbol
(black squiggle/red squiggle/red cross -- how many hymns get added that
day), a narrow, mechanical distinction, while `high_rank` is very likely
abbamoses's own editorial judgment about which stories merited a fuller
flag -- two legitimately different axes, not one measuring the other
imperfectly. Decided (with Brian, 2026-07-28): keep `rank` and `high_rank`
as independent fields; no computed-property derivation.

114/114 tests pass. All 6 real production consumers of `.saints`/`.stories`
(`alexa/speech.py`, `calendarium/ical.py`, and the 5 templates) verified
rendering correctly with no code changes needed -- `Saint.title` is a
property alias for `.name` specifically so `day.stories` items keep
answering to `.title`/`.story` exactly like the old `Commemoration` objects
did.

Next up: Stage 3 (rewire `_collect_commemorations`), or the cross-date
matching pass for same-saint-different-occasion pairs (Sergius of
Radonezh's July 5 translation-of-relics vs. September 25 repose was
noticed in passing as another real example, alongside Herman's).
