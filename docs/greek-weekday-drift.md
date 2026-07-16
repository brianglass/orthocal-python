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

**Discovered but NOT yet implemented** — several other `FloatIndex` values
are used by the `match`-on-Nativity's-weekday cases for years other than
the ones checked above (e.g. `SatBeforeTheophanyEve`, `SunBeforeTheophanyEve`,
`SatAfterNativityBeforeTheophany`, `SatBeforeNativityEve`,
`SunBeforeNativityEve`, `SunAfterNativityMonday`, `SatAfterNativityFriday`,
`SatBeforeTheophanyJan`, `RoyalHoursNativityFriday`,
`RoyalHoursTheophanyFriday`, `SunForefathers`). These were spotted with only
1-2 independent-year confirmations each during this pass (not the 2+
independent-jump-year bar used for the ones implemented above), and in a
couple of cases (`SatAfterNativityBeforeTheophany`) the one available
sample citation didn't even agree between the two years checked — so
none of these should be touched without further confirmation.

## Next steps (in order)

1. Verify and implement the remaining `FloatIndex` variants listed above,
   with the same 2+ independent-jump-year confirmation bar used for
   `SatBeforeNativity`/`SatBeforeTheophany`, being careful about the
   January year/cycle-mapping gotcha noted above.
2. Design and validate the Forefeast/Afterfeast `FloatIndex` extension
   (Theophany's own variable-count cluster), mirroring the existing
   Nativity `match`-on-weekday structure in `floats`.
3. Re-attack the quantitative trigger (open question, see above) with a
   narrower, more careful approach: rather than testing whole-formula
   hypotheses against multiple years at once, hand-trace a *single* year
   day-by-day from the jump through Triodion, explicitly labeling every
   single day as one of (a) ordinary/universal-table, (b) Typikon-named
   Nativity/Theophany/Circumcision-cluster override, or (c) unrelated
   saint's day (no effect), and see directly, by inspection, exactly which
   days' presence changes the week-count vs. which don't.
4. Once the trigger rule is fully nailed down and validated against all 7
   Nativity-weekday cases, implement it as a new `GreekYear` method,
   structurally parallel to `SlavicYear.reserves`, and wire it into
   `Day.gospel_pdist`/`epistle_pdist` alongside the existing
   `_sunday_gospel_override` hook.
5. Write the Greek-formula test suite (standing task #11) once the above is
   settled.
