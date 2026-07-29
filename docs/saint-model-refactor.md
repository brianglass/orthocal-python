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
gap, not a date-logic bug. **Closed 2026-07-29**: added as a `Saint` +
additive `DayCommemoration` on June 11 (`tradition='common'`), title
matching OCA's own ("St Luke, Archbishop of Simferopol"). Deliberately no
`story` -- not worth sourcing/writing one for this pass.

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

## Stage 4: title/identity separation, then cross-date consolidation (2026-07-28)

**Problem surfaced in design discussion, before touching code**: `Saint.name`
was doing double duty as both the person's stable identity (used by
`get_or_create_saint` to decide "is this the same person") and the
occasion-specific display text. Since occasion wording genuinely varies
(repose vs. glorification vs. translation-of-relics), the same person kept
fragmenting into multiple disconnected `Saint` rows -- confirmed for Herman
of Alaska (3 rows for 3 different people, one of them a compound string
covering 3 people at once) and Sergius/Herman of Valaam (2 rows for one
joint identity). A related design conversation (should occasion-specific
narrative live on `Saint` or `DayCommemoration`?) concluded that ALL story
content should move to `DayCommemoration` -- `Saint.story` was eliminated
entirely rather than kept as a fallback, since in practice occasion-specific
narratives never turned out to share a reusable "canonical bio" the
fallback would have served.

**Schema change**: `Saint` reduced to `name` (terse identity) + `full_name`
(nullable, fuller descriptive form for an eventual saint detail page --
discussed and explicitly deferred as a follow-on, along with a possible
`Saint.dates` free-text field for birth/death, once there's a real page to
build). `DayCommemoration` gained real `title` and `story` fields
(occasion-specific); the old `Saint.title` alias property is gone since
callers now get real fields directly off `DayCommemoration`. Migration
0009/0010 (Django wanted to remove `Saint.story` and add the new fields in
one migration -- split by hand into add-then-backfill-then-remove so the
data had somewhere to land before the source column disappeared).

**`full_name` backfill**: surveyed `Commemoration.title` for occasion-verb
prefixes ("Repose of", "Translation of the relics of", etc.) that needed
stripping into `full_name` vs. the original wording staying on
`DayCommemoration.title`. Scope was much smaller than the fragmentation
problem suggested: only 36/900 titles actually had a genuine occasion
prefix to strip; 854 were already identity-level text (honorific + name +
epithet, often a parenthetical date) with nothing to strip, so they copied
straight across. A first attempt also stripped a bare leading "The " --
wrong, since that also matches one-off feast titles ("The Circumcision of
Our Lord...") that have no separate identity to split out; removed that
rule and kept only prefixes naming a specific kind of occurrence.

**Herman of Alaska consolidation** -- the motivating case, now fixed:
- The Dec 12 entry turned out to be a pure cross-reference stub in
  abbamoses's own text ("He is also commemorated tomorrow, December 13. See
  his life there.") -- confirmed against OCA (no Herman entry at all on
  Dec 12) and deleted rather than kept as a competing occasion.
- The Dec 13 "compound" entry (one `Saint.name` covering Herman, Juvenaly,
  and Peter the Aleut) turned out to be a real joint commemoration in the
  source ("The Synaxis of St Herman and the American Protomartyrs"), not
  pure scraper garbling -- but still needed splitting, because Herman alone
  has a second, separate occasion (the Aug 9 Glorification) that the other
  two don't share. Split into 3: Herman keeps the Dec 13 row and absorbs
  the Aug 9 Glorification (previously a disconnected `Saint`); Juvenaly
  gets his own new additive row; Peter the Aleut's new row was pointed at
  the *same* `Saint` as the pre-existing Greek-tradition Dec 12 entry
  (`Holy New Martyr Peter the Aleut`) rather than creating a 4th
  disconnected row -- a genuine cross-tradition identity link, exactly what
  this model exists to capture.
- Sergius and Herman of Valaam's two occasions (June 28 repose, Sept 11
  translation of relics) merged onto the one `Saint` that already modeled
  them as a joint identity -- no split needed here, since both occurrences
  were of the *same* pair, unlike the Kiev Caves case below.

