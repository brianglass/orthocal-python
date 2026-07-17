# Greek weekday-drift investigation

Status as of this writeup: the fixed-feast portion of the problem is solved
(sections 2-3 below). The "FIFO reserve queue" model from an earlier pass
this session is now **disproven** (section 5) — isolated saints' days have
no effect on subsequent days at all. The exact quantitative mechanism that
connects `lukan_jump` to the Typikon's narrow, named Nativity/Theophany/
Circumcision omission-and-repeat rule remains **unresolved** (section 6).
This document is a checkpoint, not a final design — do not implement a
formula from this session's findings without further verification.

## Background

`GreekYear` (in `calendarium/liturgics/year.py`) already correctly computes
the Lukan-jump Sunday-numbering scheme (`lukan_sunday_numbers`,
`_LUKAN_RESERVED_WINDOWS`, etc.), validated against the official Antiochian
charts. This document covers a separate, still-open problem: the **weekday**
continuous Mark/Luke Gospel/Epistle cycle (as opposed to the Sunday cycle),
specifically in the window from a few days before Nativity through the
Theophany afterfeast.

For ordinary weekdays from the autumn Lukan Jump through ~December 23, the
existing simple formula (`raw_pdist = calendar_pdist + lukan_jump`) is
already provably correct — confirmed by exhaustive brute-force search across
four validation years. The problem is confined to the Nativity-through-
Theophany-afterfeast window, where the simple formula stops working and the
offset (`raw_pdist - calendar_pdist`) changes in a year-dependent way before
settling back to a stable value (confirmed reaching a clean 0 by early
February in at least one validated year).

**Standing constraint from the user:** this must be resolved as a
deterministic algorithm and/or table, not a per-year data overlay harvested
from antiochian.org annually. Antiochian.org data is used only as the
*validation source* for a mechanism that must hold for any year.

## Data and tooling

- `ingest_antiochian.py`'s `Antiochian.get_liturgical_day` had an anchor bug:
  `authenticate()` anchors `itemId 0` to "today," but the anchor date can be
  off by one depending on when the API rolls over relative to when
  `authenticate()` runs. This silently produced an entire harvest (the
  original 2018-2019 window) cached under the *wrong* filenames — every
  cached file's content was for the day *after* its filename date. **Fixed**:
  `get_liturgical_day` now validates `originalCalendarDate` against the
  requested date and re-anchors once if they disagree, raising if they still
  disagree after that. The corrupted 2018-2019 cache was deleted and
  re-harvested; it now validates clean (0 mismatches across 543+ cached
  files, checked directly by comparing filename date to
  `originalCalendarDate` for every file in `data/antiochian_raw/`).
- `data/antiochian_raw/*.json` now has clean winter-window (Nov 1 - Feb 10)
  coverage for all 7 possible Nativity-weekday cases:
  - Tuesday: 2018 (jump=7)
  - Saturday: 2021 (jump=28)
  - Sunday: 2022 (jump=21)
  - Monday: 2023 (jump=14)
  - Wednesday: 2024 (jump=35)
  - Thursday: 2025 (jump=14)
  - Friday: 2026 (jump=7)
- `analyze_drift.py` (repo root, disposable analysis script, not wired into
  the app) computes, for a given `GreekYear`, the per-day offset between the
  naive formula and the actual raw pdist matched against antiochian.org's
  cached Gospel citation for that date. It:
  - Normalizes antiochian.org's `Book C:V-V` citations to this project's
    `Pericope.sdisplay` `Book C.V-V` format.
  - Falls back to a fuzzy match (same book, chapter, start verse within ±2)
    when no exact citation match exists, to handle known single-verse
    citation-boundary variants between traditions.
  - Restricts candidate pdist matches to within ±60 of the naive calendar
    pdist, since the same Gospel text can recur at unrelated pdist values
    elsewhere in the full multi-year cycle table (Saints' commons readings,
    or the cycle simply repeating), and only a nearby match is plausible
    signal for this investigation.
  - **Important limitation**: this ±60 window and the "nearest match wins"
    heuristic occasionally produce spurious single-day matches (e.g. an
    isolated `+28` or `-34` surrounded by consistent `+7` on both sides) —
    treat isolated singleton values as noise, not signal, unless corroborated
    by a title/citation cross-check.

## Confirmed structural findings

### 1. The continuous cycle is a universal, year-independent sequence

