# Greek weekday-drift investigation

**Status: CLOSED.** The fixed-feast portion of the problem is fully solved
and implemented (sections 2-3, 7-8 below, plus the 18-saint Jan 15 - Feb 10
Menaion set added in the final pass). The genuine "free weekday" content in
that same window — the handful of days per year (2-4) where no fixed saint
claims the slot and the site would otherwise need to compute an ordinary
continuous-cycle Gospel/Epistle for Greek specifically — turned out **not
to be solvable from the sources available to this project**. See "Final
disposition: the unsolved recovery mechanism" at the end of this document
for the full account of why, and what was implemented instead.

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

| Year | jump | Nativity weekday | free (likely-wrong) days in Jan15-Feb10 | extends past Feb 10? |
|---|---|---|---|---|
| 2018 | 7  | Tue | 1 (Jan 24) | yes, to Feb 15 |
| 2019 | 28 | Wed | 4 (Jan 24, Feb 4/5/7) | no |
| 2020 | 14 | Fri | 5 (Jan 19/26, Feb 4/5/9) | yes, to Feb 19 |
| 2021 | 28 | Sat | 6 (Jan 19/24/26, Feb 4/7/9) | no — plus `SatAfterNativityFriday` (Dec 31) |
| 2022 | 21 | Sun | 3 (Jan 19/24/26) | no |
| 2023 | 14 | Mon | 6 (Jan 19/24/26, Feb 5/7/9) | yes, to Feb 23 |
| 2024 | 35 | Wed | 4 (Jan 24, Feb 4/5/7) | no |
| 2025 | 14 | Thu | 2 (Jan 19/26) | no |
| 2026 | 7  | Fri | 5 (Jan 19/26, Feb 4/5/9) | yes, to Feb 19 |

(Full 20-year table generated via a direct script walking
`weekday_from_pdist` over each `GreekYear`'s Leavetaking-to-Triodion span;
not reproduced here in full — see the git history of this doc's authoring
session for the exact command if needed.)

**Bottom line**: a typical year has **3 to 7 confirmed-wrong weekdays**,
concentrated in Jan 19 - Feb 9. Two additional, smaller items apply on top:

- **Jan 3 (Forefeast)**: uncertain in roughly 5 of 7 years (whenever
  Theophany's weekday doesn't cause it to be absorbed into
  `SatBeforeTheophany`/`SunBeforeTheophany`) — the 5 independently-sampled
  years disagreed with no pattern found (see "Leftover floats" above), so
  this may already be correct by chance, or may not be.
- **`SatAfterNativityFriday`** (Dec 31): confirmed wrong, but only in
  Nativity-falls-on-Saturday years (2021, 2027, 2032 in the near term —
  roughly 1 year in 7).

**Open question, not yet investigated**: in years where `lukan_jump` is
small (7, or 0 as in 2037), the affected window extends well past Feb 10
(seen as far as Feb 23 in the sample above). Whether those additional
February dates are further fixed Menaion saints (most likely, given the
pattern established for Jan 15 - Feb 10) or more of the same unsolved gap
has **not been checked** — the Menaion confirmation work this session
stopped at Feb 10. This should be the first thing tackled if this
investigation resumes.

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