**Full cross-date duplicate survey**: reused the Jaccard token-overlap
approach across all ~1000 `Saint` rows (not scoped to one person), which
surfaced 287 candidate pairs at score >= 0.4. This is a fundamentally
noisier search than the earlier single-day transliteration scan --
comparing across the whole year means generic liturgical vocabulary
("Theotokos", "Ever-Virgin Mary", "Fool-for-Christ", "Pope of Rome",
"Wonderworker") produces heavy false-positive overlap between genuinely
different feasts/people (different Theotokos feasts, three distinct
historical Cosmas-and-Damian pairs, different Popes of Rome, different
Ecumenical Councils, three different Matronas, many different Johns/
Alexanders/Josephs on first-name overlap alone). After filtering out
conflicting parenthetical years and same-day pairs, manually reviewing all
255 remaining candidates found the single strongest signal was the
source's own explicit cross-reference text ("His main commemoration is
October 19", "For his life see September 25", "also commemorated August 4,
see that date") -- every pair carrying that signal was a confirmed genuine
match. **25 pairs merged** on this basis (Theophan the Recluse, Innocent of
Irkutsk, Joseph the Hymnographer, Martin the Confessor, Aristarchus/Pudens/
Trophimus, Prophet Ezekiel, Alexander Nevsky, John the Theologian, Sergius
of Radonezh, John of Kronstadt, Vitalis, Cyprian of Carthage, Greatmartyr
Euphemia, Seven Sleepers/Youths of Ephesus, Philip Metropolitan of Moscow,
Ignatius the Godbearer, Theodore Stratelates, Athanasius the Great, John
Mavropos, Jonah Metropolitan of Moscow, St Sava of Serbia (3-way), Boris
and Gleb, Job of Pochaev (3-way)).