The weekday continuous Gospel cycle is not fundamentally "Pascha-relative
pdist" — it is a single, universal, year-independent ordered sequence of
pericopes. Confirmed empirically: the citation at a given `(week number,
weekday)` slot (as labeled by antiochian.org's own `feastDayTitle`, e.g.
"TUESDAY OF THE 14TH WEEK") is identical across every independent year
checked, for weeks 9 through 14 (5-6 different years cross-checked per slot,
zero contradictions) and again for week 16 onward, post-Theophany (e.g.
"16th week Wednesday" = Mark 12:28-37 in both 2022 and 2025, completely
different Nativity weekdays and jump sizes).

The disruption is real but **local and temporary**: it only affects
weeks ~14-16 (the Nativity-to-Theophany-afterfeast span), and every year
re-converges onto the same universal sequence position afterward.

This means what we store today by `pdist` in the `Reading` table already
*is* this universal sequence, just read out under one particular year's
calendar mapping. No new content data is needed for the parts of the season
outside the disrupted window.

### 2. `ByzantineYear.floats` already covers most of the disrupted window

`floats` (in `year.py`) computes, via a `match` on Nativity's weekday, the
pdist for every weekday-dependent anchor around Nativity/Theophany:
`EveNativity`, `SatBeforeNativity`, `SunBeforeNativity`,
`SatAfterNativity`/`SunAfterNativitiy` (+ moved variants), `SatBeforeTheophany`
/`SunBeforeTheophany`, `TheophanyEve`, `SatAfterTheophany`/`SunAfterTheophany`,
and Royal Hours variants — already shared by both `SlavicYear` and
`GreekYear` since it lives on the base class.

Checked against confirmed Greek citations (via `FloatIndex`'s integer value
used directly as `Reading.pdist`):

| FloatIndex | Slavic (existing) | Greek (confirmed) | Status |
|---|---|---|---|
| EveNativity | Luke 2.1-20 | Luke 2:1-20 | matches |
| SatBeforeNativity | Luke 13.18-29 | Luke 13:19-29 | **1-verse variant** |
| SunBeforeNativity | Matt 1.1-25 | Matt 1:1-25 | matches |
| SatAfterNativity | Matt 12.15-21 | Matt 12:15-21 | matches |
| SunAfterNativitiy | Matt 2.13-23 | Matt 2:13-23 | matches |
| SatBeforeTheophany | Matt 3.1-11 | Matt 3:1-6 | **variant (shorter range)** |
| SunBeforeTheophany | Mark 1.1-8 | Mark 1:1-8 | matches |
| TheophanyEve | Luke 3.1-18 | Luke 3:1-18 | matches |
| SatAfterTheophany | Matt 4.1-11 | Matt 4:1-11 | matches |
| SunAfterTheophany | Matt 4.12-17 | Matt 4:12-17 | matches |

Only 2 of 10 need a new `greek`-tagged overlay `Reading` row (same pattern as
the existing Beheading/Nativity-of-Forerunner overlays). 8 of 10 need
nothing at all.

### 3. Fixed month/day feasts are almost entirely already correct

Checked the actual fixed-calendar-date feasts (not weekday-dependent) against
the DB:

| Feast | Month/Day | Existing DB | Confirmed Greek | Status |
|---|---|---|---|---|
| Nativity | 12/25 | Matt 2.1-12 | Matt 2:1-12 | matches |
| Synaxis of Theotokos | 12/26 | Matt 2.13-23 | Matt 2:13-23 | matches |
| Stephen | 12/27 | Matt 21.33-42 | Matt 21:33-42 | matches |
| Nicomedia Martyrs | 12/28 | *(missing)* | Luke 14:25-35 | **needs new row** |
| Holy Innocents | 12/29 | *(missing)* | Matt 2:13-23 | **needs new row** |
| Circumcision | 1/1 | Luke 2.20-21,40-52 | Luke 2:20-21,40-52 | matches |
| Theophany | 1/6 | Matt 3.13-17 | Matt 3:13-17 | matches |
| Synaxis of Forerunner | 1/7 | John 1.29-34 | John 1:29-34 | matches |

Only Nicomedia Martyrs and Holy Innocents are missing outright (OCA doesn't
commemorate them on these dates) — straightforward new fixed-date Reading
rows, same mechanism as the existing Beheading-of-John overlay.

### 4. Forefeast/Afterfeast of Theophany are NOT yet modeled at all

