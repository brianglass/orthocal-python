# Greek weekday-drift investigation

**Status: REOPENED 2026-08-25.** See "REOPENED (2026-08-25): the day labels
are Greek's own lectionary index" at the end of this document. In short: every
earlier pass resolved Greek citations by matching them against this project's
Slavic-built `pdist` table, and antiochian.org was publishing Greek's own
lectionary slot index the whole time, in a JSON field no pass ever read. Using
it, the ordinary weekday formula is now pinned exactly (zero exceptions across
303 labeled days in 9 cycles), the disruption is identified as a pointer
*suspension* rather than a drift, and the remaining gap is measured at 20 days
across 7 cycles — concentrated on just three calendar dates (Jan 19, 24, 26).
goarch.org was also read for the first time, which showed the app is already
correct in February and that GOA and antiochian.org genuinely disagree on the
contested days. The harvest was then extended to 27 cycles (2011-2037), which
established that **GOA's own software does not compute the contested days
either** — a human curates them from the annual ordo out to the published
Kanonion horizon, and past that the site falls back to a commons Gospel. See
"GOA harvest extended" at the very end. That section also identifies an
unlimited, noise-free oracle for the one mechanism still worth modelling.
The sections below are retained as written; where they conflict with the new
section, the new section supersedes them.

**Previous status: CLOSED.** The fixed-feast portion of the problem is fully solved
and implemented (sections 2-3, 7-8 below, plus the 18-saint Jan 15 - Feb 10
Menaion set added in the final pass). The genuine "free weekday" content in
that same window — the handful of days per year (0-5, see the corrected
count in "Known scope of remaining incorrectness" below) where no fixed
saint claims the slot and the site would otherwise need to compute an
ordinary continuous-cycle Gospel/Epistle for Greek specifically — turned out
**not to be solvable from the sources available to this project**. See
"Final disposition: the unsolved recovery mechanism" at the end of this
document for the full account of why, and what was implemented instead. The
window is confirmed fully bounded between the Theophany-afterfeast cluster
and each year's own Triodion start -- it does not extend further into
February in low-`lukan_jump` years (see "Feb 11+ question: RESOLVED").

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

### 7. BREAKTHROUGH: identified the actual mechanism — recovered Matthew-Sunday Gospels, not continuous-cycle drift at all

A fresh hand-trace of 2024 (jump=35, Nativity=Wednesday) and 2022 (jump=21,
Nativity=Sunday) found that almost every "unexplained variation" day
discovered in earlier passes was contaminated by dates that are actually
**fixed** Menaion readings coincidentally matching unrelated content
elsewhere in the table (see the corrected disposition of `SatAfterNativityFriday`
above — the same class of mistake). Systematically checking dominance ratios
across 3-5 independent-jump years for every day in Jan 15-31 shows almost
the entire window is fixed (`Luke 12:32-40` for Paul of Thebes Jan 15,
`John 21:14-25` for Jan 16, etc.) — only Jan 19, 24, and 26 show genuine
year-to-year variation, plus Jan 14 (Leavetaking of Theophany, which per the
Typikon explicitly reads "the daily" and so is expected to vary).

**What that genuine variation actually is.** On Jan 19/24/26, the Epistle
frequently stays *fixed* (`Gal 5:22-26; 6:1-2`, a commons-of-an-ascetic
reading) while the *Gospel* varies. Resolving those varying Gospel citations
against the `common`/`slavic` `Reading` table (unrestricted — no plausible-
window filter) finds **exact, unambiguous, single-candidate matches**, but at
pdist positions far outside any plausible "drift" range — e.g. for the 2022
cycle, Jan 19/24/26 resolve to pdist 147/154/161 respectively (`Matthew
22:2-14`, `22:35-46`, `25:14-30` — the parable of the wedding feast, the
great commandment, and the parable of the talents). Those three pdist values
are exactly one week apart and **all three are Sundays** in the common table.

The critical check: harvesting antiochian.org directly for the *actual*
autumn 2022 Sundays at those same pdist positions (Sept 18, 25, Oct 2 —
easy to do, previously never harvested since the project's harvest windows
were always winter-only) shows Greek did **not** read that Matthew content
live on those dates at all:

- pdist 147 (Sept 18, 2022): `SUNDAY AFTER HOLY CROSS`, `Mark 8:34-38; 9:1`
  — a fixed feast-day reading, not an ordinary numbered Matthew Sunday.
- pdist 154 (Sept 25, 2022, = `first_sun_luke` for this year):
  `1ST SUNDAY OF LUKE`, `Luke 5:1-11`.
- pdist 161 (Oct 2, 2022): `2ND SUNDAY OF LUKE`, `Luke 6:31-36`.

So Greek's own real-time calendar reads **Luke** on those calendar Sundays,
confirmed genuinely — nothing was "skipped and deferred." What's stored in
the `common`/`slavic` `Reading` table at those same pdist positions is
**Slavic's own** Matthew-Sunday content, because Slavic's jump to Luke
happens much later than Greek's (Slavic waits for a full 17 weeks of
Matthew; Greek jumps on a fixed date tied to Elevation regardless of where
Matthew's count stands). The two traditions are reading *different* content
on the *same* pdist positions past the jump point — Luke for Greek, Matthew
(continuing) for Slavic — purely because their Sunday-numbering schemes
diverge from `first_sun_luke` onward.

**The mechanism, matching the Typikon's own words exactly**
("after we finish the readings from St. Luke, we return to St. Matthew and
count the weeks that are left from the Sunday after the Elevation of the
Holy Cross"): the Matthew-Sunday-designated Gospels that a longer,
Slavic-style Matthew season *would* have read as Sundays, but that Greek's
earlier jump bypassed, are **not lost** — they get recovered and read later
as **ordinary weekday Gospels**, one per available (non-major-feast)
weekday, in strict chronological order, starting once the fixed Nativity/
Theophany cluster clears (first observed slot varies by year — Jan 14
Leavetaking or the first free weekday after). Weekday alignment is *not*
preserved (pdist 147/154/161, whatever weekday they originally were, land on
Thu/Tue/Thu in January) — it's a straight FIFO drain of the backlog, not a
day-matched substitution.

**The count matches `lukan_jump / 7` in the one case fully checked**: 2022
(jump=21, expect 3) showed exactly 3 recovered Sunday-Gospels (147, 154,
161) landing on Jan 19/24/26. This lines up with `lukan_jump`'s own
construction (`calendar_pdist + lukan_jump` = a fixed universal target, i.e.
`lukan_jump / 7` literally counts how many weeks early Greek's jump lands
relative to where a 17-week Matthew season would have put it) — so
`lukan_jump / 7` is the natural, well-motivated prediction for the backlog
size in every year, not a coincidence specific to 2022.

**Confirmed against 2 more distinct jump values.** 2018 (jump=7, predict 1):
found exactly 1 (Jan 24 → pdist 98, `Matthew 9:27-35`) — exact match. 2021
(jump=28, predict 4): found 3 clean instances (Jan 19/24/26 → pdist
140/147/154, each exactly 7 apart, all confirmed Sundays), one short of the
predicted 4. The likely 4th is masked behind `Matthew 10:1, 5-8` — a
citation that shows up as completely unmatched (`content_at_pdist` returns
`[]`) on the last remaining recovery-eligible weekday in *every* year
checked so far (2019-01-31, 2022-01-31), including years with different
jumps — consistent with it being a genuinely Greek-specific pericope (there
is no `Matt 10:1-8`-range row anywhere in the `Pericope` table at all, of
any tradition) rather than a disconfirmation. Net: 1-for-1, 3-for-3 (twice,
independently), and 3-of-4 with a plausible explanation for the gap — strong
enough to treat `lukan_jump / 7` as the working formula for the recovery
count, though the true count should be double check once that Matthew
10:1-8-range pericope is sourced and added.

**Starting point: CONFIRMED, straight from the Typikon's own text.**
`/tmp/typikon.txt` line 10086-10088 states the rule explicitly: "On
weekdays, after we finish the readings from St. Luke, we return to St.
Matthew and **count the weeks that are left from the Sunday after the
Elevation of the Holy Cross**." That anchor — "the Sunday after Elevation"
— is the *1st* Sunday after Elevation, one week before `first_sun_luke`
(which is the *2nd* Sunday after Elevation, where Greek's jump actually
happens). Checked algebraically against all 8 years with computed
`elevation`/`first_sun_luke` values (2018, 2020-2026): in every single case,
`first_sun_luke - 7` equals the first Sunday strictly after `elevation`,
regardless of what weekday Elevation itself falls on. This matches the
observed recovery-queue starting points exactly: 2022's queue is {147, 154,
161} and 147 = `first_sun_luke(154) - 7`; 2021's queue is {140, 147, 154}
and 140 = `first_sun_luke(147) - 7`. **The recovery queue starts at
`first_sun_luke - 7`, not at `first_sun_luke` itself**, and proceeds forward
one week at a time from there.

**Apparent complication, investigated and RESOLVED as a false alarm: Jan 14
(Leavetaking of Theophany) is its own fixed reading, not a second
mechanism.** Initially, checking Leavetaking's Gospel across 7 years showed
`Luke 4:1-15` in 5 of them but `Matthew 4:1-11`/`4:12-17` in 2 others
(2023, 2024) — which looked like evidence of a second, independent
continuous weekday sequence. The actual explanation: **those two samples
weren't ordinary weekday occurrences of Leavetaking at all.** Checking the
real weekday of Jan 14 in each source file: 2023-01-14 is a **Saturday**
and 2024-01-14 is a **Sunday** — and the Typikon (lines 9964-9979) gives
Leavetaking-on-Saturday and Leavetaking-on-Sunday their own entirely
different rules (Saturday reads "Saturday after Epiphany"; Sunday gets its
own full service), completely unrelated to the ordinary "reads the day's
Epistle/Gospel" rule that applies when Leavetaking is a plain weekday. Once
those two contaminated samples are excluded and only genuine weekday
occurrences are compared (2019 Monday, 2021 Thursday, 2022 Friday, 2025
Tuesday, 2026 Wednesday — five different weekdays, five different jump
values), **all five show the identical citation, confirmed both Epistle and
Gospel: `Acts 2:38-43` / `Luke 4:1-15`.** Leavetaking-on-an-ordinary-weekday
is simply a fixed reading, exactly like every other fixed date already
implemented in this project — no second mechanism, no interleaving puzzle.
(The Saturday/Sunday special cases likely already resolve correctly via the
existing `SatAfterTheophany`/`SunAfterTheophany` float machinery, but that
should be double-checked separately — out of scope for the recovery-queue
question this section is about.)