**Two more joint-vs-solo splits**, same shape as Herman: "Ven. Anthony and
Theodosius of Kiev Caves" (Sept 2, no story of its own) split so Anthony's
existing solo identity (July 10) and Theodosius's existing translation-of-
relics identity (Aug 14) each get their own additive link to that day
rather than being merged into one one conflated identity; "Ven. Isaac,
Dalmatus, Faustus" (Aug 3) split so Isaac's portion links to his existing
solo identity (May 30, explicit "also commemorated May 30, see his life
there" in the source text) while the renamed `Saint` keeps Dalmatus and
Faustus, who have no separate entry elsewhere.

**A third joint-vs-solo split, caught by Brian reviewing the fixture after
the fact**: the Athanasius the Great merge above was wrong. At merge time
the reasoning was "Cyril has no separate occurrence to reconcile with, so
the conflated identity is harmless" -- but that reasoning addressed the
wrong problem. The May 2 occurrence ("His main commemoration is January
18") is Athanasius's *alone*; Cyril is never commemorated May 2 at all, so
pointing that occurrence at a `Saint` whose name is "Ss Athanasius the
Great **and Cyril** of Alexandria" is simply incorrect, independent of
whether Cyril has anywhere else to anchor to -- exactly the same failure
mode as Anthony/Theodosius and Isaac/Dalmatus/Faustus, just not recognized
as such the first time. Split out a solo Athanasius `Saint`, repointed the
May 2 `DayCommemoration` to it, left the two Jan 18 (common + greek) rows
on the joint "Athanasius and Cyril" `Saint`. **Lesson**: "no separate
occurrence to reconcile with" is not a valid reason to leave a joint
identity attached to a solo occasion -- check whether the *other* person in
the joint pair is actually commemorated on that specific day, not just
whether they have some other row to fall back on.

**The other ~230 candidates were reviewed and deliberately NOT merged** --
worth recording why, since the failure mode is specific: Jaccard score on
short token sets (after stopword removal) is unreliable at the low end.
"John the Hieromartyr" reduces to the single token `{john}` after stopword
stripping, which trivially scores 0.5 against *any* other entry containing
"John" plus one more word -- this pattern (single- or two-token identities)
accounts for the bulk of the 255 and is nearly all noise, not a matching
problem to solve better. Concrete confirmed-different examples worth
remembering if this survey is ever rerun: three distinct historical
Cosmas-and-Damian pairs (Rome/Arabia/Asia Minor, on three different dates);
"Bl. Andrew, Fool-for-Christ" (Constantinople, 911) vs. "Blessed Andrew of
Totma" (1637) -- different people, ~700 years apart; three different
Maximos saints (the Confessor, the Greek, Kavsokalybites); three different
Matronas (Moscow-blind 1952, Perga/Constantinople 492, Chios); different
Popes of Rome and different Ecumenical Councils matched only on
"Pope"/"Rome" or "Ecumenical Council" tokens. `Saint.name`/`.full_name`
sharing an epithet or office is not evidence of shared identity without a
corroborating explicit source signal or a genuinely matching biography.

135 total `Saint` rows removed across this stage (25 simple merges + the
Herman/Sergius-Herman/2-split cleanups); 114/114 tests still pass
unchanged, fixture regenerated.

**Deliberately deferred, decided in conversation, not yet built**:
`Saint.dates` (birth/death display text) and the saint detail page itself
(one page per `Saint`, listing every `DayCommemoration` chronologically,
linked from saint names on the daily readings page) -- both explicitly
scoped as a future follow-on rather than part of this stage. The saint
page is *why* this consolidation pass mattered beyond data hygiene: without
it, the same person would render as 2-3 disconnected pages.

## Stage 5: the actual #146 fix (2026-07-28)

**Root cause, precisely**: `Day.__init__` computes `self.month`/`self.day`
by reinterpreting the requested civil (Gregorian) date under the Julian
calendar's own numbering (`datetools.gregorian_to_julian`) when in Julian
mode. For traditional Menaion content this is correct -- Old Calendar
believers observe a fixed feast on its own Julian-labeled day, which
genuinely falls on a different civil day than the Gregorian date requested.
But `new_style` commemorations are modern historical events (a repose, a
1970 canonization) that both Old- and New-Calendar jurisdictions observe on
the same real civil day -- there's no Julian-label shift to apply, because
the event never had a Menaion slot to begin with.

**Fix, in `_add_supplemental_commemorations`** (`calendarium/liturgics/day.py`):
`Day.__init__` now stores `self.calendar`. In Julian mode, `new_style=True`
`DayCommemoration` rows are excluded from whichever Julian-shifted `Day`
they happen to be additively attached to, and a second, narrow query
re-fetches `Day` rows keyed on `self.gregorian_date.month`/`.day` (the true
civil date, always available since it's computed unconditionally in
`__init__`) to pull in just their `new_style=True` commemorations, appended
into the additive bucket regardless of their original `day_native`/
`ordering`. In Gregorian mode `self.month`/`self.day` already equal the
civil date, so nothing changes -- confirmed by leaving the Gregorian-mode
branch of the loop untouched.

**Why exclusion (not just addition) was necessary**: every one of the 21
confirmed `new_style` rows turned out to be an *additive* commemoration
attached to a `Day` row that also carries ordinary, unrelated Menaion
content for that Julian-labeled slot (checked all 19 systematically before
writing the fix, not assumed) -- e.g. Gerontissa Gavrilia's row also
natively lists "Ven. Hilarion the New". Without exclusion, the bug would
simply move: whichever *other* civil day's Julian-shifted label happens to
land on that same month/day would incorrectly show the modern saint
alongside that day's real native content.

**Confirmed scope -- 21 `DayCommemoration` rows flagged `new_style=True`**:
19 found via the `"(...OC)"` annotation already present in `Commemoration.title`
(itself confirming these are all 20th-century figures whose repose year is
explicitly OS-annotated: Gerontissa Gavrilia, John Maximovich, Silouan of Mt
Athos, Lazarus (Moore), Nikolai (Velimirovic), Seraphim of Vyritsa, Paisios
of the Holy Mountain, Maxim (Sandovich), Jonah of Manchuria, Savvas the New
of Kalymnos, Alexis Toth, Sophrony of Essex, Photios Kontoglou, Georges
Florovsky, Seraphim (Rose) of Platina, Justin (Popovic), Porphyrios of
Kavsokalyvia, Gorazd of Slovakia, Joseph the Hesychast), plus the 2 found
earlier with no textual tell (Herman of Alaska's Aug 9 Glorification,
Matrona of Moscow's May 2 repose). Matching each `Commemoration` row to its
`Saint`/`DayCommemoration` needed care: several stories were the same
`'<p></p>'` empty placeholder (Georges Florovsky's row matched 8 different
`DayCommemoration` rows via story-equality before resolving it by name
instead) -- a repeat of the same false-collision pattern from the Stage 4
`full_name` backfill.

**A genuinely separate bug found and fixed along the way**: Justin
(Popovic)'s row had `day_native=True, ordering=-1` -- Stage 3's fuzzy
matching had mismatched his commemoration to *Tikhon's* `feast_name` text
on the same shared `Day` row (April 7), silently suppressing his name from
the terse list on the (wrong) assumption he was already represented via
`self.feasts`. Corrected to `day_native=False, ordering=0` so he displays
via the normal additive path. Unrelated to #146 itself, just adjacent data
surfaced by the same investigation.

**Tests**: 5 new (`test_liturgics.py::TestDay`) covering the civil-date
match, the negative case (the shifted-label date must NOT show it),
Gregorian-mode being unaffected, and both Matrona and Toth. 119/119 tests
pass; fixture regenerated.

**Deliberately still open, not part of this fix**: John Kochurov (Oct 31)
and Raphael of Brooklyn (Feb 27) remain genuinely ambiguous NS/OS cases --
neither OCA's pages nor era-based reasoning resolved them cleanly during
the original investigation, and nothing in this stage changed that.

This closes the core refactor plan. Remaining follow-on work (explicitly
deferred, not urgent): the saint detail page, `Saint.dates`, and eventually
removing the now-fully-unused `Day.saints` JSONField once this has run in
production a while.

## Stage 6: DayCommemoration.tradition -- fixing a real duplication antipattern (2026-07-28)

**Found while reviewing the fixture after Stage 5**: Brian noticed two
`DayCommemoration` rows for "Ss Athanasius the Great and Cyril of
Alexandria" with byte-identical `title`/`story`, one on the `common` Jan 18
`Day` row and one on the `greek` Jan 18 `Day` row. Investigating turned up
something bigger than a one-off duplicate: **26 saints** had this exact
pattern (a saint listed identically in both the `common` and `greek`
`Day.saints` JSON for the same date), because the Greek-tradition harvest
(a separate, earlier project) populated a full parallel `Day` row per date
rather than a sparse overlay the way `Reading` was designed -- confirmed
this wasn't the wholesale "hundreds of duplicate rows" problem it first
looked like: only 37 `greek`-tagged `Day` rows exist total, and every one
of them diverges from its `common` counterpart in *something* -- but for
29 of the 37, the *only* field that differs is `saints`, meaning the
separate `Day` row exists solely to carry a handful of Greek-specific
additions, at the cost of re-declaring (and thus double-storing) whatever
shared saints happen to also be commemorated that day in both traditions.

**Root architectural cause**: `_prefer_tradition_days` treats a
tradition-specific `Day` row as a *complete replacement* for that
(month, day) slot, not a merge -- correct for `Reading`, where each row is
independent and genuinely either shared or overridden at the individual-
citation level, but wrong for `Day`, where feast_level/fast/service_note
*and* the saints list all live on one row together. A date where only the
saints list differs still needs its own full row under this model, forcing
either full duplication (the bug) or losing the shared saints entirely if
the greek row had been trimmed to just its additions.

**Fix**: added `DayCommemoration.tradition` (same three-value common/
slavic/greek field as `Day`/`Reading`, migration 0011), making the
overlay/fallback pattern operate at the *individual commemoration* level
instead of the whole `Day` row -- mirroring `Reading`'s design exactly,
just one level down. `_add_supplemental_commemorations` now filters
`DayCommemoration` by `tradition__in=(self.tradition, 'common')` directly,
rather than relying solely on which `Day` row `_prefer_tradition_days`
picked. `_prefer_tradition_days` still exists and still governs day-level
facts (feast_level, fast, etc.) for the cases where those genuinely
diverge -- it's just no longer doing double duty for saints too.

**Data migration** (one-off script, not a Django migration): for each of
the 29 `greek` `Day` rows that diverge from `common` *only* in `saints`,
walked its `DayCommemoration` rows -- if the same `Saint` already has a
commemoration on the `common` row (a shared saint, duplicate content),
deleted the `greek`-attached copy after asserting the content actually
matched; if not (a genuine Greek-only addition, e.g. "Zenia the Martyr" on
Jan 18), repointed it onto the `common` `Day` row and tagged it
`tradition='greek'`. Deleted the 29 now-empty `greek` `Day` rows once done.
Result: 26 deduped/deleted, 33 genuine additions relocated, 26 `Day` rows
removed. The remaining 11 `greek`-tagged `Day` rows are either genuinely
greek-only dates with no `common` counterpart at all (8), or floating
(pdist-keyed, `month=0`/`day=0`) rows that diverge in more than just
`saints` and were correctly left untouched (3).

**A latent bug caught before it did damage**: the first version of the
migration script built a `{(month, day): day_row}` dict keyed only on
month/day to find each `common` counterpart -- but floating `Day` rows
(Paschal-cycle content, keyed by `pdist` instead of a real calendar date)
all share `month=0, day=0`, so that dict silently collapsed dozens of
distinct floating rows down to whichever was inserted last. Checked for
real damage before trusting the result: none occurred, because the
mismatched comparisons this caused all happened to show differences
beyond just `saints` (comparing unrelated floating content against each
other), so they were safely skipped rather than wrongly merged -- verified
directly (no floating rows deleted, no `DayCommemoration` incorrectly
pointed at a `month=0`/`day=0` row) rather than assumed safe. Worth
remembering if any further `Day`-level data work reuses this kind of
month/day keying: floating rows need `pdist` in the key, not just
month/day.

**Verification**: `Day(2026, 1, 18, tradition=Slavic)` now shows only
"Ss Athanasius the Great and Cyril of Alexandria"; `Day(2026, 1, 18,
tradition=Greek)` shows that plus "Zenia the Martyr" -- additive, not
replaced. New test
`test_tradition_specific_commemoration_is_additive_not_a_replacement`.
120/120 tests pass on a from-scratch test database (rebuilt the test image
and dropped `--keepdb` to confirm the regenerated fixtures are what's
actually being tested, not a stale cached test DB).

## Stage 7: retire `Commemoration`, migrate `high_rank`, more joint-vs-solo splits (2026-07-28)

**Retiring the source table.** `Commemoration` had zero remaining code
references (not queried anywhere, not registered in Django admin) since
Stage 3's rewire -- confirmed by grep before touching anything. The one
open item was `high_rank` (abbamoses's editorial "story-worthy" flag),
which had never been migrated onto the new model and had no consumer at
all. Brian chose to migrate it rather than drop it or leave the table as
a dead safety net. Added `DayCommemoration.high_rank` (migration 0012),
backfilled from all 129 `Commemoration` rows with `high_rank=True` using
the same story-equality-first/title-fuzzy-fallback approach used
throughout this project -- 128 matched cleanly, the 1 miss was
`Commemoration` id 860 (the Dec 12 Herman-of-Alaska stub already deleted
in Stage 5 as a confirmed duplicate/pointer, so correctly has nothing left
to match). Then deleted the `Commemoration` model entirely (migration
0013). `rank` and `high_rank` remain two independent fields per the
Fast-follow section's finding -- this migration doesn't change that,
just gives `high_rank` a home on the model that's actually used.

**A new, more general "event vs. person" pattern, found by Brian reviewing
the fixture**: `Saint` rows that are really commemorations of a *relic or
event* associated with an existing saint, not a distinct identity --
"Veneration of Chains of Apostle Peter" (Jan 16) was sitting as its own
disconnected `Saint` with no link to any Peter identity at all. Same root
cause as the Athanasius/Cyril and Anthony/Theodosius splits: the *only*
existing Peter-related identity was the joint "Holy, Glorious and
All-praised Leaders of the Apostles, Peter and Paul" (June 29) -- but the
Chains veneration is only about Peter, so linking it to the joint pair
would incorrectly implicate Paul. No solo "Apostle Peter" `Saint` existed
to link to, so one was created and the Chains veneration repointed onto
it. A broader pattern search (`Veneration of`, `Placing of`, `Appearance
of`, `Confession of`, `Miracle of`, `Icon of` as leading title patterns)
found one more of the same shape: "Miracle of Archangel Michael at
Colossae" (Sept 6), whose only existing Michael identity was the joint
"Synaxis of the Chief Captains... Michael and Gabriel" (Nov 8) -- same
fix, new solo "Archangel Michael" `Saint` created and repointed.

**Found and deliberately NOT fixed, flagged as a different/bigger
question**: "Robe of the Theotokos at Blachernae," "Sash of the
Theotokos," and "The Placing of the Precious Robe of the Lord in Moscow"
(Christ's robe) look superficially like the same pattern, but aren't --
unlike Peter and Michael, there is no existing solo "Theotokos" or
"Christ" `Saint` identity anywhere in this data to link them to. Every
other Marian/Christological feast (Nativity, Dormition, Annunciation,
Theophany, Transfiguration, etc.) is already modeled as its own
independent entry, never folded into one trackable person. Creating a
"solo Theotokos"/"solo Christ" identity to absorb these would be a new
modeling decision with much bigger scope (a dozen-plus feasts would be
candidates), not a mechanical application of the Peter/Michael precedent
-- left alone pending an explicit decision if Brian wants to pursue it.

120/120 tests still pass; fixtures regenerated.

## Stage 8: nullable saint, and a real Theotokos identity (2026-07-28)

**`DayCommemoration.saint` made nullable** (migration 0014) so a
commemoration of a relic/icon/event with no appropriate person to attach
to doesn't have to invent one. Since Stage 6's rewire, `day.py` never reads
`dc.saint` at display time -- only `dc.title`/`dc.story` -- so this needed
no changes to `_add_supplemental_commemorations` at all; verified live
(`Day(2026, 7, 2)` still renders "Robe of the Theotokos at Blachernae"
correctly with `saint=None`).

Then Brian refined the Theotokos/Christ distinction from Stage 7: the
Theotokos genuinely is a canonized saint, so a solo `Saint` row for her is
appropriate; Christ is not "a saint" in that category, so his robe stays
`saint=None`. Created a `Saint` for "The Theotokos" and linked "Robe of
the Theotokos at Blachernae" and "Sash of the Theotokos" to it, leaving
"The Placing of the Precious Robe of the Lord in Moscow" unlinked.

Brian then asked for the obvious next step: her own major feasts should
tie to that same identity too. Surveyed every `Saint`/title mentioning
"Theotokos"/"Mother of God" before touching anything, to get the set right
rather than guess -- found 7 clear cases (the Annunciation, Dormition,
Nativity of the Theotokos, Protection, Entry into the Temple, Conception,
and the Dec 26 Synaxis), all now linked to the same `Saint`. Two things
found in the same survey were deliberately excluded rather than assumed:
"Dormition Righteous Anna, Mother of Theotokos" (7/25) is about Anna, the
Theotokos's own mother -- a different person, correctly kept separate --
and four icon-appearance commemorations (Kazan, Tikhvin, Vladimir icons,
and the Synaxis of the "Of the Three Hands" icon) were flagged but not
linked, since an icon's own history feels like a different kind of
occasion than her biographical feasts and wasn't what was actually asked
for -- a decision for Brian if he wants to extend this further.

The Theotokos `Saint` now anchors 9 occurrences across the year (7
biographical feasts + Robe + Sash). 120/120 tests pass on a from-scratch
database each time; fixtures regenerated.

## Stage 9: full-year local-vs-production comparison, and the 6-date Greek gap (2026-07-29)

**Comprehensive comparison** (Brian's explicit request, since production can
handle the load): 365 days x 3 configs (Slavic/Gregorian, Slavic/Julian,
Greek/Gregorian) = 1095 date-configs, ~2200 requests, comparing saints,
feasts, titles, fast/feast level, and readings. Zero diffs outside
`saints` -- strong confirmation nothing else was disturbed. 197
saints-list diffs, all of which resolved to either the known alt_title
dedup bug (149, all on production, already fixed here), genuine additions
from this refactor (34), or two known-good fixes landing on the same date
(5 "mixed" cases).

**Two real bugs found and fixed by this comparison**:
- `summary_title` returned `None` (and crashed the API's Pydantic
  validation with a 500) for the one date in the entire year where a
  composite `Day` has zero titles/feasts/saints at all (Greek/Gregorian,
  Feb 5 -- a pre-existing content gap in the Greek-tradition dataset,
  unrelated to this refactor). Fixed with a `''` fallback.
- The Stage 4 Anthony/Theodosius split reused the same title text for both
  new rows, showing "Ven. Anthony and Theodosius of Kiev Caves" twice in
  the terse list on Sept 2. Gave Anthony's row its own title.

**The 6-date Greek gap, investigated in depth**: 6 dates (Feb 27, May 7,
Jul 5, Aug 9, Oct 31, Nov 23) had their only commemorations tagged
`tradition='slavic'` at the `calendarium.Day` level (not `'common'`),
with an empty parallel `greek` row taking precedence -- meaning Greek
users saw nothing at all, not even genuinely shared content. Checked the
project's own prior Antiochian harvest (`data/antiochian_fixed_saints.json`)
rather than guessing, and found the truth splits three ways per date:
saints genuinely shared by both traditions (should be visible to Greek but
weren't), saints confirmed Slavic-only (Alexis Toth and Alexander Nevsky
are both confirmed absent from the Antiochian calendar entirely -- an
OCA-specific and a distinctly Russian saint respectively), and saints
genuinely Greek-only that this system has never had source content for
(explicitly out of scope per Brian -- "don't create content for saints we
don't already have content for").

**Fixed 5 of 6 dates** using the correct architecture -- retag the whole
`Day` row from `slavic` to `common` (making it visible to both traditions'
queries) and tag the genuinely-Slavic-only `DayCommemoration` rows
`tradition='slavic'` individually (so they're excluded from Greek's
DayCommemoration-level filter while the row itself stays visible for the
shared content) -- plus deleted the now-redundant empty `greek` placeholder
rows that were causing the original invisibility. May 7 (Sergius'
translation of relics + Athanasius of Mt Athos), Aug 9 (Matthias, Anthony,
Herman's Glorification), Oct 31 (the Apostles-of-the-70 group, Nicholas of
Chios), Nov 23 (Amphilochius of Iconium) now correctly show shared content
to Greek while Slavic-only content (Toth, Elizabeth Romanov, Nevsky,
Columban, etc.) stays hidden from Greek.

**A genuine mid-course correction, caught by the existing test suite**:
first tried a parallel-Day-row approach (create a *new* `common` row,
move the shared commemorations onto it, leave the `slavic` row's leftovers
in place) -- this is wrong, because `_prefer_tradition_days` treats a
tradition-specific row as a full replacement for a slot, not a merge, so
Slavic requests would have picked the still-present `slavic` row over the
new `common` one and silently lost the content just moved off it. Caught
by testing directly rather than assuming, reverted, and redone with the
whole-row-retag approach instead (the same lesson Stage 6 already
established, just rediscovered the hard way for Day-row-level tagging
instead of DayCommemoration-level).

**Feb 27 (Raphael of Brooklyn) was retagged and then fully reverted** --
`test_raphael_brooklyn_differing_commemoration_date` (a pre-existing test
from the Greek-tradition-axis project) caught that Raphael is *not*
observed by Greek tradition on this civil date at all -- confirmed via
Antiochian's own typikon, he's kept on the moveable first-Saturday-of-
November instead (`FloatIndex.RaphaelBrooklyn`). The
`antiochian_fixed_saints.json` harvest entry for Feb 27 mentioning Raphael
was misleading (likely a cross-reference on antiochian.org's page, not his
actual commemoration) -- a reminder that a name appearing under a given
date key in that harvest isn't proof of the correct date without
cross-checking, the same lesson as `ref-goarch-chapel`. Since `Day.
feast_name` has no per-tradition granularity, and it must show for Slavic
(where Raphael belongs) but never for Greek on this exact date, the whole
row couldn't be split to also share Procopius (the other saint on that
date) without leaking Raphael's feast_name to Greek too -- reverted Feb 27
entirely rather than force it.

**Residual, deliberately unresolved**: `Day.feast_name` has no
per-tradition granularity at all (unlike `DayCommemoration.tradition`), so
retagging May 7/Oct 31/Nov 23's rows to `common` means Greek users now see
the feast_name text for Toth/Kochurov/Nevsky (all confirmed Slavic-only)
even though the underlying `DayCommemoration` rows are correctly hidden
from them. Three options were surfaced and none picked yet: accept the
minor leak, move those three saints off their feast_name-based headline
treatment onto plain list entries (a Slavic-side display downgrade), or
build real per-tradition granularity for `Day.feast_name` itself (the same
idea as Stage 6's fix, one level up -- a bigger schema change).

New tests: `test_greek_gap_dates_share_confirmed_common_saints`,
`test_alexis_toth_and_nevsky_remain_slavic_only`,
`test_raphael_brooklyn_full_year_check_unaffected`. 123/123 tests pass;
fixtures regenerated.

## Stage 10: decouple DayCommemoration visibility from Day-row winner selection (2026-07-29)

**The Stage 9 fix was itself wrong, caught before it shipped.** Retagging
whole `Day` rows from `slavic` to `common` fixed saint visibility but
conflated it with an unrelated concern: `feast_level`/`fast`/
`fast_exception`/`feast_name` are legitimately whole-day, per-tradition
facts (`_prefer_tradition_days`'s "one row wins the whole slot" semantics
are *correct* for these), while which *saints* are visible is genuinely
additive/mergeable (`DayCommemoration.tradition`, Stage 6). Retagging the
whole row smuggled Slavic's elevated feast/fast levels onto Greek's view
of the same day. Caught by directly re-checking production immediately
after the fix (not assuming it was fine) -- production confirmed
`feast_level=0` for Greek on all 5 retagged dates while local now showed
Slavic's elevated values. Reverted fully (Day rows back to their original
tags, empty greek placeholders recreated with their exact original
fast/fast_exception values re-verified against production) before
redesigning.

**The actual fix**: decouple *where* `_add_supplemental_commemorations`
looks for `DayCommemoration` rows from *where* `_collect_commemorations`
gets its feast-level facts. `_collect_commemorations` now fetches every
`Day` row matching the slot regardless of tradition tag
(`self._commemoration_day_ids`, unfiltered), but still computes `self.days`
(feast_level/fast/fast_exception/feast_name/titles/service_notes) exactly
as before -- tradition-filtered, single-winner via
`_prefer_tradition_days`, zero behavior change for those fields.
`_add_supplemental_commemorations` now queries `DayCommemoration` across
the full `_commemoration_day_ids` set, filtered purely by
`DayCommemoration.tradition` -- meaning a saint attached to a `slavic`-
tagged `Day` row can now be shared to Greek via its own tradition tag,
without Greek also inheriting that row's day-level facts. No Day-row
retagging, no new rows, no data movement -- purely a query change, plus
tagging the same 9 confirmed-shared `DayCommemoration` rows from Stage 9
(this time correctly, with zero collateral risk to feast/fast facts).

**This also cleanly recovered Feb 27** (Raphael of Brooklyn), which Stage
9 had to fully abandon: Procopius is now shared (tagged `common`) while
Raphael, Titus, and Leander stay `slavic`-tagged -- Raphael's feast_name
exclusion from Greek is completely untouched by any of this, since
feast_name still comes solely from `_prefer_tradition_days`'s Day-row
selection, which never changed.

**A second, subtler gap found while re-verifying**: `day_native=True,
ordering=-1` (feast_name-matched) commemorations were previously excluded
from `self.saints` on the assumption "it's already shown via
`self.feasts`" -- true when the commemoration's own `Day` row is the one
whose facts are winning, false when it's shared to a tradition where a
*different* row won (Sergius of Radonezh's translation + Athanasius of Mt
Athos, both feast_name-matched on the `slavic` row for July 5, were
becoming invisible to Greek via *any* channel, since Greek's own winning
row -- the empty placeholder -- has no feast_name of its own to surface
them through). Fixed by checking whether the commemoration's `day_id` is
actually in the winning `self.days` set before excluding it; if not, it
falls back to the plain (`self.saints`) path instead of being silently
dropped.

**A third, unrelated duplicate bug surfaced by the broader query, found
by an existing exact-fixture-comparison test (`test_list_days`) rather
than assumed clean**: 3 saints (Gregory of Nyssa, Ananias of the Seventy,
Zachariah the Recluse) had genuine pre-existing duplicate
`DayCommemoration` rows across two different `Day` rows for the *same*
civil date -- previously silently hidden because the old narrow query
(`day_id__in=[d.id for d in self.days]`) only ever reached one of the two
rows per request. Ananias's case was actually a *deliberate*, tested
duplicate from before `DayCommemoration.tradition` existed (both
traditions needed to see him, so he was duplicated onto both a `slavic`-
and `greek`-tagged row rather than shared via a single `common`-tagged
row) -- confirmed this still works correctly with a single row once
`DayCommemoration.tradition` handles the sharing instead. All 3 de-duped
(content verified identical before deleting either side, per the
established pattern); this Stage 6 blind spot only ever checked greek-vs-
common duplication, never slavic-vs-common, which is exactly why these
three survived undetected until this broader query surfaced them.

Verified directly against production one more time across every affected
date (the 6 gap dates plus the 3 newly-deduped ones): zero field-level
diffs anywhere (feast_level/fast/fast_exception match exactly), and every
remaining saints-list difference traces to an already-understood pattern
(production running behind this codebase's already-tested fixes like
Raphael's differing-date handling, or the long-documented alt_title dedup
bug) -- nothing unexplained. 122/122 tests pass; fixtures regenerated.

**How to apply**: the general lesson from Stages 9-10, worth remembering
for any future tradition-overlay work -- Day-row-level facts (feast_level/
fast/fast_exception/feast_name) and DayCommemoration-level facts (which
saints are visible) are two genuinely independent axes with different
merge semantics (whole-row-replace vs. additive-overlay), and fixing one
by manipulating the other's mechanism (retagging a whole Day row to move
a saint) will eventually smuggle the wrong semantics onto the wrong axis.
Keep them decoupled, the way `_commemoration_day_ids` vs. `self.days` now
does.