The Forefeast of Theophany (a variable number of days, ~Jan 2-5 depending on
Theophany's weekday) and the Afterfeast (variable days after Theophany) have
no `FloatIndex` entries today — `floats` stops after the core
Nativity/Theophany anchors and Annunciation. Slavic doesn't need this
because OCA apparently doesn't assign distinct Epistle/Gospel overrides
there. This is structurally the same kind of problem `floats` already solves
for Nativity (a weekday-`match`-driven variable-count cluster) and should
very likely be addable the same way — new `FloatIndex` entries plus a
`match` on Theophany's weekday — but this has **not yet been designed or
validated**.

### 5. The "FIFO reserve queue" hypothesis is DISPROVEN

An earlier pass through this investigation (see git history of this file)
believed the mechanism was a `SlavicYear.reserves`-style FIFO queue: content
skipped on a feast-overridden weekday gets deferred and read later, in
strict order, on the next ordinary weekday. Initial data (2021, 2024, 2026)
seemed to confirm this — the first ordinary day(s) after the Nativity
cluster read exactly the "shadow" position (`date_to_pdist(month, day,
year) + lukan_jump`) of Eve, then Nativity, in strict sequence.

**This is now disproven as a general mechanism.** Direct inspection of an
isolated, ordinary (non-Nativity-cluster) saint's day disproves it cleanly:

- **Spyridon of Trymithous (Dec 12)** is a significant, well-known
  hieromartyr-bishop saint (First Ecumenical Council father) whose citation
  (`John 10:9-16`) is confirmed fixed/dominant across every sampled year —
  clearly a genuine override.
- If overrides deferred their content to the next ordinary day (the FIFO
  model), Dec 13 (the very next weekday) should read *Dec 12's* deferred
  content.
- Instead, Dec 13 reads exactly `Mark 9:10-15` — the same, confirmed
  universal "13th week Thursday" content — **in every single year checked**,
  completely independent of what happened on Dec 12.

So an isolated override's content is simply lost for that occurrence, with
**zero effect on any subsequent day.** There is no general-purpose deferred
reading queue for ordinary saints.

This actually reconciles cleanly with the Typikon's own words (see the
Epiphany Leavetaking section, `/tmp/typikon.txt` line ~10086): the
"omission and repeat" rule is explicitly scoped to *"the feasts of the
Nativity or Theophany (including the day before and after each feast) and
the Circumcision"* — a short, named, enumerable list, not "any saint's
day whatsoever." The apparent FIFO behavior seen in 2021/2024/2026 is real,
but it's a special-cased mechanism specific to that named list, not a
general pattern that extends to every override day in the season.

### 6. Open question: the exact quantitative trigger, still unresolved

Given #5, the "backlog" that `lukan_jump` represents must be repaid
specifically through the Nativity-cluster's and Theophany-cluster's own
omissions (the narrow, named Typikon list) — but attempts to make the
arithmetic balance have **not yet succeeded**, and several plausible-looking
formulas have been tested and individually falsified:

- **Total named-weekday count across the whole Nativity-Theophany span**
  (Dec 24 through Leavetaking of Theophany, Jan 14) is roughly constant
  across years (14-15 days) *regardless of `lukan_jump`* (7 through 35) —
  so it cannot be what repays a jump that varies from 7 to 35. This rules
  out "count every named day in the window."
- **Narrowing to just the Typikon's literal named list** (Eve, Nativity,
  Synaxis "day after"; TheophanyEve, Theophany, Synaxis-of-Forerunner "day
  after"; Circumcision — 7 fixed occasions total) caps out at 7 possible
  weekday-landing days, which cannot arithmetically repay a jump of 35
  through simple 1-for-1 day counting either.
- **A pure week-number formula** (attempts included: continuous count from
  Sunday-after-Elevation; count from the jump date itself; count backward
  from `triodion_start`) each produced partial matches but broke down on
  cross-checks:
  - Backward-from-`triodion_start` counting matched cleanly for a short
    window near Triodion (`ts-4` matched exactly between 2021 and 2024
    despite very different jumps and different `triodion_start` values) —
    but completely mismatched by `ts-16` through `ts-25` in the same
    comparison, and the "generic vs. named" classification needed to
    explain *why* it stops working is itself unresolved (see below).
  - A naive "count weeks since the jump" formula gave inconsistent results
    for the identical `week 9 Friday` label falling on very different
    calendar dates in same-jump years (2018 vs. 2026, both jump=7): off by
    one in one direction for one year and matching for the other, with no
    consistent correction found.