**The ordinary continuous weekday formula, directly confirmed via harvest
data.** Harvested the full Nov-Dec 2022 window (jump=21) and checked every
weekday's Gospel citation against the shared `common`/`slavic` table,
unrestricted. Result: from early November straight through Dec 23, *every*
weekday resolves to an exact, unambiguous match at exactly `calendar_pdist +
lukan_jump` — `Luke 11:42-46` etc. in November, transitioning seamlessly
into `Mark` content by mid-December (`Mark 8:22-26`, `9:33-41`, `10:11-16`,
etc.), all at offset exactly `+21`. This is the direct confirmation of the
very first finding from early in this investigation ("offset = jump, flat
through Dec 21-23") — now fully explained: Greek reads the *identical*
shared Matthew→Mark→Luke weekday sequence Slavic uses, just permanently
`lukan_jump` days ahead of it, for the entire autumn/early-winter span.
(One single date, Dec 27, briefly looked like an early recovery-queue hit —
`Matthew 21:33-42`, matching Sunday-pdist 140 — but is confirmed fixed for
St. Stephen's own commemoration across 5 independent-jump years regardless
of jump value; another instance of the same coincidental-text-reuse
gotcha as the Jan 13/Jan 31 false positives above, not a genuine hit.)

Checked how far this shared continuous material extends in the `Reading`
table: Gospel entries stop dead at pdist 279 (a Saturday, `Luke 18:2-8`) —
nothing beyond that in the 276-300 range. For the 2022 cycle, the
`calendar_pdist + jump` pointer would cross that boundary (need pdist 280+)
right around calendar_pdist 259 (~Jan 7) — squarely inside the Jan 1-18
fixed-feast-cluster blackout window, so this exact crossover is never
directly observable (every candidate day in that stretch is already a
confirmed fixed date). Practically this doesn't matter: by the time the
first free weekday appears (Jan 19), the recovery queue is already firmly
in effect, and nothing in the blackout window depends on knowing the exact
crossover day.

**Full season picture, now coherent end-to-end:**
1. Before Nativity through ~Dec 30: ordinary continuous weekday formula,
   `calendar_pdist + lukan_jump`, confirmed directly.
2. ~Jan 1-18: the fixed Nativity/Theophany/Forefeast/Afterfeast/Leavetaking
   cluster (already implemented per earlier sections + this session's Jan
   14 finding) masks whatever the underlying pointer is doing.
3. First free weekday after the cluster clears (e.g. Jan 19 in 2022):
   Sunday-Gospel recovery queue takes over, draining `lukan_jump / 7` items
   starting at `first_sun_luke - 7`, one per available weekday.
4. Once the recovery queue is drained: offset converges to exactly 0 (Feb
   4/5/7 in the 2022 cycle) — Greek reading in perfect lockstep with
   Slavic's own continuous position from then on.

**Count still not fully nailed down.** 2024 (jump=35, predicting 5
recovered Sundays) still only shows 1-2 unambiguous instances (Jan 24 →
pdist 70; Jan 14 is now excluded per the paragraph above, not a recovery
instance). 2021 (jump=28, predicting 4) shows only 3 (140/147/154, missing
161/`Matthew 25:14-30`) — checked the obvious candidate slot (Jan 31,
`Matthew 10:1, 5-8`) and ruled it out: that citation is confirmed fixed for
Jan 31 in 6 of 7 independent years regardless of jump size (the one
exception, 2021-01-31, is a genuine Sunday that year and shows `Luke
19:1-10`/Zacchaeus instead, per the Typikon's separate "Sundays between
Epiphany and Triodion" rule two paragraphs above the recovery rubric — an
unrelated mechanism). So the 4th 2021 instance is genuinely unobserved in
the harvested window (Jan 3 - Feb 9), not hiding under a mislabeled fixed
day. Best working theory: the Typikon's own boundary condition ("we do the
same...until we begin the Triodion") caps the recovery queue — if fewer
than `jump/7` free (non-fixed-feast) weekdays exist before that year's
Triodion start, the excess is genuinely dropped, not carried further.
2021's `triodion_start` (287) is close to the edge of the harvested window
(283 = Feb 9), consistent with this, but not yet verified by harvesting
further into February. Also still open: whether the Epistle side is ever
touched by the recovery queue at all (Jan 19/24 evidence says no — the
day's own commons-of-a-saint Epistle stays put and only the Gospel slot is
overridden).

This finding **supersedes** most of \#6 above: the "quantitative trigger"
being sought was never a week-count-repayment formula acting on the
Nativity/Theophany override list. It's a distinct, additive recovery queue,
structurally the sibling of `SlavicYear.reserves` (which defers skipped
**Luke** Sundays for later re-insertion as Sundays) — Greek instead defers
skipped **Matthew** Sundays for later re-insertion as weekdays.

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

The leftover-floats investigation is closed out — see "Leftover floats:
final disposition" above. The quantitative-trigger question (\#6) has been
superseded by the recovered-Matthew-Sunday-Gospel mechanism found in \#7.
Remaining work:

1. The mechanism is now understood end-to-end (see the "Full season
   picture" at the end of #7): ordinary continuous `calendar_pdist +
   lukan_jump` weekday formula through ~Dec 30, the already-implemented
   fixed cluster through ~Jan 18, then the Sunday-Gospel recovery queue
   (starting at `first_sun_luke - 7`, draining `lukan_jump / 7` items) for
   the remaining disrupted days, converging to offset 0 once drained. The
   earlier "second mechanism" concern (Jan 14 Leavetaking) was a false
   alarm — resolved as its own fixed reading, no interleaving puzzle.
   Two minor items remain, neither blocking implementation:
   a. Confirm the `lukan_jump / 7` recovered-Sunday-count formula and its
      Triodion-boundary cutoff against one more distinct jump value where
      more February data can be harvested (2021's missing 4th instance is
      consistent with running out of free days before Triodion, not a
      formula error, but this needs verifying by harvesting further into
      February for a similar case).
   b. Confirm whether the recovery queue ever touches the Epistle slot
      (current evidence says no — only Gospel; the day's own
      commons-of-a-saint Epistle stays put).
   c. Double-check the Leavetaking-on-Saturday/Leavetaking-on-Sunday
      special cases (2023, 2024 in the sample) resolve correctly via the
      existing `SatAfterTheophany`/`SunAfterTheophany` float machinery —
      not investigated in this pass, low risk since those floats are
      already confirmed elsewhere in this document.
2. Once the count/ordering rule is fully nailed down and validated across
   multiple jump values, implement it as a new `GreekYear` method,
   structurally parallel to `SlavicYear.reserves` (this is genuinely the
   same *kind* of mechanism — a deferred-Sunday-Gospel recovery queue —
   just deferring Matthew instead of Luke, and re-inserting as weekdays
   instead of Sundays). Wire it into `Day.gospel_pdist` alongside the
   existing `_sunday_gospel_override` hook. This should also resolve
   `SatAfterNativityFriday` as a side effect, once the disrupted-window
   content is correctly computed.
3. Write the Greek-formula test suite (standing task #11) once the above is
   settled.

## Final disposition: the unsolved recovery mechanism

The `matthew_sunday_recovery_queue`/`weekday_recovery_assignments` formula
described in the "Next steps" section above (`first_sun_luke - 7`, stepping
forward by 7, count = `lukan_jump // 7`) was implemented, wired into
`GreekYear`/`Day.gospel_pdist`, and then **disproven** by testing against 2
more independent jump values before being trusted:

- **2018 (jump=7, predicting 1 item)**: the one genuine free-day hit
  (Jan 24 → `Matthew 9:27-35`) resolves to Matthew-Sunday number **n=7**
  (`49+7n=98`), not the predicted n=16 (`first_sun_luke-7=161`). Off by 9
  weeks, in the wrong direction to be an indexing bug.
- **2023 (jump=14, predicting 2 items)**: **3** genuine free-day hits were
  found (Jan 19/24/26 → pdist 133/112/147, i.e. Matthew-Sunday numbers
  n=12, n=9, n=14) — wrong count, and not even in ascending date order.
- The "convergence to ordinary content" offset that follows the free days
  also varies by year in a way `lukan_jump` alone doesn't explain: 0
  (2022), -35 (2023), -154 (2018) at the same relative point in the season.
- Checked whether `triodion_start` (which varies independently of
  `lukan_jump`, since it depends on the *following* year's Pascha) was the
  real hidden variable instead — confirmed it clearly matters (2023 and
  2025 both have jump=14 but 6.00 vs. 2.57 weeks of "runway" between
  Leavetaking and Triodion) but a clean formula combining it with
  `lukan_jump` was not found.
- antiochian.org's own day labels for this window ("15th week Wednesday",
  "17th ... after Pentecost") don't match this project's own Slavic-built
  pdist positions consistently either — e.g. a citation labeled "17th
  Tuesday after Pentecost" resolves (via exact, unambiguous DB lookup) to
  a pdist this project's own numbering calls "the 15th Sunday of Matthew".
  This strongly suggests antiochian.org computes this specific content via
  its own internal week-counting system, independent of the shared table
  this project maintains — meaning the "matches" driving this whole
  investigation are very likely coincidental text reuse between two
  different, undocumented algorithms, not evidence of one real mechanism.

**The code was reverted** (`GreekYear`/`Day.gospel_pdist` changes fully
removed, confirmed via `git diff --stat` showing no diff) rather than ship
a formula that fails on the two most common jump values (7 and 14).

**The Typikon was re-read specifically looking for a weekday-equivalent to
the detailed Sunday table** it gives for "Sundays between Epiphany and the
Triodion" (the `_THEOPHANY_INTERPOLATION` table already implemented, quoted
in full at lines 10059-10089). Checked the "Order of Daily Services"
chapter (Ch. II, pages 40-46) — it only says generically "the daily
readings from the Epistle and Gospel" without specifying the assignment
rule. Searched for every other occurrence of the "readings for..." heading
style used by the Sunday table — none analogous exists for weekdays. The
two sentences already quoted throughout this document (line 10086-10088)
are the **complete extent** of what this Typikon says about the mechanism;
the day-by-day arithmetic apparently lives only in an actual annual
lectionary chart/ordo — exactly what antiochian.org's own system evidently
computes from, but not something this project has access to in tabulated
form.

**Conclusion: not solvable with the sources currently available.** Per
explicit user direction, this narrow gap (2-4 weekdays per year, only in
some years, only when no fixed Menaion saint already claims the slot) is
accepted as a known, documented limitation rather than guessed at. Nothing
was implemented for it, and `Day.gospel_pdist` continues to fall through to
the existing (Slavic-oriented) `next_pascha`-relative computation on those
specific days for Greek — not verified correct for Greek, but the least-bad
available default, and never worse than what a wrong formula would have
produced.

## Implemented (final pass): the 18-saint Jan 15 - Feb 10 Menaion set

While investigating the above, the "claimed" (fixed, jump-independent)
Menaion saints filling nearly all of the Jan 15 - Feb 10 window were
already fully identified and multi-year confirmed (5 independent years
each, 4/5 for Feb 6 with an explained exception — see below). Since these
are ordinary fixed-calendar-date commemorations wholly unrelated to the
unsolved recovery-mechanism question above, they were implemented on their
own merits:

- **18 dates**: Jan 15, 16, 18, 20 (Epistle only), 21, 22, 23, 25 (Epistle
  only), 28, 29, 31, Feb 1, 6, 8, 10. (Jan 17, 27, 30 already matched the
  existing `common` row exactly, confirmed earlier this session — no
  change needed. Jan 20 and Jan 25 needed only their Epistle changed; the
  Gospel already matched.)
- **Feb 6 exception, explained**: 1 of 5 years (2026) shows a different
  saint entirely (`Julian of Homs`, an Antiochian-regional commemoration)
  outranking Photius that particular year — not contamination, a genuine
  locally-significant competing commemoration. Implemented on the 4/5
  majority (Photius: `Heb 7:26-28; 8:1-2` / `John 10:9-16`).
- **Pericope reuse, not duplication**: of the 20 Gospel+Epistle citations
  needed beyond the 3 already-matching dates, 18 already existed in the
  `common`/`slavic` `Pericope` table under an equivalent citation notation
  (several only found after checking a *dash-range* form against the
  antiochian.org *semicolon-separated* form, e.g. `Heb 7:26-28; 8:1-2` ==
  existing `Heb 7.26-8.2`, id 768 — same verses, different citation
  style). Only **2 genuinely new** `Pericope` rows were needed: `John
  21.14-25` (Jan 16 Gospel) and `2 Tim 1.3-8` (Jan 22 Epistle — a
  1-verse-boundary variant of the existing `2 Tim 1.3-9`, treated as a
  genuine Greek-specific divergence per the established precedent of the
  Beheading-of-John-the-Baptist Acts 13:25-32 vs. 13:25-33 case).
- **2 retags**: the existing `common` Epistle rows for Jan 20 (`Heb
  13:17-21`, shared with several *other*, unrelated saints via the same
  generic "commons of a monastic saint" pericope — only the Jan 20 row was
  retagged, not the shared pericope's other uses) and Jan 25 (`1 Cor
  12:7-11`) were retagged `slavic`; new `greek` rows added pointing to the
  confirmed citations (`2 Cor 4:6-15` and `Heb 7:26-28; 8:1-2`
  respectively).
- Verified via `Day` queries: Greek correctly shows the new dedicated
  row *alongside* the ordinary `common` continuous-cycle row (consistent
  with the established "list every applicable reading" precedent); Slavic
  is unaffected except at the 2 retagged dates, where it now shows its own
  distinct citation instead of what was actually Greek's.
- `fixtures/calendarium.json` regenerated via `dumpdata` inside the `local`
  Docker Compose service: **+2 `Pericope`, +28 `Reading`**, `Day`/
  `Composite` untouched. Full 92-test suite passes (0 failures, 1 skipped)
  via `docker compose run --rm tests`.

## Known scope of remaining incorrectness

Quantified precisely rather than left vague, since "how many days will be
wrong" is the practical question that matters going forward. First,
directly confirmed the current fallback is genuinely wrong, not just
unverified: for **2022-01-19** (a confirmed weekday, jump=21), the app
currently computes `Epistle: Jas 1.1-18` / `Gospel: Mark 8.30-34` for
Greek — the actual antiochian.org citation for that date is `Gal 5:22-26;
6:1-2` / `Matthew 21:33-42`, confirmed independently earlier in this
document. Completely different content, not a near-miss.

**Per-year day count**, computed directly (every weekday between
Leavetaking of Theophany and that year's Triodion start, minus the 18
now-implemented fixed Menaion dates, minus Saturdays/Sundays which are
handled by separate, already-correct mechanisms), for 2018-2037:

**Correction (Feb 11+ investigation, below):** the original version of this
table double-counted several dates. Jan 19/24/26 and Feb 4/5/7/9 are fixed
*calendar* labels carried over from the sample years where each was first
confirmed wrong on a weekday — but the same calendar date falls on a Sunday
in other years, where it's governed by the already-fixed Sunday-numbering
mechanism (`sunday_gospel_override`), not this unsolved weekday mechanism.
Corrected below (struck entries were miscounted as weekdays):

| Year | jump | Nativity weekday | free (likely-wrong) weekdays in Jan15-Feb10 | extends past Feb 10? |
|---|---|---|---|---|
| 2018 | 7  | Tue | 1 (Jan 24) | no — see below |
| 2019 | 28 | Wed | 4 (Jan 24, Feb 4/5/7) | no |
| 2020 | 14 | Fri | 2 (Feb 4/5) — ~~Jan 19/26, Feb 9 are Sundays~~ | no — see below |
| 2021 | 28 | Sat | 4 (Jan 19/26, Feb 4/9) — ~~Jan 24, Feb 7 are Sundays~~ | no — plus `SatAfterNativityFriday` (Dec 31) |
| 2022 | 21 | Sun | 3 (Jan 19/24/26) | no |
| 2023 | 14 | Mon | 5 (Jan 19/24/26, Feb 7/9) — ~~Feb 5 is a Sunday~~ | no — see below |
| 2024 | 35 | Wed | 3 (Jan 24, Feb 5/7) — ~~Feb 4 is a Sunday~~ | no |
| 2025 | 14 | Thu | 0 — ~~Jan 19/26 are both Sundays~~ | no |
| 2026 | 7  | Fri | 5 (Jan 19/26, Feb 4/5/9) | no — see below |

(Full 20-year table generated via a direct script walking
`weekday_from_pdist` over each `GreekYear`'s Leavetaking-to-Triodion span;
not reproduced here in full — see the git history of this doc's authoring
session for the exact command if needed. The Sunday miscounts above were
caught by checking each listed date's real weekday directly against Python's
stdlib `date.weekday()`, independent of this project's own code.)

**Bottom line**: a typical year has **0 to 5 confirmed-wrong weekdays**
(previously reported as 3-7, before the Sunday-miscount correction above),
concentrated in Jan 19 - Feb 9. Two additional, smaller items apply on top:

- **Jan 3 (Forefeast)**: uncertain in roughly 5 of 7 years (whenever
  Theophany's weekday doesn't cause it to be absorbed into
  `SatBeforeTheophany`/`SunBeforeTheophany`) — the 5 independently-sampled
  years disagreed with no pattern found (see "Leftover floats" above), so
  this may already be correct by chance, or may not be.
- **`SatAfterNativityFriday`** (Dec 31): confirmed wrong, but only in
  Nativity-falls-on-Saturday years (2021, 2027, 2032 in the near term —
  roughly 1 year in 7).

**Feb 11+ question: RESOLVED, not a gap.** The "extends past Feb 10"
years (2018, 2020, 2023, 2026) don't actually extend the unsolved window —
they just reach **Triodion start** (the Sunday of the Publican and
Pharisee, always exactly pdist -70) at a later calendar date than usual:
2018-01-28, 2020-02-09, 2023-02-05, 2026-02-01. Once a date crosses that
boundary it's inside the ordinary Meatfare/Cheesefare pre-Lenten season,
which is fixed, Pascha-relative content already shared with `SlavicYear` —
confirmed by harvesting the actual post-Feb-10 dates for all three low-jump
years with real gaps (2018, 2020, 2023) and checking for cross-year
agreement:

- 2018-02-12/13 ("Cheesefare Monday/Tuesday") = 2023-02-20/21 ("Cheesefare
  Monday/Tuesday"): identical citations both years (`3 John 1:1-15` / `Luke
  19:29-40; 22:7-39`, and `Jude 1:1-10` / `Luke 22:39-42,45-71; 23:1`).
- 2020-02-18 ("Meatfare Tuesday") = 2023-02-14 ("Meatfare Tuesday"):
  identical (`1 John 3:9-22` / `Mark 14:10-42`).

Same pattern as the already-confirmed Nov-Dec continuous cycle (see finding
\#1 above): a universal, year-independent sequence, just reached at a
different calendar date depending on that year's Triodion start. Nothing
new to implement here — the unsolved recovery-mechanism window is fully
bounded between the Theophany-afterfeast cluster and each year's own
Triodion start, and nothing beyond that boundary is at risk.

Everything outside this narrow window — the entire Sunday-of-Luke cycle,
the Nativity/Theophany fixed cluster, Forefeast/Afterfeast, Leavetaking,
and all ordinary weekdays before Nativity and after the window closes — is
confirmed correct.

### Cross-check against goarch.org/chapel

This entire investigation had relied on a single source, antiochian.org.
GOA (Greek Orthodox Archdiocese of America) and the Antiochian Archdiocese
are normally in lockstep on the ordinary daily lectionary (that shared
premise is the basis of this whole `tradition=greek` axis, per the plan's
Context section), but antiochian.org's own site could in principle have a
bug or idiosyncrasy on these specific unresolved days that a second source
would reveal.

**Attempted programmatically, blocked**: goarch.org sits behind Cloudflare
bot management that returns HTTP 403 to both `WebFetch` and direct
`requests`/`curl` calls, even with a fully realistic browser header set
(UA, `Accept-Language`, `Sec-Fetch-*`, etc.) — confirmed via the
`Server: cloudflare` response header and garbled response body. This is
almost certainly TLS-fingerprint-based (JA3/JA4) bot detection, which
happens before HTTP headers are even read, so no amount of header-spoofing
from a Python script fixes it; it would need a real browser engine. A
search-engine snippet initially suggested GOA showed `Romans 12:6-14` for
the **2025-01-24** Epistle (vs. antiochian.org's `Gal 5:22-26; 6:1-2`) —
flagged at the time as unreliable, since search-snippet summarization
conflated results across different lectionary `code=` values.

**Manually confirmed by the user (2026-07-22)**: goarch.org actually shows
`Galatians 5:22-26; 6:1-2` for 2025-01-24 — **matching antiochian.org
exactly**, and directly contradicting the unreliable search-snippet result
(confirming that result was noise, as suspected). This is exactly the
outcome the "Bottom line" note above anticipated: **GOA agreeing with
antiochian.org on a known-wrong day is evidence against "antiochian.org
has a bug"** and strengthens the case that the current app's incorrect
output on this date (see the confirmed 2022-01-19 before/after example
above) reflects a real, still-undiscovered liturgical mechanism — not bad
source data. One date confirmed; checking the remaining identified dates
(Jan 19/26, Feb 4/5/7/9, and the Feb 11+ unverified extension in low-jump
years) the same way — manually, in a browser — is the natural next step
whenever this investigation resumes, using the URL patterns discovered
this pass: `https://www.goarch.org/chapel/lectionary?type=epistle&code=
217&date=MM/DD/YYYY` for a single date, or
`https://www.goarch.org/chapel/calendar?month=M&year=YYYY&viewStyle=
GridView&viewType=ViewReadings` for a whole month at a glance.

## Two of the "confirmed-wrong" days turned out to be missing Menaion data, not the drift mechanism

While manually checking 2025-01-24 against goarch.org (previous section),
the user noticed the `Gal 5:22-26; 6:1-2` Epistle traces to a specific
saint — Xenia of Rome, Deaconess, commemorated Jan 24 (this project's own
`Day` table already lists her: `'Ven. Xenia of Rome; Bl. Xenia of St
Petersburg'`, feast_level=0) — not a coincidental repeat. This raised the
hypothesis: are some of the "confirmed-wrong" free-weekday dates actually
just *missing Menaion data* for a genuine but low-rank saint, rather than
evidence of the unsolved recovery mechanism?

**Checked directly — the answer is a real split, not uniform:**

- **Jan 19 (Ven. Macarius the Great) and Jan 24 (Xenia of Rome)**: the
  Epistle is genuinely fixed across every sampled year (`Gal 5:22-26;
  6:1-2`, 5/5 for both dates) — this really was missing Menaion data, not
  drift. **Both now added** as `greek`-tagged `Reading` rows (pdist=999,
  reusing the existing `Gal 5.22-6.2` Pericope, id 647), purely additive
  (the existing `common` row is untouched and stays correct for Slavic —
  confirmed against oca.org, which shows a *different* Epistle,
  `Jas 2:1-13`/`Jas 1:1-18`, for these same dates: this repo's `common`
  data was built from oca.org, and this incidentally confirms that base
  data is still accurate).
- **Jan 26 (Ven. Xenophon and Mary) and Feb 4/7/9**: checked the same way
  (Epistle citations across every sampled year) — **no fixed pattern at
  all**. Feb 4 alone showed 5 different, non-repeating Epistle citations
  across 5 independent years, exactly mirroring the Gospel-side variation
  already established for these dates. These are *not* missing-data gaps;
  the "no fixed reading of any kind" pattern is exactly what the unsolved
  drift mechanism predicts.

**Net effect on the day count above**: Jan 19 and Jan 24 are now correct
on the **Epistle** side specifically (Gospel on both dates still shows the
confirmed-wrong drift-mechanism content — that part is untouched and still
needs the unsolved mechanism to fix). Jan 26 and the Feb dates are
unaffected by this pass. The 18-date fixed-Menaion-set count from the
"Known scope" section above doesn't change; Jan 19/24 are best thought of
as "half fixed" (Epistle solid, Gospel still wrong) rather than moved into
the fully-resolved column.

Regenerated `fixtures/calendarium.json` (+2 `Reading`, `Pericope`/`Day`/
`Composite` untouched) and confirmed the full 92-test suite still passes.

This suggests a productive way to whittle down the remaining Feb 11+
unverified extension (see above) if this resumes: check each date's
Epistle for a fixed, non-varying pattern first (cheap, using already-
harvested data) before assuming it's part of the unsolved mechanism —
some fraction of those days may turn out to be the same kind of simple
missing-saint gap as Xenia and Macarius.

## Separate, unrelated bug found and fixed: `greek_extra_sundays > 5` crashed

While cross-checking Xenia's Epistle against goarch.org, a genuinely
different and more serious bug surfaced: `GreekYear.greek_extra_sundays`
(the count of "extra" Sundays needing content between Theophany and
Triodion) is 6 or 7 in roughly a quarter of all years (2020, 2023, 2026,
2031, 2034, 2039, 2042 in the near term), but `_THEOPHANY_INTERPOLATION`
only had entries for 0-5. When uncovered, `sunday_gospel_override` returned
`None` for every affected Sunday that year, and `Day.gospel_pdist` fell
through to a Slavic-only branch (`self.pyear.reserves[i-1]`) that always
raised `IndexError` for Greek, since `GreekYear.reserves` is hardcoded to
`[]`. This was a genuine 500 error, not just wrong content — worse than
anything else catalogued in this document, and unrelated to the
weekday-drift mechanism above (it's on the Sunday side, not the weekday
side).

**Test-first, then fixed in three parts:**

1. **Regression test added first** (`TestReadingsView.
   test_greek_extra_sundays_overflow_does_not_500`), confirmed to fail
   (raising `IndexError` via the actual HTTP view) against the original
   code for both known crash magnitudes (2021-01-24, n=6; 2024-01-14,
   n=7), *then* fixed with a bounds check in `Day.gospel_pdist` so it
   degrades to the existing generic fallback instead of crashing. This
   alone doesn't produce correct content — just stops the 500 — see below
   for the real fix.

2. **`_THEOPHANY_INTERPOLATION` rebuilt from real data.** The byzcath.org
   source this table was originally transcribed from only ever enumerated
   cases up to n=5 and was never checked against a real n=5 year. Checking
   it against 4 independent years (2022=n4, 2018=n5, 2020=n6, 2023=n7)
   revealed the table's own n=5 entry was wrong (claimed 12th, 14th, 15th,
   17th-of-Matthew; real 2018 data shows 12th, 15th, **16th**-of-Matthew,
   17th-of-Matthew) — and confirmed the true sequence builds up in a
   specific, non-linear insertion order as the gap grows (not "extend the
   sequence forward"): 3→(12,15); 4→+Canaanite Woman (17th Matthew); 5→+
   16th Matthew; 6→+14th (inserted between 12th and 15th, not appended).
   "Canaanite Woman" (Greek) / "Zacchaeus" (Slavic) were confirmed, via
   Wikipedia's Paschal cycle article, to be the *same* fixed,
   Pascha-anchored occasion (11 weeks before Pascha) in both traditions —
   `_matthew_sunday_target(17)` already resolves to the correct text
   (`Matt 15:21-28`) in the shared table, so no new Pericope was needed.
   n=7 (2023, where Leavetaking of Theophany also happened to fall on a
   Sunday that year) showed the exact n=6 sequence with one extra slot
   prepended for the Leavetaking special case — confirmed to structurally
   always land on the table's first slot whenever it applies, since both
   are always exactly one week after `sun_after_theophany`. Implemented as
   `regular_extra_sundays` (n adjusted for the Leavetaking case) indexing
   the same table, with the Leavetaking slot prepended when it applies.
   n=2's entry is unchanged (unverified this pass, not contradicted).

3. **Epistle/Gospel wiring bug, found while implementing the above.**
   `Day.epistle_pdist` never consulted `_sunday_gospel_override` at all —
   only `gospel_pdist` did. So on every numbered Sunday-of-Luke/Matthew
   occasion (all of n=2 through 7), the Epistle fell through to an
   unrelated calendar-relative formula instead of the target pdist the
   Gospel correctly resolved to. Confirmed via a live example: 2026-01-18
   ("12th Sunday of Luke") showed the correct Gospel (`Luke 17:12-19`) but
   `1 Tim 1:15-17` for the Epistle — actually `Hebrews 13:7-16`, which
   *is* the correct Epistle when that Sunday coincides with a fixed
   Menaion saint (Athanasius & Cyril, Jan 18, already correctly
   implemented this session) — the underlying Sunday-of-Luke Epistle bug
   was masked on that specific test date by an unrelated fixed-saint
   override coincidentally being right. Checked whether the shared
   common/slavic table already has the correct Epistle paired with the
   Gospel at every target pdist used (12th, 14th, 15th Luke; 16th, 17th
   Matthew) — it does, confirmed against 5-7 independent years each — so
   the fix was purely wiring `epistle_pdist` to also consult
   `_sunday_gospel_override`, no new data needed.

   **Correction (found later, via a user-reported live discrepancy on
   2026-09-27): this fix over-applied.** The verification above only ever
   checked *post-Theophany interpolation* dates (all in the Jan-Feb
   window). It was never checked against the *ordinary* Oct-Dec numbered
   Sundays of Luke (`lukan_sunday_numbers`'s natural, non-interpolated
   progression) — and there, pairing the Epistle to the Gospel's number
   is wrong. Confirmed with clean, unambiguous cross-year evidence: the
   real antiochian.org Epistle for "1st Sunday of Luke" is `2 Cor 4:6-15`
   in 2022 but `2 Cor 6:16-7:1` in 2026 — different citations for the
   *same* numbered Sunday in different years, which rules out a fixed
   Gospel-paired target. In both years it's exactly the plain, unadjusted
   calendar pdist's own Epistle instead — identical to what `SlavicYear`
   already shows for the same date (same underlying `common` row, since
   Slavic's Epistle is never affected by the Lukan jump either). Same
   result for "2nd Sunday of Luke" (`2 Cor 6:1-10` in 2022, `2 Cor 9:6-11`
   in 2026, both matching the plain pdist). The Canaanite Woman and
   post-Theophany-interpolation cases *do* still pair Epistle to Gospel
   (re-confirmed: Canaanite Woman's Epistle, `2 Cor 6:16-18;7:1`, matches
   the paired target in 4 of 5 harvested years).

   **Fixed** by splitting the override into two methods:
   `GreekYear.sunday_gospel_override` (unchanged, still used for
   `gospel_pdist`) and a new `GreekYear.sunday_epistle_override`, which
   skips the override specifically in the ordinary
   `first_sun_luke..forefathers` range (falling back to the plain pdist
   there, matching `SlavicYear`), while still applying it for the
   Canaanite Woman and interpolation cases, and still suppressing
   outright when an Apostle feast claims the Sunday. `Day` now has a
   separate `_sunday_epistle_override` cached property feeding
   `epistle_pdist`, parallel to `_sunday_gospel_override`. See
   `TestDay.test_ordinary_sunday_of_luke_epistle_does_not_follow_gospel`
   in `test_liturgics.py`.

4. **A fourth, subtler bug found while testing #2-3: the Canaanite
   Woman/Zacchaeus boundary is a distinct `GreekYear` *instance* boundary,
   not just a table entry.** pdist -77 (Canaanite Woman/Zacchaeus) is,
   by construction, always exactly `next_pascha - 77` for one `GreekYear`
   instance *and* exactly `pascha - 77` for the following instance (since
   `next_pascha` of one year equals `pascha` of the next). `Day` resolves
   a real calendar date via whichever Pascha is closer — confirmed
   `Day(2026, 1, 25)` picks `GreekYear(2026)`, not `GreekYear(2025)`, even
   though the latter is what actually computed the "15th Sunday of Luke"
   assignment for that date via `theophany_interpolation`. This means the
   *last* entry in every `_THEOPHANY_INTERPOLATION` sequence (n>=4) was
   never actually reachable through the mechanism that computed it — Day
   always lands on the following year's instance and falls through to the
   shared table's own Zacchaeus content there instead. Fixed with a new
   `GreekYear.canaanite_woman_applies` property that looks up the
   *preceding* year's `regular_extra_sundays` (the one whose winter
   actually leads into this Sunday) to decide whether pdist -77 should
   show Canaanite Woman (n>=4) or fall through to the shared table's own
   content unchanged (n<=3) — checked directly in `sunday_gospel_override`
   rather than through `theophany_interpolation`. Confirmed against both
   a real small-n case (2026-01-25, n=3, correctly *not* overridden — that
   test was already passing before this fix only because it happens to
   also coincide with St. Gregory the Theologian's fixed reading) and
   multiple real large-n cases (2019-02-10 n=5, 2021-02-14 n=6, both now
   correctly showing `Matt 15:21-28`/`2 Cor 6:16-18;7:1`).

All four fixes verified end-to-end via `Day` (not just `GreekYear` in
isolation) against real antiochian.org data across 2018, 2019, 2020, 2021,
2023, 2024, and 2026. Full test suite: 95/95 passing (was 92 before this
session; +1 crash-regression test, +2 covering the table/boundary fixes).

### n=2 confirmed, and `_THEOPHANY_INTERPOLATION`'s dead trailing entries removed

The n=2 table entry (`25th of Luke`) was flagged above as unverified this
pass (no reachable year). Found one: 2017 cycle (Jan-Feb 2018) has
`regular_extra_sundays=2` (raw `greek_extra_sundays=3`, adjusted down by
one for the Leavetaking-on-Sunday case, confirmed present that year too).
Checked directly against real antiochian.org data: Jan 21, 2018 shows
"15th Sunday of Luke" (`Luke 19:1-10`/`1 Tim 4:9-15`), not "25th" as the
table claimed.

This looked like the same class of bug as n=5, but turned out not to be a
bug at all: working the math, the *last* entry in an n-row sequence always
lands exactly at `sun_after_theophany + 7*n` = `triodion_start - 7` =
`next_pascha - 77` — i.e. it always coincides exactly with the Canaanite
Woman/Zacchaeus boundary from the previous section, for *every* n, not
just n>=4. Confirmed directly: `Day(2018,1,21)` resolves via
`GreekYear(2018)` (not `2017`, landing on pdist -77 relative to
`GreekYear(2018).pascha`) and `canaanite_woman_applies` correctly returns
`False` there (2017's `regular_extra_sundays` is 2, below the n>=4
threshold), falling through to the shared table's own content — an exact
match to the real citation. So the table's n=2 entry (and every other
row's trailing entry) was never actually reachable through
`theophany_interpolation` at all; it happened to be harmless for n=2/3
(the boundary fallthrough coincidentally produces correct content anyway)
and merely redundant for n>=4 (duplicating what `canaanite_woman_applies`
already computes independently).

**Cleaned up**: removed the trailing entry from every row in
`_THEOPHANY_INTERPOLATION` (confirmed dead code, not a behavior change —
`canaanite_woman_applies` already governs that position exclusively).
Updated the one test that directly asserted a removed dict key, added the
new n=2 confirmation as its own test case (both at the `GreekYear` level
and end-to-end through `Day`). Full suite: still 95/95 passing.

**Net result**: the n-value table (now 0-6, each row one entry shorter)
and `canaanite_woman_applies` together are confirmed correct across every
reachable magnitude (n=2 through 7) against real data. n≥8 has never been
observed and remains unverified in principle, but no such year exists in
the checked 2010-2050 range, so this is not a live gap.

## REOPENED (2026-08-25): the day labels are Greek's own lectionary index

This investigation was closed as "not solvable from the sources available."
That conclusion rested on a method, not on the data: every pass resolved
Greek citations by **matching them against this project's `common`/`slavic`
`Reading` table by `pdist`**, and then tried to explain the resulting
positions. The final disposition above says as much — "the 'matches' driving
this whole investigation are very likely coincidental text reuse between two
different, undocumented algorithms."

That is correct, and it is also avoidable. **antiochian.org publishes Greek's
own lectionary index, and no pass ever read it.** The harvest scripts only
ever consumed `reading1Title`/`reading2Title` (the citations).
`feastDayTitle` is normally a saint's name, but on a day with no ranking
commemoration it is instead the day's own **slot identity**, in one of three
formats:

| Format | Example | Meaning |
|---|---|---|
| A | `17TH TUESDAY AFTER PENTECOST` | Matthew section, week 17, Tuesday |
| B | `TUESDAY OF THE 15TH WEEK` | Luke section, week 15, Tuesday |
| S | `12TH SUNDAY OF LUKE` | numbered Sunday/Saturday series |

`tools/greek/greek_labels.py` (repo root) extracts these into
`data/greek_lectionary_from_labels.json`: **394 labeled slots** across the
1500 cached days. Resolving through this index instead of through `pdist`
removes the coincidental-reuse noise entirely, because it is Greek's own
numbering rather than an inference from Slavic's.

### What the index shows

**1. Two complete weekday sequences, reconstructed directly.**

- **Matthew section** (format A): Matthew weekdays weeks 1-11, then **Mark**
  weekdays weeks 12-17, plus a separate Matthew-Saturday series.
- **Luke section** (format B): Luke weekdays weeks 1-12, then **Mark**
  weekdays weeks 13-16, plus a separate Luke-Saturday series.

Both are reconstructed nearly gap-free. The Gospel is a **pure function of
(section, week, weekday)** — of 169 weekday slots, every single conflicting
one falls inside the disputed January window. Outside it, 5-8 independent
years agree exactly, with zero contradictions. (Epistle slots do conflict,
but only because a saint's own Epistle displaces the cycle's while the day
keeps its slot label — a known, separate effect.)

**2. The Luke-section pointer is calendar-locked, exactly, with no
exceptions.** Defining `calendar_week = (date - (first_sun_luke + 1)) // 7 + 1`,
the label's week number satisfies

        label_week = calendar_week + 1

for **every one of 303 labeled days across 9 independent cycles**
(2018/19 through 2026/27), from the Lukan jump through December 31. Not a
majority, not a fit — zero exceptions. This is the first time the ordinary
weekday formula has been stated in Greek's own terms rather than inferred as
`calendar_pdist + lukan_jump` against the Slavic table.

**3. The disruption is a pointer *suspension*, not a drift or a reshuffle.**
The lag holds at -1 through Dec 31, then jumps to +3..+6 during the
Nativity/Theophany cluster, then the sequence resumes — still weekday-aligned
(Monday content on a Monday) and still contiguous, just behind schedule. Direct
evidence of deferral rather than loss: 2021-12-31 was labeled `FRIDAY OF THE
15TH WEEK` but read `Luke 16:10-15` (the `SatAfterNativityFriday` feast), and
that slot's real content, `Mark 12:1-12`, then appears on **2022-02-04** — the
next free Friday. This is the Typikon's "omission and repeat" rule operating
exactly as written, and it is why the FIFO model in #5 above looked right for
some years and wrong for others: it applies to the *cluster*, not to ordinary
saints.

**4. When the Luke section runs out, the Matthew section resumes.** In the
2018/19 cycle (`jump=7`, latest Triodion of any harvested year, 2019-02-18)
the format-B labels stop after Dec 31 and February's free days carry
**format-A** labels instead — `17TH MONDAY/TUESDAY/THURSDAY AFTER PENTECOST`
reading `Mark 5:24-34`, `6:1-7`, `6:30-45`, a contiguous Markan run. That is
the Typikon's "we return to St. Matthew and count the weeks that are left
from the Sunday after the Elevation" clause, observed live.

### Re-measured: exactly which days the app gets wrong

`tools/greek/greek_check.py` compares `Day(..., tradition='greek')`'s computed
Gospel against every harvested day between Leavetaking of Theophany and
Triodion, tolerating the known +/-2 verse-boundary variants and counting a day
correct if the antiochian citation appears anywhere in the app's reading list
(the app lists a saint's reading alongside the continuous one):

| cycle | days checked | wrong |
|---|---|---|
| 2019 | 28 | 7 |
| 2021 | 30 | 2 |
| 2022 | 28 | 5 |
| 2023 | 24 | 4 |
| 2024 | 32 | 3 |
| 2025 | 28 | 1 |
| 2026 | 20 | 2 |

**24 wrong days across 7 cycles** against antiochian.org — but see the GOA
cross-check below: **four of those 24 are false alarms**, days where the app
is right and antiochian.org is the outlier, so the real count is **20**.
February is already correct throughout. The gap is really **three calendar
dates**:

- **Jan 19** (Macarius the Great) — wrong in 6 of 7 cycles
- **Jan 24** (Xenia) — wrong in 5 of 7
- **Jan 26** (Xenophon) — wrong in 5 of 7

plus 2019's four format-A February days, 2023-01-14, 2026-01-24, and two
Sundays (2022-01-23, 2022-01-30) that belong to the Sunday mechanism, not
this one.

### The residual unknown, stated precisely

On those three dates the Gospel slot is unclaimed (the saints supply only the
already-implemented `Gal 5:22-26; 6:1-2` ascetic Epistle), and what
antiochian.org shows is a **numbered Sunday-of-Matthew pericope** — confirming
the recovered-Matthew-Sunday mechanism of #7 qualitatively. The numbers
observed, against each cycle's parameters:

| cycle | jump | jump/7 | Sunday interpolation uses | observed weekday Matthew numbers (Jan 19/24/26) |
|---|---|---|---|---|
| 2021 | 28 | 4 | 16th Matthew | **13, 14, 15** |
| 2022 | 21 | 3 | none | **14, 15, 16** |
| 2020 | 14 | 2 | 16th Matthew | 12 |
| 2023 | 14 | 2 | 16th Matthew | 12, 9, 14 |
| 2024 | 35 | 5 | none | 3 |
| 2025 | 7 | 1 | none | 15 |
| 2018 | 7 | 1 | 16th Matthew | 4, 7, 15 |

Two cycles fit a clean rule perfectly. Taking the numbered Matthew Sundays as
1-16 (17th being the Canaanite Woman, handled separately by
`canaanite_woman_applies`), the jump skips `{17 - jump/7, ..., 16}`:

- **2021** (`jump=28`): skipped `{13,14,15,16}`; weekdays drain 13, 14, 15 in
  order and the Sunday interpolation takes 16. Complete, no remainder.
- **2022** (`jump=21`): skipped `{14,15,16}`; weekdays drain 14, 15, 16.
  Complete, no remainder.

The other five cycles do not fit this or any variant tried, and 2023's
`12, 9, 14` is not even monotonic. So the rule is **not** confirmed, and
nothing should be implemented from it. But the failure now has a specific
shape worth testing rather than a general one: either there is a further
constraint governing which skipped Sunday is drained when, or — given that
`Matt 19:16-26` (the rich young ruler, the classic venerable-monastic
Gospel) shows up on Macarius's day in two separate cycles, and `Matt 6:22-33`
on Xenia's in another — **antiochian.org is itself making ad-hoc editorial
choices on these three dates**, in which case there is no rule to find in this
source at all.

### GOA cross-check: obtained at last, and it changes two conclusions

goarch.org has never been readable by this project — Cloudflare's
TLS-fingerprint block defeats `requests`/`WebFetch`, and a real browser engine
(Claude in Chrome) still hits the "Performing security verification"
interstitial. **The user cleared the interstitial manually on 2026-08-25**,
after which seven months of the grid view were readable in-session. The
results are saved to `data/goarch_winter_readings.json`. Use the same
human-in-the-loop procedure to extend it:

    https://www.goarch.org/chapel/calendar?month=M&year=YYYY&viewStyle=GridView&viewType=ViewReadings

GOA's grid is strictly better source data than antiochian.org's feed for this
question: it prints the day label **and** both citations together, so a slot
identity is never hidden behind a saint's name the way `feastDayTitle` hides
it.

**Conclusion change 1: the app is already correct in February, and
antiochian.org is the outlier.** For the 2018/19 cycle, GOA's February reads

| date | GOA label | GOA Gospel | app computes | antiochian |
|---|---|---|---|---|
| 2019-02-04 | Monday of the 15th Week | Mark 10:46-52 | Mark 10.46-52 | Mark 5:24-34 |
| 2019-02-05 | Tuesday of the 15th Week | Mark 11:11-23 | Mark 11.11-23 | Mark 6:1-7 |
| 2019-02-07 | Thursday of the 15th Week | Mark 11:27-33 | Mark 11.27-33 | Mark 6:30-45 |
| 2019-02-09 | Saturday of the 15th Week | Luke 17:3-10 | Luke 17.3-10 | Matthew 25:1-13 |

GOA simply continues the Luke section (format B) contiguously into weeks 15
and 16, exactly as the pointer model predicts, and **the app matches it on
every one**. Antiochian.org instead returns to the Matthew section — which is
also a defensible reading of the Typikon, but it is Antiochian practice, not
universal Greek practice. The "return to St. Matthew" behaviour documented in
finding #4 of this section is therefore real but **jurisdiction-specific**.
Four of the 24 measured wrong days evaporate; the corrected count is **20**.

**Conclusion change 2: GOA and antiochian genuinely disagree on the
contested days, so there is no single ground truth to compute.** Of 14
comparable Jan 19/24/26 slots, they agree on 11 and disagree on 3:

| date | GOA | antiochian |
|---|---|---|
| 2021-01-19 | Matthew 22:2-14 (14th of Matthew) | Matthew 19:16-26 (12th) |
| 2021-01-26 | Matthew 22:35-46 (15th) | Mark 11:11-23 (ordinary B wk15 Tue) |
| 2024-01-19 | Matthew 9:1-8 (6th) | Matthew 19:16-26 (12th) |

This supersedes the 2026-07-22 note above, which found GOA and antiochian
agreeing on 2025-01-24 and reasonably read that as evidence against
"antiochian.org has a bug." With a wider sample the two sources do diverge —
so on these three dates the project is not choosing between right and wrong,
it is choosing **whose calendar to follow**.

**What GOA's numbers do for the drain hypothesis.** Substituting GOA where it
differs, the observed weekday Matthew-Sunday numbers become:

| cycle | jump | jump/7 | Jan 19 | Jan 24 | Jan 26 | + Sunday interp | fits? |
|---|---|---|---|---|---|---|---|
| 2020 | 14 | 2 | 14th | (Sun) | 15th | 16th | ends at 16 |
| 2021 | 28 | 4 | 13th | 14th | 15th | 16th | **exact** |
| 2022 | 21 | 3 | 14th | 15th | 16th | — | **exact** |
| 2018 | 7 | 1 | 4th | 7th | 15th | 16th | no |
| 2023 | 14 | 2 | 6th | 9th | 14th | 16th | no |
| 2024 | 35 | 5 | (Sun) | 3rd | (Sun) | — | no |
| 2025 | 7 | 1 | 15th | (Sat) | (Mon P&P) | — | partial |

GOA's 2020 numbers (14, 15) are consecutive and, with the interpolation's
16th, end exactly where 2021 and 2022 do. Three consecutive cycles now form
clean ascending runs terminating at the 16th of Matthew — the last numbered
Matthew Sunday before the Canaanite Woman. That is a real, repeated
structure, and it is the strongest positive signal this investigation has
produced.

It still does not generalise. Cycles 2018, 2023 and 2024 give 4/7/15, 6/9/14
and 3 — not ascending runs, not terminating at 16, and not explained by
`jump`, `triodion_start`, or the interpolation count. Notably those three are
the extremes of `triodion_start` (315, 315, 280 against 287-308 for the
cycles that fit), which is worth testing but is one degree of freedom fitted
to three points.

**Recommendation.** Do not implement a drain formula. Two things are worth
doing instead, in order:

1. **Extend the GOA harvest** to the cycles not yet covered and to more
   years in each direction, using the manual procedure above. The drain
   hypothesis makes a sharp, falsifiable prediction — ascending run of
   `jump/7` numbered Matthew Sundays ending at the 16th — and roughly six
   more cycles would settle it. This is cheap and it is the only remaining
   line of evidence that could turn the gap into code.
2. **Decide the jurisdiction question explicitly.** The `tradition=greek`
   axis was built on the premise that GOA and Antiochian are in lockstep on
   the ordinary daily lectionary. On these ~20 days per 7 years they are not.
   The February evidence says the app's current behaviour already matches
   GOA, so "Greek" here effectively means GOA — worth stating in the docs
   deliberately rather than leaving it as an accident of which source was
   easiest to scrape.

### Artifacts from this pass

- `tools/greek/greek_labels.py` -> `data/greek_lectionary_from_labels.json`:
  the label-derived Greek-native lectionary (394 slots) and the per-cycle
  pointer-lag trace. Rebuild with `python3 tools/greek/greek_labels.py`.
- `tools/greek/greek_check.py`: the app-vs-antiochian audit that produced the
  24-day table above. Run inside Docker
  (`docker compose exec -T local python tools/greek/greek_check.py`).
- `data/goarch_winter_readings.json`: the first goarch.org data this project
  has ever held — 7 months of the contested window, labels plus both
  citations. Extend it manually; scripted access is blocked.

## GOA harvest extended (2026-08-25, same session): the source of truth is partly human

`data/goarch_winter_rows.txt` now holds **215 rows covering 27 cycles**
(Jan/Feb 2011 through Jan 2037), harvested from goarch.org's grid view.
`tools/greek/goa_analyze.py` and `tools/greek/goa_audit.py` (repo root) do the
analysis; both need Docker (`docker compose exec -T local python ...`).

### GOA breaks both of antiochian.org's horizon limits

The "Leftover floats: final disposition" section above establishes that
antiochian.org's API fails before 2018 and beyond roughly a year out, and
several questions were closed as permanently unobservable on that basis.
**goarch.org serves 2011 and 2037 equally well.** Any question previously
closed for lack of reachable years should be reconsidered against GOA before
being treated as settled.

Harvest method: navigate to any goarch.org page once (the user clears the
Cloudflare interstitial), then `fetch()` further months from inside the page
origin via `javascript_tool` — same-origin requests inherit the clearance
cookie, so one manual step buys a whole session. The month grid parses out of
`innerText`: `[day number, long date, fasting lines, label, saints...,
'Epistle Reading', '-', epistle, 'Gospel Reading', '-', gospel]`.

### The decisive finding: GOA's own software does not compute these days

Every year from **Jan 2028 onward** is invariant:

- **Jan 19 is always `Matthew 19:16-26`** — the rich young ruler, the standard
  venerable-monastic commons Gospel — regardless of weekday, jump, or
  Triodion date. Checked 2028-2037, ten consecutive years, no exceptions.
- **Jan 24 and Jan 26 are always ordinary continuous-cycle readings**, carrying
  a genuine slot label and the matching universal citation.

Every year from **Jan 2011 through Jan 2027** varies: Jan 19 takes Matthew
Sunday numbers 3, 4, 6, 7, 12, 13, 14 or 15 depending on the year, and Jan
24/26 sometimes take Matthew Sundays and sometimes ordinary readings.

2027 is exactly GOA's published-Kanonion horizon (the site footer advertises
"2027 Kanonion"). So the boundary is not liturgical — it is editorial.
**GOA's calendar software computes only the ordinary continuous cycle; for
years inside the Kanonion horizon a human overrides these days from the
annual ordo, and past that the software falls through to the saint's commons
Gospel.** That is the same conclusion the "Final disposition" section above
reached from the Typikon ("the day-by-day arithmetic apparently lives only in
an actual annual lectionary chart/ordo") — now confirmed from the other side,
by watching a real implementation run out of curated data.

Supporting evidence that the *algorithmic* part is genuinely deterministic:
cycles 11 years apart share `(lukan_jump, triodion_start,
regular_extra_sundays)`, and all **8 such pairs in range reproduce their
Format-B pointer lag exactly** — 2011/2022 both lag 3, 2012/2023 both [3,6],
2013/2024 both 4, 2014/2025 both 2, 2015/2026 both [3,5], 2016/2027 both 3,
2017/2028 both 2, 2018/2029 both [3,5]. The reproducible part reproduces
perfectly; the contested days do not. Note the paired cycles do *not* share
weekday alignment, which is why their labels differ while their week numbers
agree.

(One earlier claim in this document needs softening: the return to the
Matthew section is **not** Antiochian-specific. GOA does it too — 2035-01-24
and 2035-01-26 carry `16th Wednesday/Friday after Pentecost`. The two sources
differ about *when* the Luke section is exhausted, not about the rule.)

### Consequence 1: an unlimited, noise-free oracle for the suspension lag

Because GOA's uncurated years are pure algorithm, they are a clean training
and validation set for the one mechanism still unmodelled — the pointer
suspension across the Nativity/Theophany cluster. `tools/greek/goa_audit.py`
scores the app against them: **47 uncurated days, 17 mismatches**, and once
the ten Jan-19 commons days are set aside the residue is a consistent
**~2-week lag** — the app reads B-week 13 where GOA reads B-week 15:

| date | GOA slot | GOA Gospel | app computes |
|---|---|---|---|
| 2030-01-24 | Thursday of the 15th Week | Mark 11:27-33 | Mark 9.10-15 (B13 Thu) |
| 2030-01-26 | Saturday of the 15th Week | Luke 17:3-10 | Luke 14.1-11 (B13 Sat) |
| 2032-01-24 | Saturday of the 14th Week | Luke 16:10-15 | Luke 13.18-29 (B12 Sat) |
| 2032-01-26 | Monday of the 15th Week | Mark 10:46-52 | Mark 8.11-21 (B13 Mon) |

This is the first time the unsolved mechanism has had a source that can be
sampled arbitrarily. Harvesting 2028-2060 gives ~30 clean cycles spanning
every `(jump, triodion_start)` combination, which is almost certainly enough
to pin the lag rule and finally implement it. **This is the recommended next
step**, and it no longer depends on anyone's editorial judgement.

Two smaller app bugs also surface in the uncurated set and are worth
confirming separately, since they are on the Sunday side rather than the
weekday side: 2031-01-19 (app says 12th Sunday of Luke, GOA says 15th) and
2031-01-26 (app says 15th Sunday of Luke, GOA says the Publican and
Pharisee, i.e. Triodion has already begun).

### Consequence 2: one small fix available now

**Jan 19 (Macarius the Great) has no Greek Gospel in this project's data.**
GOA assigns `Matthew 19:16-26` invariantly whenever no curated override
applies, paired with the `Gal 5:22-26; 6:1-2` Epistle this repo already
implemented for that date. Adding it as a `greek`-tagged `month`/`day`
`Reading` row is the same one-line change as the Xenia/Macarius Epistle rows,
and would replace today's output — an unrelated continuous-cycle pericope
that is wrong in every sampled year — with the reading GOA falls back to.
Not implemented here: it is right against GOA's algorithm but will disagree
with the curated ordo in the years GOA has curated, and that trade-off is a
judgement call about which the project should follow.

### Consequence 3: the standing "no per-year overlay" constraint now bites

GOA's curated values for Jan 19/24/26 are available for 2011-2027 and could
simply be loaded as data. That is exactly the per-year overlay the standing
constraint at the top of this document rules out, and it would need
re-harvesting each year as the Kanonion horizon advances. Worth restating
deliberately rather than assuming: the constraint is now the only thing
standing between this project and correct output on those days, because the
evidence says no algorithm exists to be found for them.

## The lag rule, SOLVED: the Luke-section cycle is back-anchored to Triodion

Harvested GOA's uncurated (pure-algorithm) years at scale to fit the pointer
suspension. `data/goarch_pointer_sequences.txt` holds the resulting
observations for **37 cycles** (2027-2096, concentrating on long seasons);
`tools/greek/backanchor.py` and `tools/greek/backanchor_audit.py` do the fitting.

**The mechanism is not a lag at all.** Every earlier pass, including the
first half of this session, modelled the Luke-section pointer as running
*forward* from `first_sun_luke` and falling behind across the
Nativity/Theophany cluster — hence "lag", and hence the search for a rule
predicting how far behind. That framing is wrong. The cycle is anchored to
the **end** of the season:

| weeks before Triodion | Luke-section week read | observations | exceptions |
|---|---|---|---|
| last (b-1) | **16** | 145 | 0 |
| second-last (b-2) | **15** | 96 | 0 |
| third-last (b-3) | **14** | 48 | 0 |

**289 observations, zero exceptions**, spanning every `lukan_jump` value from
0 through 35 and every Nativity weekday. The forward `lag` looked
year-dependent only because it is an artefact of measuring a back-anchored
sequence from the wrong end.

This also explains why the forward-lag hunt kept producing partial fits that
broke on cross-checks: `triodion_start` varies independently of
`lukan_jump` (it depends on the *following* year's Pascha), so any rule
expressed in terms of `lukan_jump` was fitting noise.

### The app already implements this correctly

`tools/greek/backanchor_audit.py` scores `Day(..., tradition='greek')` against
every harvested observation:

- **b >= -3 (the back-anchored tail): 140 days, 140 correct, 0 wrong.**
- **b <= -4 (surplus weeks): 14 days, 0 correct, 14 wrong.**

The app's Gospel pdist is computed relative to Pascha, and Triodion is itself
a fixed Pascha offset, so the existing computation *is* back-anchored — it
gets the tail right by construction. There was nothing to fix here. What was
missing was any test pinning the property, so a future change to the Greek
weekday path could have broken it silently.

**Added `TestGreekPreTriodionWeekdayCycle`** in
`calendarium/tests/test_liturgics.py`: 56 dates spread deliberately across
jumps 0, 7, 14, 21, 28 and 35, asserting that the three weeks before Triodion
read Luke-section weeks 14/15/16 with the correct weekday pericope. The test
derives the week purely from Pascha (Triodion is always pdist -70), so it
asserts the invariant rather than memorised answers. Verified to fail when
the expected table is perturbed.

### What actually remains broken

The residual is now precisely bounded: **the surplus weeks, b <= -4**, which
only exist in the longest seasons (`triodion_start >= 308`, roughly one year
in five). The app is wrong on all of them. What GOA reads there is
deterministic — every configuration observed twice or three times agrees
exactly — but no generative rule was found:

| jump | Nativity | b-5 | b-4 | cycles |
|---|---|---|---|---|
| 7 | Mon | — | A16 | 2034, 2045, 2056 |
| 7 | Tue | — | B15 | 2029, 2091 |
| 7 | Wed | — | B12 | 2075, 2086 |
| 7 | Thu | B14 | B15 | 2031, 2042, 2053 |
| 7 | Sat | — | B14 | 2083 |
| 7 | Sun | — | B15 | 2061, 2067, 2072 |
| 14 | Sun | B15 | A15 | 2039, 2050 |
| 14 | Tue | B15 | — | 2096 |
| 14 | Wed | B12 | — | 2058, 2069, 2080 |
| 14 | Sat | B14 | A15 | 2077 |

Tested and rejected: forward continuation from December's last week (checked
directly against harvested December sequences for 2029, 2034, 2058, 2075,
2083 — the December pointer ends at B14/B15/B16 in every case, while the
surplus reads B12/B14/B15/A15/A16, so it is neither a continuation nor a
simple repeat).

### Caution: GOA's uncurated data has its own bugs

Do not treat GOA's generated years as infallible. **2031-01-26 is labelled
"Sunday of the Publican and Pharisee: Triodion Begins Today", but GOA's own
April 2031 page gives Pascha as April 13, 2031** — which puts Triodion at
February 2, a week later. GOA's pre-Lenten labels for that cycle are
internally inconsistent with their own Paschalion. This project's Paschalion
agrees with GOA's Pascha date, and the back-anchor analysis (which uses this
project's Triodion) came out 289/289 — so the anomaly is confined to GOA's
labels, not to the reading sequence.

This retracts the note in the previous section flagging 2031-01-19 and
2031-01-26 as app bugs on the Sunday side. **They are GOA data errors; the
app is correct on both dates.**

## The GOA/Antiochian deterministic split — and orthocal's current mixed allegiance

`tools/greek/goa_vs_ant.py` compares the two sources on every date both hold in
the winter window: **56 dates, 46 identical Gospels, 10 different.** The 10
are not one phenomenon. They sort into three classes:

**1. Weekday section divergence (4 days, 1 cycle) — deterministic.**
Cycle 2018 (`jump=7`, `triodion_start=315` — the longest season with the
smallest jump, so the largest gap to fill), all four at `b-2`:

| date | GOA | Antiochian |
|---|---|---|
| 2019-02-04 | Monday of the 15th Week, `Mark 10:46-52` | 17th Monday after Pentecost, `Mark 5:24-34` |
| 2019-02-05 | Tuesday of the 15th Week, `Mark 11:11-23` | 17th Tuesday after Pentecost, `Mark 6:1-7` |
| 2019-02-07 | Thursday of the 15th Week, `Mark 11:27-33` | 17th Thursday after Pentecost, `Mark 6:30-45` |
| 2019-02-09 | Saturday of the 15th Week, `Luke 17:3-10` | 17th Saturday after Pentecost, `Matthew 25:1-13` |

Both jurisdictions have both rules — GOA also returns to the Matthew section
(e.g. 2035-01-24/26). They disagree about *when the Luke-section material is
exhausted*: GOA keeps the back-anchored Luke-section tail at `b-2` and pushes
Matthew-section content into the surplus weeks instead; Antiochian brings it
forward to `b-2`.

**2. Sunday numbering divergence (2 days) — also deterministic.** In cycle
2023, Antiochian runs one week behind GOA at the end of the Luke Sunday
sequence, and terminates on a Luke Sunday where GOA terminates on a Matthew
Sunday:

| date | GOA | Antiochian |
|---|---|---|
| 2024-01-28 | 15th Sunday of Luke, `Luke 19:1-10` | 14th Sunday of Luke, `Luke 18:35-43` |
| 2024-02-04 | 15th Sunday of Matthew, `Matthew 22:35-46` | 15th Sunday of Luke, `Luke 19:1-10` |

**3. Annual-ordo and surplus-week differences (4 days)** — Jan 19 in 2021 and
2024, plus 2021-01-26 and 2026-01-24. Not deterministic; these are the
curated-ordo days already documented above.

### orthocal currently follows *both*, inconsistently

`tools/greek/sunday_alleg.py` asks, on each date where the two sources disagree,
which one `Day(..., tradition='greek')` matches:

- **Weekdays: follows GOA, 4 of 4.**
- **Sundays: follows Antiochian, 2 of 2.**

This is not a choice anyone made; it is an artefact of provenance. The
Sunday machinery (`lukan_sunday_numbers`, `_THEOPHANY_INTERPOLATION`,
`canaanite_woman_applies`) was built and validated against antiochian.org's
official liturgical charts — see `TestGreekLukanNumbering`'s docstring and
`data/antiochian_official_chart_2026.json`. The weekday tail was never
authored at all; it falls out of the shared Pascha-relative `Reading` table,
which happens to agree with GOA.

So `tradition='greek'` today means **Antiochian on Sundays, GOA on
weekdays**. That has to be resolved before any jurisdictional overlay is
built, or the overlay will be layering one jurisdiction's ordo data on top of
another's Sunday logic.

### What accounting for it would take

- **Cheapest: name one jurisdiction and make the other half match.** If GOA,
  `_THEOPHANY_INTERPOLATION` and the Lukan Sunday numbering need rebuilding
  against Kanonion/goarch data (the table has already been rebuilt once, so
  this is known-touchable). If Antiochian, the weekday tail must change — and
  there is currently **no seam to change it at**: the back-anchor is implicit
  in the Pascha-relative pdist computation shared with `slavic`. It would
  have to be promoted into an explicit `GreekYear` method before it can vary.
- **Full split into `greek_goa` / `greek_antiochian`**: schema `choices`,
  fixture rows, API surface, and the same missing seam. Hard to justify for
  6 days per 8 years unless the overlay work makes the distinction load-
  bearing anyway.

### Evidence caveat before committing

The weekday divergence rests on **one cycle**. The other reachable
`jump=7, trio=315` cycle is 2015, which is before antiochian.org's 2018
horizon, and the next is cycle 2026 (Jan 2027), at or past their forward
edge. GOA has many such cycles and is sampleable to 2060+; Antiochian is not.
Confirming Antiochian's behaviour is a stable rule rather than a one-off is
**not currently possible from that source** — which is itself an argument for
treating GOA as the definition of `greek`.

## DECISION (2026-08-26): `tradition='greek'` means GOA

Brian's call, taken deliberately as a working decision rather than a final
one: **GOA is the definition of the `greek` tradition.** Refactoring to
support Antiochian separately is a possible future step, but the axis needs
one unambiguous meaning now.

Reasons, from the section above: GOA has a published multi-year upstream
(the Kanonion PDFs at `/chapel/kanonion`, currently 2021-2027); GOA's
algorithmic output is sampleable to 2060+, which is what made the back-anchor
proof possible; the app already matches GOA on the weekday side; and
Antiochian's 2018-onward horizon makes their divergent behaviour
unconfirmable in principle.

Noted for the future refactor: **antiochian.org publishes an equivalent
annual document**, e.g.
`https://antiochianprodsa.blob.core.windows.net/liturgicalinstructions/Liturgical%20Chart%20for%202026%20English.pdf`
— the direct counterpart to the Kanonion. That makes the eventual Antiochian
overlay a data problem rather than a blocked one.

### Consequence: the Sunday side is now the half that must change

Per the split-allegiance finding, the app follows Antiochian on Sundays. With
GOA chosen, `_THEOPHANY_INTERPOLATION` is the thing that has to be rebuilt.
`data/goarch_sunday_sequences.txt` holds GOA's Sunday sequence for **30
cycles (2010-2039)**; `tools/greek/interp_fit.py`, `tools/greek/pool_fit.py` and
`tools/greek/rule_verify.py` do the analysis.

**Diagnosis: the table is keyed on the wrong thing.** It maps
`regular_extra_sundays` alone to a fixed sequence. But the sequence also
depends on **which Lukan Sunday numbers the autumn actually consumed** —
`lukan_sunday_numbers` leaves either `{12, 14, 15}` or `{12, 15}` unassigned
depending on the year, and GOA fills the interpolation from whatever is left.
The current table is correct for the (n, availability) combinations that
happened to be sampled from antiochian.org's charts, and wrong for the rest:

| n | autumn left 14 free? | GOA sequence | app table | |
|---|---|---|---|---|
| 5 | no | `12L 15L 16M` | `12L 15L 16M` | correct |
| 5 | **yes** | `12L 14L 15L` | `12L 15L 16M` | **wrong** |
| 6 | yes | `12L 14L 15L 16M` | `12L 14L 15L 16M` | correct |
| 6 | **no** | `12L 15L 15M 16M` | `12L 14L 15L 16M` | **wrong** |

This exactly explains the observed failures: cycles 2010/2021/2032 (n=5, 14
free) and 2012/2023 (n=6, 14 taken).

**The rule, verified against 26 of 27 observable cycles.** Build the pool by
this inclusion priority, dropping any Lukan number the autumn already used:

        12L, 15L, 14L, 16M, 15M

take the first `regular_extra_sundays - 2`, and read them out in ascending
order (Lukan numbers first, then Matthean). The final slot is always the
Canaanite Woman / Zacchaeus boundary, already governed by
`canaanite_woman_applies`. The count rule (`n - 2`) holds for 25 of 27.

Note this introduces the **15th Sunday of Matthew**, which the current table
never uses. No new data is needed: `_matthew_sunday_target(15)` is pdist 154,
which already holds `Matt 22.35-46` as a `common` row — precisely what GOA
reads there.

**Two edge cases remain, both involving the count rather than the
selection**, and both in Leavetaking-of-Theophany-on-Sunday years: cycle 2030
(n=3 but 0 interpolated slots) and cycle 2034 (n=5 but 2 slots, and the only
selection mismatch — it omits `12L`, plausibly because the Leavetaking Sunday
consumed that slot). The doc already treats Leavetaking-on-Sunday as a
special case; these should be resolved before the rewrite, not after.

### Resolved: the two "Leavetaking edge cases" were GOA data errors

The two cycles that failed the rule (2030 and 2034) turned out not to involve
Leavetaking at all. Both are cycles where **goarch.org's own "Triodion Begins
Today" contradicts goarch.org's own Paschalion**:

| cycle | this project's Triodion | GOA marks Publican & Pharisee on |
|---|---|---|
| 2030 | 2031-02-02 | 2031-01-26 |
| 2034 | 2035-02-18 | 2035-02-11 **and** 2035-02-18 |

Cycle 2034 is unambiguous: GOA prints Publican and Pharisee on **two
consecutive Sundays**, the later of which matches this project. Pascha 2035 is
April 29 (GOA's own April page agrees), and 70 days back is February 18. In
both cycles GOA's whole pre-Lenten tail is shifted one Sunday early, which
swallows an interpolation slot and truncated the harvest.

Checked systematically: **28 of 30 cycles align exactly**, and the 2 that do
not are precisely the 2 that broke the rule. With them excluded the rule is
**25 matches, 0 failures** (3 further cycles unobservable because a fixed
feast claims a slot). The Leavetaking-on-Sunday handling needed no change --
cycles 2017, 2023 and 2028 all pass with the existing `regular_extra_sundays`
adjustment.

### Implemented

- `_THEOPHANY_INTERPOLATION` (keyed on `n` alone) replaced by
  `_INTERPOLATION_PRIORITY` plus a new `GreekYear.interpolation_sequence`
  cached property implementing the pool rule. `theophany_interpolation` now
  consults it; the Leavetaking `leading` slot is unchanged.
- No data change: the newly reachable 15th of Matthew is pdist 154, already
  carrying `Matt 22.35-46` as a `common` row.
- `TestGreekLukanNumbering.test_theophany_interpolation` updated. The 2023
  cycle's assertions previously carried **antiochian.org's** answer (14th then
  15th of Luke) and now carry **GOA's** (15th of Luke, then 15th of Matthew) --
  this is the one cycle in the sample where the two sources genuinely diverge,
  so it is a deliberate behaviour change under the GOA decision, not a fix.
  Added coverage for the two shapes the old table got wrong: cycle 2010 (n=5
  with the 14th of Luke still free) and cycle 2012 (n=6 with it already used,
  the only shape that reaches the 15th of Matthew).
- App vs GOA on Sundays in this window: **48/56 before, 54/56 after.** The
  two remaining differences are cycle 2030's GOA Triodion error, where the app
  is correct.
- Full suite: 170 tests, 0 failures.

## How much do GOA and Antiochian actually differ? A full-year count

Everything above compares the two sources only inside the winter window. To
size the jurisdictional gap properly, 2026 was compared end to end: `data/`
holds a complete 365-day antiochian.org harvest for that year, and goarch.org
was harvested for all twelve months to match (`data/goa2026.txt`,
`data/ant2026.txt`; `tools/greek/fingerprint.py` builds the Antiochian side,
`tools/greek/year_diff.py` does the comparison).

Both sides are reduced to a canonical `[ordinal]BOOK chapter:verse` fingerprint
of the first reference, compared with the same +/-2 verse tolerance used
elsewhere in this document.

**Calendar year 2026, 365 days compared:**

| | days |
|---|---|
| no Epistle/Gospel listed on one or both sides (aliturgical Lenten weekdays etc.) | 29 |
| source-formatting artifacts (see below) | 5 |
| **genuine differences** | **4** |

That is **roughly 1% of the year** — 4 days out of 336 comparable ones.

The four:

| date | GOA | Antiochian | what it is |
|---|---|---|---|
| 2026-01-24 | `Gal 5:22` / `Luke 18:35` | `Gal 3:23` / `Mark 5:24` | Xenia — the annual-ordo day documented at length above |
| 2026-02-01 | `Rom 8:28` / `Luke 18:10` | `2 Tim 3:10` / `Luke 18:10` | Publican & Pharisee vs. Trypho the Martyr: a precedence difference, same Gospel |
| 2026-02-06 | `Heb 7:26` / `John 10:9` | `2 Tim 2:1` / `John 15:17` | Photius vs. Julian of Homs, an Antiochian-regional commemoration |
| 2026-06-14 | `Rom 2:10` / `Matt 4:18` | `Acts 11:19` / `Matt 4:18` | Antiochian reads Acts 11:19 ("the disciples were first called Christians in Antioch") — a jurisdiction's own patronal commemoration |

Note what these are *not*: only one of the four (Jan 24) belongs to the
lectionary machinery this document has been about. The other three are
commemoration-ranking and regional-saint differences, which the existing
`tradition` field on `Day` already has the shape to express.

**The five artifacts, for the record** — both are source formatting, not
liturgy, and anyone redoing this comparison will hit them:

- antiochian.org writes Jude as "St. Jude's **First** Universal Letter" though
  there is only one (2026-02-19, 2026-06-19). Their ordinals also *follow* the
  book name ("St. Peter's First Universal Letter") where goarch.org's precede
  it ("I Corinthians") -- getting this wrong inflated the count from 4 to 16.
- On Holy Week days (2026-04-06/07/08) antiochian.org carries the **Matins
  Gospel** in `reading1Title`, where the Epistle normally sits, and the
  Liturgy Gospel in `reading2Title`; goarch.org's grid lists a single Gospel.
  Same services, different field layout.

**Caveat on generalising**: this is one year, chosen because it is the only
complete Antiochian harvest in the repo. The winter-window comparison across
2018-2026 (56 shared dates, 10 differences) is consistent with the same order
of magnitude, but a second full year would be needed before treating "about 4
days" as a stable annual figure rather than a 2026 measurement.