- **An empirical "is this date's citation dominant/fixed across
  independent-jump years" classifier** (built from the harvested data,
  filtering out same-jump-year contamination) correctly identified Dec 12
  (Spyridon) as an override — but a crossover simulation built on top of
  this classifier still predicted crossover dates *before Nativity even
  happens* in multiple years, directly contradicting the confirmed flat
  `offset = jump` observed through Dec 21-23. This means the simulation's
  *day-by-day accumulation model itself* is wrong (consistent with #5 — most
  overrides shouldn't accumulate anything at all), not just the classifier.

**Where this leaves us:** the mechanism is real, bounded, and governed by a
short, named list of feast days per the Typikon's own words — but the exact
arithmetic connecting `lukan_jump` (7 to 35, in multiples of 7) to that short
list's effect on the continuous week-count has not been found. This is a
narrower, better-scoped problem than where the investigation started, but it
is **not yet solved**, and no formula should be implemented from this
session's findings without further, careful verification against real dates.

## Implemented (this pass)

The 2 `floats` citation variants and 2 missing fixed-date rows are now
**done**, added as `greek`-tagged `Reading`/`Pericope` rows and baked into
`fixtures/calendarium.json` (regenerated via `dumpdata`, verified: +6
`Reading`, +3 `Pericope`, `Day`/`Composite` untouched, fixture re-parses
cleanly):

- `FloatIndex.SatBeforeNativity` (pdist 1011): existing `common` row
  (`Luke 13.18-29`) retagged `slavic`; new `greek` row added (`Luke
  13.19-29`). Confirmed 7/7 years.
- `FloatIndex.SatBeforeTheophany` (pdist 1022): existing `common` Gospel
  (`Matt 3.1-11`) and Epistle (`1 Tim 3.14-4.5`) rows retagged `slavic`; new
  `greek` rows added (`Matt 3.1-6`, `1 Tim 3.13-4.5`). **Correction to an
  earlier verification bug**: two of my four original confirmation samples
  (labeled 2018 and 2022) were actually checking `SatBeforeTheophanyEve`
  and `SatAfterNativityBeforeTheophany` respectively — different
  `FloatIndex` entries entirely, due to a year/cycle mislabeling bug (see
  below). Re-verified correctly against 2024 and 2025 (2 independent,
  correctly-matched years, different jumps) — still confirms `Matt 3.1-6`
  / `1 Tim 3.13-4.5`.
- Nicomedia Martyrs (Dec 28, new `greek` row): Gospel only (`Luke
  14.25-35`, confirmed 5/5 years). The Epistle varies year to year in the
  harvested data, meaning it isn't a genuine override there — left alone,
  falls through to the ordinary continuous cycle.
- Holy Innocents (Dec 29, new `greek` row): both Epistle (`Heb 2.11-18`)
  and Gospel (`Matt 2.13-23`) confirmed fixed, 5/5 years.
- Confirmed via direct `Day` queries (with `ainitialize()`) that Greek and
  Slavic each resolve to their own variant with no cross-contamination for
  the two float retags. Nicomedia/Innocents correctly show their `greek`
  reading *alongside* the ordinary continuous-cycle reading (not
  suppressing it) — confirmed with the user this matches existing site
  precedent (Stephen, Dec 27, already behaves this way for Slavic; multiple
  applicable readings are listed together with qualifiers, same as how
  oca.org lists multiple Sunday Gospels even though only one is read aloud).

**Caught during this verification pass — a year/cycle-mapping bug in
manual testing** (not a data or code bug): a `GreekYear(Y)`'s own Nativity
falls in calendar year `Y` but its Theophany falls in January of `Y+1`. A
cached file named e.g. `2025-01-04.json` belongs to `GreekYear(2024)`'s
cycle, not `GreekYear(2025)`'s (`GreekYear(2025)`'s January dates are
cached under `2026-01-*.json`). Manually associating January-dated cache
files with the wrong `GreekYear` produced an incorrect `FloatIndex` lookup
and briefly looked like a `_prefer_tradition` dedup bug — it wasn't.
Watch for this specifically whenever hand-checking a January date against
a `GreekYear` instance.

## Implemented (second pass)

Went back through the remaining `FloatIndex` values with the same 2+
independent-jump-year bar, this time also checking the **Epistle** side
(the first pass only checked Gospel citations for most floats — a gap
found and closed this pass) and accounting for the fact that several of
these floats already store **two Reading rows per source** in the DB —
one for each of the two combined observances (e.g. `SatAfterNativity` +
`SatBeforeTheophany` both landing on the same Saturday). All verified by
direct raw-file reads, not the bulk per-year dump script (which turned out
to have a bug — see below), and all baked into `fixtures/calendarium.json`
(regenerated via `dumpdata` inside the `local` Docker Compose service, so
the write persists to the host filesystem; verified +5 `Reading`, +1
`Pericope`, `Day`/`Composite` untouched, fixture re-parses cleanly, full
92-test suite passes with 0 failures via `docker compose run --rm tests`):

- **`SunBeforeNativity` (pdist 1012), Epistle**: existing `common` row
  (`Heb 11.9-10, 17-23, 32-40`) retagged `slavic`; new `greek` row added
  (`Heb 11.9-10, 32-40` — omits the middle clause). Confirmed 5/5
  independent-jump years via direct file reads. Gospel side (`Matt
  1.1-25`) already matched, no change.
- **`SatBeforeNativityEve` (pdist 1015), Gospel**: this combined float (Eve
  of Nativity falling on the same day as Saturday-before-Nativity, when
  Nativity=Sunday) already stores two Gospel rows — one for each combined
  identity. The `SatBeforeNativity`-side row (`Luke 13.18-29`) retagged
  `slavic`; new `greek` row added reusing the same pericope created for
  standalone `SatBeforeNativity` (`Luke 13.19-29`). The `EveNativity`-side
  row (`Luke 2.1-20`) already matched Greek, untouched.
- **`SunBeforeNativityEve` (pdist 1016), Epistle**: same pattern for the
  Nativity=Monday combined case — the `SunBeforeNativity`-side row
  retagged `slavic`, new `greek` row added reusing the same new pericope
  from the point above.
- **`SatAfterNativityBeforeTheophany` (pdist 1017), Gospel + Epistle**:
  the Nativity=Sunday-or-Monday combined float (Saturday-after-Nativity
  coinciding with Saturday-before-Theophany). Confirmed via direct file
  reads that this shows **either** parent identity's own citation
  depending on the year (2022 showed the `SatBeforeTheophany` side, 2023
  showed the `SatAfterNativity` side) — consistent with it being a true
  merge of the two, with antiochian.org's single-citation display just
  picking one. The `SatAfterNativity`-side rows already matched Greek
  (already-confirmed standalone citation); the `SatBeforeTheophany`-side
  rows retagged `slavic` and new `greek` rows added reusing the same
  pericopes created for standalone `SatBeforeTheophany`.
- **`SatAfterTheophany` Epistle re-examined and confirmed correct as-is**:
  the bulk per-year dump script had reported a 2024/2025 split
  (`Eph 6.10-17` vs `Heb 13.7-16`) that looked like a possible variant.
  Direct file reads showed this was a **bug in that script** (it
  misattributed `2026-01-10.json`'s citation, actually `Eph 6.10-17`, to
  something else) — the real data is 4/5 years confirming `Eph 6.10-17`
  (matching the existing `common` row exactly), with only the genuine
  2024 sample as a single unexplained outlier. No change made; this is a
  reminder not to trust that bulk script's exact citation values without
  spot-checking via direct file reads when something looks anomalous.

## Leftover floats: final disposition (no further data possible)

Went back through every item in the "not yet implemented" list above with
a specific goal: for each one, determine whether *more* harvested data
could ever resolve it, and get that data if so. Two important discoveries
about antiochian.org's API along the way:

- **The historical horizon is bounded on both ends.** Forward: dates more
  than roughly a year out fail (confirmed both with the original 2029-2030
  test and, this pass, January 2027 — 6 months past the already-working
  November/December 2026 data). Backward: 2015-2017 and earlier consistently
  fail; 2018 onward works. So "go further back" or "go further forward" is
  not unconditionally available — always check reachability before
  planning a harvest around it.
- **Isolated single-date gaps exist within the reachable window**, distinct
  from the horizon boundary. Harvesting Nov 2020-Feb 2021 (Nativity=Friday,
  jump=14 — otherwise safely reachable) hit exactly one failure, Jan 1, 2021
  (Circumcision) specifically, with every surrounding date fine. Treat a
  single-date failure surrounded by successes as a data gap to skip over,
  not evidence of a horizon boundary.

With that in hand, here's what's resolvable and what isn't:

- **`SunAfterNativityMonday`** and **`SatBeforeTheophanyJan`**: **fully
  resolved, no code change needed.** Both are *provably, permanently*
  masked — checked computationally through 2034, every single occurrence
  of each coincides exactly with a fixed feast (Synaxis of the Theotokos
  Dec 26, and Circumcision Jan 1, respectively) that always wins the
  citation display. No harvested data, past or future, could ever observe
  either float's own identity independently. Their existing inherited
  citations (matching the standalone `SunAfterNativitiy`/`SatBeforeTheophany`
  floats, already confirmed correct) are harmless by construction.
- **`RoyalHoursNativityFriday` / `RoyalHoursTheophanyFriday`**: **out of
  scope for this data source, permanently.** These are 4-part Royal Hours
  services (1st/3rd/6th/9th Hour, each with its own Epistle/Gospel/Prophecy)
  that antiochian.org's simple single `reading1Title`/`reading2Title`
  fields cannot express at all, regardless of how many years are
  harvested. Would need a different source entirely (e.g. a printed
  Antiochian service book) to verify.
- **`SatAfterNativityFriday`** (only occurs when Nativity=Saturday):
  **attempted a code fix, reverted — turns out to be entangled with the
  still-open weekday-drift problem (see below), not independently
  fixable.** Every reachable Nativity=Saturday year (2021, 2027, 2032)
  shares the same jump (28); the next different-jump occurrences (2004,
  2010, 2038+) are outside the reachable window in either direction, so a
  second independent-jump confirmation is provably unobtainable. The one
  sample (2021, `Luke 16:10-15`) doesn't match the plain continuous-cycle
  Gospel for that (week, weekday) slot as originally claimed here — that
  claim was a mistake, based on a mismatched comparison (2022-12-30 is
  actually `Mark 12:1-12`, not `Luke 16:10-15` — corrected on
  re-verification). Implemented `GreekYear.floats` dropping this key so
  the date falls through to the ordinary continuous-cycle formula, then
  checked the *actual* computed output against antiochian.org's real
  citation for that date: they don't match (`Mark 12:1-12` computed vs.
  `Luke 16:10-15` actual). The reason: Dec 31, 2021 is Nativity(Sat)+6 —
  exactly the Leavetaking-adjacent date, squarely inside the disrupted
  window where the simple continuous-cycle formula is already known to be
  unreliable (see "The remaining true unknown" below). Neither the old
  behavior (inherited Slavic-specific citation) nor the fix produces the
  right answer; the real fix depends on solving the weekday-drift trigger
  mechanism first. **Reverted the code change** rather than trade one
  wrong answer for a different wrong answer. Revisit once the weekday-drift
  mechanism is solved.
- **Jan 3 (Forefeast)**: **exhausted, not just under-sampled.** Jan 3 is
  only ever "genuine" (not absorbed into `SatBeforeTheophany`/
  `SunBeforeTheophany`) for 5 of the 7 possible Theophany weekdays — it's
  *structurally* always claimed when Theophany falls on Tuesday or
  Wednesday, the same kind of permanent masking as the two floats above.
  All 5 genuine cases were already sampled before this pass; the 2020
  addition (Theophany=Wednesday) turned out to be one of the 2
  permanently-masked cases, confirming there is no 6th sample obtainable
  in either time direction. The existing 5 samples remain genuinely
  inconsistent (3 different Epistle citations, 2 different Gospels) with
  no pattern found relating to window length, weekday, or anything else
  checked — this needs a different investigative approach entirely (e.g.
  a printed Typikon/lectionary), not more harvesting.

## Forefeast/Afterfeast of Theophany: implemented, and simpler than planned

The original plan (see "Next steps" in earlier revisions of this doc) assumed
this would need a new weekday-`match` `FloatIndex` extension, mirroring how
`floats` handles Nativity's cluster. **It didn't.** Circumcision (Jan 1),
Theophany's Eve (Jan 5, always the day before the fixed Jan 6 feast),
Theophany itself (Jan 6), Synaxis of the Forerunner (Jan 7), and Leavetaking
(Jan 14) are all **fixed calendar dates** — unlike Nativity's Eve/Sat-before/
Sun-before, which genuinely move depending on weekday and thus needed
`floats`'s weekday-`match` machinery. Since every anchor bounding the
Forefeast (Jan 2-5) and Afterfeast (Jan 8-13) windows is fixed, the ordinary
days *inside* those windows are ALSO just fixed calendar dates — no new
`FloatIndex` entries or `match` logic needed at all, just plain `month`/`day`
`Reading` rows (the same mechanism already used for Nicomedia Martyrs/Holy
Innocents).

Checked every date in both windows across 6 independent years (2018, 2021,
2022, 2023, 2024, 2025 — missing only the Nativity=Friday/2026 case, whose
January cache wasn't harvested), reading only the "genuine" occurrences (a
few of these dates get absorbed into the existing `SatBeforeTheophany`/
`SunBeforeTheophany`/`TheophanyEve`/`SatAfterTheophany`/`SunAfterTheophany`
floats in some years, i.e. when Jan 2/3/4 or Jan 8/9/10/11 happens to land
on a Saturday or Sunday that year):

- **Jan 2** (Epistle only): `Heb 5:4-10` confirmed 5/5, zero outliers —
  implemented. Gospel is messier: 4/5 confirm `John 3:1-15`, but the
  Nativity=Tuesday/2018 sample (the only Theophany=Sunday case in the
  dataset) shows `Mark 1:1-8` instead. Implemented anyway given the strong
  majority and a plausible explanation (unique weekday case), but flagged
  as the one soft spot in this pass.
- **Jan 4** (both Epistle + Gospel): `1 Cor 4:9-16` / `John 1:18-28`,
  confirmed 4/4 each, zero outliers. Implemented.
- **Jan 8, 9, 10, 11, 12, 13** (all both Epistle + Gospel): every single one
  confirmed 4/5 or 5/5 with **zero outliers** — `Rom 6:3-11`/`John 3:22-33`,
  `2 Tim 2:1-10`/`Mark 1:9-15`, `Eph 4:7-13`/`Luke 3:19-22`,
  `Heb 13:7-16`/`Luke 4:1-15`, `Acts 18:22-28`/`John 10:39-42` (new pericope,
  didn't already exist), `Gal 3:23-4:5`/`Luke 20:1-8`. All implemented.
- **Jan 3 explicitly excluded**: both Epistle and Gospel are genuinely
  inconsistent across years (3 different Epistle citations across 5
  samples, 2 different Gospel citations), with no pattern found relating
  the differences to window length, weekday, or anything else checked.
  **Update**: this has since been confirmed exhausted, not just
  under-sampled — see "Leftover floats: final disposition" below. All 5
  possible genuine samples are already in hand; no amount of further
  harvesting can add a 6th.

All added as new `greek`-tagged `month`/`day` `Reading` rows (`pdist=999`,
`ordering=821`/`921`, matching the Nicomedia/Innocents pattern), shown
*alongside* whatever else applies that date (e.g. a Saturday landing on
Jan 4 shows both the `SatBeforeTheophany` float's reading and the Jan 4
Forefeast reading together) — consistent with the established "list every
applicable reading, don't suppress" precedent. Verified via `dumpdata`
(+16 `Reading`, +1 `Pericope`, `Day`/`Composite` untouched, fixture
re-parses cleanly) and the full 92-test suite (0 failures) via Docker.

## Next steps (in order)

The leftover-floats investigation is now closed out — see "Leftover
floats: final disposition" above for the conclusive status of each item
(2 permanently resolved with no code change, 1 permanently out of scope,
1 confirmed entangled with the still-open weekday-drift problem below and
not independently fixable, 1 confirmed exhausted). Remaining work:

1. Re-attack the quantitative trigger (open question, see above) with a
   narrower, more careful approach: rather than testing whole-formula
   hypotheses against multiple years at once, hand-trace a *single* year
   day-by-day from the jump through Triodion, explicitly labeling every
   single day as one of (a) ordinary/universal-table, (b) Typikon-named
   Nativity/Theophany/Circumcision-cluster override, or (c) unrelated
   saint's day (no effect), and see directly, by inspection, exactly which
   days' presence changes the week-count vs. which don't.
2. Once the trigger rule is fully nailed down and validated against all 7
   Nativity-weekday cases, implement it as a new `GreekYear` method,
   structurally parallel to `SlavicYear.reserves`, and wire it into
   `Day.gospel_pdist`/`epistle_pdist` alongside the existing
   `_sunday_gospel_override` hook. This should also resolve
   `SatAfterNativityFriday` as a side effect, once the disrupted-window
   content is correctly computed.
3. Write the Greek-formula test suite (standing task #11) once the above is
   settled.
