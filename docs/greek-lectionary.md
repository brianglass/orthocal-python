# The Greek lectionary in orthocal

How the Greek tradition's readings are computed, where the data comes from,
what is known to be wrong, and how it was all worked out.

**Read Part I for the current state.** Part II is the operational knowledge
about the two sources -- worth reading before harvesting anything, because
several of its traps have each cost a working session. Part III is the
investigation history, kept because it records *why* decisions were made and
which hypotheses are already dead; some of its early sections are superseded
and are marked as such.

Last measured 2026-08-27: against goarch.org over calendar 2026, the app is
**correct on 333 of 336 days (99.1%)**.

---

# Part I — Current state

## The weekday cycle

Two sequences run the ordinary weekdays, both universal and year-independent:
the **Matthew section** (Matthew weekdays for weeks 1-11, then Mark for 12-17)
and, after the Lukan jump, the **Luke section** (Luke weekdays for weeks 1-12,
then Mark for 13-16). Each has its own Saturday series. Both are reconstructed
in full in `data/greek_lectionary_from_labels.json`.

**From the Lukan jump through December**, Greek reads the same shared
Matthew→Mark→Luke weekday sequence Slavic uses, permanently `lukan_jump` days
ahead of it. In Greek's own numbering this is exact: the week label satisfies

        label_week = calendar_week + 1

for every one of **303 labelled days across 9 independent cycles**, with no
exceptions.

**The three weeks before Triodion are back-anchored**, not forward-anchored:
they always read Luke-section weeks **14, 15 and 16**, whatever that year's
`lukan_jump`.

| weeks before Triodion | week read | observations | exceptions |
|---|---|---|---|
| last | 16 | 145 | 0 |
| second-last | 15 | 96 | 0 |
| third-last | 14 | 48 | 0 |

The app gets this right by construction -- its Gospel pdist is Pascha-relative
and Triodion is a fixed Pascha offset -- and `TestGreekPreTriodionWeekdayCycle`
pins it across every jump value from 0 to 35.

This back-anchoring is why every earlier attempt failed. Modelling the pointer
as running *forward* and "lagging" across the Nativity/Theophany cluster makes
the lag look year-dependent, so every rule expressed in terms of `lukan_jump`
was fitting noise -- `triodion_start` varies independently of it, since it
depends on the *following* year's Pascha.

## The Sunday cycle

`GreekYear.lukan_sunday_numbers` handles the autumn numbering, including the
reserved windows and the Apostle-feast overrides.

Between Theophany and Triodion the extra Sundays are filled by
`GreekYear.interpolation_sequence`. Build the pool in this inclusion priority,
dropping any Lukan number the autumn already consumed:

        12th of Luke, 15th of Luke, 14th of Luke, 16th of Matthew, 15th of Matthew

take the first `regular_extra_sundays - 2`, and read them out ascending (Lukan
first, then Matthean). The final Sunday before Triodion is the Canaanite Woman
/ Zacchaeus boundary, governed separately by `canaanite_woman_applies`.

Verified against **25 cycles with zero failures**. The sequence is *not* a
function of `regular_extra_sundays` alone, which is what the previous
`_THEOPHANY_INTERPOLATION` table assumed; it also depends on which Lukan
Sundays the autumn used up.

## The annual-ordo days

**January 19, 24 and 26 are not computable.** They carry venerable-monastic
commemorations whose Menaion entries supply an Epistle but no proper Gospel, so
the Gospel falls to whatever that year's ordo assigns.

That this is genuinely not computable was established rather than assumed: past
its published Kanonion horizon, goarch.org's own software stops assigning these
days and falls back to a commons Gospel (`Matt 19:16-26`) invariantly -- and
that fallback matches the curated ordo in **1 of 15** sampled years. The
curated values span the 3rd through the 16th Sunday of Matthew with no
derivable pattern.

They are therefore carried as data in `models.OrdoReading`, keyed by
`(jurisdiction, year, month, day, source)`.

**Where the two jurisdictions' ordos disagree, both readings are shown, each
labelled** -- "(Gospel, GOA)" and "(Gospel, Antiochian)" in the reference index,
"(Gospel, Greek Archdiocese)" and "(Gospel, Antiochian Archdiocese)" in the
passage heading and the API -- the
same treatment this project already gives a saint's reading standing beside the
cycle's. A jurisdiction is only named when there is another to contrast it
with: where the ordos agree, or where only one has published (anything before
antiochian.org's 2018 horizon), the reading shows plainly. That happens on
about four dates a year; `Day._add_ordo_alternatives` does it, and the label
reaches the API as a reading's `description`. **This is a per-year overlay, the
only one in this codebase**, and it deliberately reverses the constraint this
investigation began under. It covers about two dates a year and is currently
good through **January 2027**; extending it means re-harvesting goarch.org and
running `tools/greek/load_ordo.py`.

## Everything else

Fixed feasts, the Nativity/Theophany floats, the Forefeast and Afterfeast of
Theophany, the Jan 15 - Feb 10 Menaion set, and the Lukan-numbering crash fixes
are all implemented and recorded in Part III.

## What is still wrong

Ranked by how much they cost a reader:

1. **The unmodelled pointer suspension.** The app runs the Luke-section cycle
   weekday-aligned and consistent with its own week label. GOA's content
   pointer instead falls behind, because the Nativity/Theophany cluster
   consumes days it never makes up -- the Typikon's "omission and repeat". The
   app models no suspension at all, and that shows up in two places:

   - **The surplus weeks**, after Leavetaking. In long seasons
     (`triodion_start >= 308`, about one year in five) there are more weeks
     before Triodion than the back-anchored tail covers. The app extends the
     tail backward (weeks 13, 12), consistently -- 302 of 302 days. GOA
     repeats weeks instead, reproducibly but with no derivable rule.
     **~6.5 days a year, 68% of cycles.**
   - **The last days of December**, before Theophany. Here GOA's content
     disagrees with **its own label**: on 2026-12-30, labelled "Wednesday of
     the 15th Week", it reads `Mark 10:17-27`, which is week 14's Thursday.
     The app follows the label. Roughly **1-2 days a year**, and only when
     Nativity falls late enough in the week for the cluster to eat the days --
     Friday in 2026 and Saturday in 2021 both show it, Thursday in 2025 does
     not.

   Across the whole harvest, **13 Luke-section days have content contradicting
   their own label**: 7 in January (the annual-ordo days, now fixed), 3 in
   December and 1 in February (this suspension), and 2 in November 2020 that
   look like source glitches rather than the mechanism.

   Deliberately left alone -- see Part III for why the rule could not be
   derived and why a configuration table was rejected.
2. **Jan 3 (Forefeast of Theophany).** Genuinely inconsistent across every
   sampled year; all five obtainable samples are already in hand.
3. **`SatAfterNativityFriday`** (Dec 31, only when Nativity falls on a
   Saturday, roughly one year in seven).
4. **Royal Hours.** Four-part services neither source's feed can express.

## Accuracy, measured

| | days compared | correct |
|---|---|---|
| app(Greek) vs goarch.org, calendar 2026 | 336 | **333 (99.1%)** |

Three remain, and none is addressable from these sources:

| date | what |
|---|---|
| 2026-04-10 | Holy Friday -- the Royal Hours structure, which neither feed expresses |
| 2026-12-30, 12-31 | the pointer suspension, in its pre-Theophany form. These are **not** the surplus weeks, which sit after Leavetaking; both are the same unmodelled mechanism in different parts of the season |

Against **antiochian.org** over the same year the figure is 6 days of 365.
Three of those are the shared unsolved items above; the other three are dates
where the two jurisdictions genuinely differ, and on the annual-ordo ones both
readings are now shown side by side rather than only GOA's.

There is no separate Antiochian tradition: one was built, measured and removed
-- see Part III.

---

# Part II — Working with the sources

Two jurisdictions publish the Greek-tradition calendar, and neither is a clean
API. Everything here was learned the hard way; each trap below cost real time.

## antiochian.org

A JSON feed, ingested by `ingest_antiochian.py` into `data/antiochian_raw/`
(currently ~1500 days, 2018-2026).

- **Horizon: 2018 through roughly one year ahead.** 2015-2017 and earlier fail
  consistently; so does anything much beyond a year out. Several questions in
  Part III were closed as "permanently unobservable" on this basis --
  **reconsider all of them against goarch.org**, which has no such limit.
- **Isolated single-date gaps exist** inside the reachable window (2021-01-01
  fails while every surrounding date works). A single failure surrounded by
  successes is a data gap, not a horizon.
- **The anchor bug.** `authenticate()` anchors `itemId 0` to "today", which can
  be off by one depending on when the API rolls over. This silently produced a
  whole harvest cached under the *wrong* filenames. `get_liturgical_day` now
  validates `originalCalendarDate` against the requested date and re-anchors
  once. If you write a new harvester, do the same.
- **`feastDayTitle` carries the day's lectionary slot**, not just a saint's
  name -- `"17TH TUESDAY AFTER PENTECOST"` (Matthew section) or
  `"TUESDAY OF THE 15TH WEEK"` (Luke section). This is Greek's own numbering
  and it is what made the weekday cycle tractable. It is hidden whenever a
  ranking commemoration claims the day.

## oca.org

The source this project's `common`/`slavic` data was originally compiled from,
and the one to check before assuming a reading is Greek-specific.

- Daily: `https://www.oca.org/readings/daily/YYYY/MM/DD`
- A whole year at once: `https://www.oca.org/readings/monthly/YYYY`

Plainly fetchable -- no API, no bot blocking. It lists everything for the day,
Vespers and Matins included, so a saint's proper readings are distinguishable
from the daily cycle by what else is present. Lives of the saints are at
`/saints/lives`.

Note that a commemoration appearing on the page does not mean it has proper
readings: oca.org lists the Appearance of the Cross on May 7 and the Myrtle
Tree icon on Sep 24, and gives neither a Liturgy reading.

## goarch.org

No API, and Cloudflare blocks scripted access -- `requests`, `curl` and
`WebFetch` all get 403, and a real browser engine still lands on the
"Performing security verification" interstitial.

- **How to harvest**: have a human clear the interstitial once in their own
  browser, then `fetch()` further months from *inside the page origin*.
  Same-origin requests inherit the clearance for the rest of the session. One
  manual click buys a whole harvest.
- **No horizon.** It serves 2011 and 2060+ equally well.
- **Past its published Kanonion horizon the data is pure algorithm**, which
  makes it an arbitrarily large, noise-free oracle for the *reading cycle*.
  That is what made the back-anchor proof possible.
- **But its generated years contain real errors.** Its own
  "Triodion Begins Today" contradicts its own Paschalion in 2 of 30 sampled
  cycles; in 2035 it prints Publican and Pharisee on **two consecutive
  Sundays**. Check `tools/greek/pp_align.py` before trusting a cycle.
- **The Kanonion PDFs** at `/chapel/kanonion` are the upstream the curators
  work from -- ordinary text PDFs, ~180 KB, unencrypted, no scanned pages. Not
  currently needed, since the web calendar carries the same curated data.
- Month grid, which prints label *and* both citations together:

        /chapel/calendar?month=M&year=YYYY&viewStyle=GridView&viewType=ViewReadings

  It parses out of `innerText` as `[day, long date, fasting lines, label,
  saints..., 'Epistle Reading', '-', epistle, 'Gospel Reading', '-', gospel]`.

## Traps when comparing the two

Every one of these has produced a false result at least once:

- **Ordinal position differs.** antiochian.org writes the ordinal *after* the
  book ("St. Peter's **First** Universal Letter"); goarch.org writes it before
  ("I Corinthians"). Getting this wrong inflated one comparison from 4
  differences to 16.
- **antiochian.org calls Jude "St. Jude's First Universal Letter"** though
  there is only one.
- **Single-chapter books.** This repo cites Jude without a chapter
  (`Jude 11-25`) where the sources write `1:11-25`.
- **Holy Week reuses the fields.** antiochian.org puts the **Matins** Gospel in
  `reading1Title`, where the Epistle normally sits, and the Liturgy Gospel in
  `reading2Title`. Any code assuming `reading1 = Epistle` is wrong there.
- **Aliturgical Lenten weekdays reuse them too**, for the Vespers Old Testament
  readings. There is no Epistle or Gospel to compare on those days.
- **A ±2 verse tolerance is not safe on its own.** `Mark 5:24-34` (the woman
  with the issue of blood) and `Mark 5.22-24, 35-6.1` (Jairus' daughter) open
  two verses apart and are different pericopes. Match the *closing* reference
  too. This shipped one wrong ordo row before it was caught.
- **A one-verse opening difference is usually benign**, though: this repo
  carries `Matt 22.1-14` where both jurisdictions print `22:2-14`, and there
  are several such boundary variants.
- **Coincidental text reuse.** The same pericope recurs at unrelated positions
  (saints' commons, the cycle repeating). Matching a citation against the
  `Reading` table without a plausibility window produces confident nonsense --
  this is what derailed the first two investigations. Resolve through the
  *labels* instead wherever possible.

## Other operational notes

- **Regenerate fixtures with `--indent=2`.** The default reformats
  `fixtures/calendarium.json` end to end -- 62k insertions and 61k deletions,
  unreviewable. With the right indent an overlay change is a few hundred added
  lines and zero deletions.
- **A `GreekYear(Y)`'s Nativity is in December of `Y`, but its Theophany is in
  January of `Y+1`.** A file named `2025-01-04.json` belongs to
  `GreekYear(2024)`. Associating January dates with the wrong `GreekYear`
  produced a convincing-looking phantom bug once.
- **The sqlite database is a read-only build artifact**, loaded from the
  fixture at image build time. A fixture row and a Python constant therefore
  cost exactly the same to change; "update without a deploy" is not available
  for either.

## Tooling

`tools/greek/` holds the analysis scripts, with a README mapping each claim in
this document to the script and data that establish it. None of it is
application code.

---

# Part III — How this was worked out

Chronological, oldest first. Sections marked SUPERSEDED record
reasoning that later work overturned; they are kept because they
document which hypotheses are already dead and why, which is worth
more than the space they cost.

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

### 6 and 7 (SUPERSEDED) -- the quantitative trigger, and the "recovered
Matthew-Sunday" mechanism

Two long hypotheses lived here and are both dead. They are summarised rather
than reproduced because their observations were real and their conclusions were
not.

**#6 hunted for a formula connecting `lukan_jump` to the disrupted window.**
Every candidate was falsified: counting named weekdays across the whole
Nativity-Theophany span (roughly constant regardless of jump, so it cannot
repay one that varies 7 to 35); narrowing to the Typikon's literal seven named
occasions (cannot arithmetically repay 35 by 1-for-1 counting); and several
pure week-number formulas anchored variously on the Sunday after Elevation, the
jump date, and `triodion_start`, each matching over a short window and breaking
on cross-checks.

**#7 concluded that Matthew Sundays displaced by the jump were recovered later
as weekdays**, drained FIFO from `first_sun_luke - 7` at `lukan_jump / 7` items.
The observation was sound -- Jan 19, 24 and 26 really do carry numbered Sundays
of Matthew. The mechanism was not: implemented and then disproven against two
further jump values (2018 predicted one item and the hit resolved nine weeks
away; 2023 predicted two and produced three, out of order). The code was
reverted rather than shipped.

**What was actually going on**, established much later: those three dates are
annual-ordo days, assigned by hand from each jurisdiction's published calendar
and not computable at all -- see Part I. The Matthew Sundays are what the ordo
happens to assign, not the output of a recovery queue. And the ordinary weekday
cycle is back-anchored to Triodion, which is why no jump-based formula could
ever have fitted it.

Both efforts were also handicapped by resolving citations against this
project's Slavic-built `pdist` table, which produces confident false matches
through coincidental text reuse. See Part II.

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
  unreliable (the surplus weeks -- see Part I). Neither the old
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

The original plan (in an earlier revision of this document) assumed
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

## Final disposition of the recovery mechanism (SUPERSEDED)

The `first_sun_luke - 7` / `lukan_jump // 7` formula from #7 was implemented,
wired into `GreekYear`/`Day.gospel_pdist`, disproven against two more jump
values, and reverted. The investigation closed here, concluding the gap was
"not solvable from the sources available" -- correct about the sources it was
using, wrong about the problem.

Two observations from that pass are still worth having:

- The Typikon says only two sentences about the weekday mechanism ("after we
  finish the readings from St. Luke, we return to St. Matthew and count the
  weeks that are left from the Sunday after the Elevation"). There is no
  weekday equivalent of its detailed Sunday table. The day-by-day arithmetic
  lives in an annual ordo, which turned out to be exactly right -- see Part I.
- antiochian.org's own day labels for this window did not line up with this
  project's Slavic-built pdist positions, which was read at the time as
  evidence that the matches were coincidental. They were coincidental, but the
  labels were the answer rather than the problem -- see the label-index section
  below.

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

## Known scope of remaining incorrectness (SUPERSEDED -- see Part I)

This section carried a 20-year table estimating 0-5 wrong weekdays a year, and
a correction to it after several dates turned out to be Sundays rather than
weekdays. Both are superseded by direct measurement against both sources; Part
I carries the current figures.

Two findings from it survive intact:

- **The window is bounded** between the Theophany afterfeast and each year's
  Triodion start. Dates past Triodion are ordinary pre-Lenten content shared
  with `SlavicYear`, confirmed by cross-year agreement (2018-02-12/13 matches
  2023-02-20/21 exactly; 2020-02-18 matches 2023-02-14). Nothing beyond that
  boundary is at risk.
- **goarch.org agreeing with antiochian.org on a known-wrong day is evidence
  against "antiochian.org has a bug"** -- confirmed manually on 2025-01-24
  (2026-07-22), and the basis for later treating the two sources as
  cross-checks rather than rivals.

## Jan 19 and Jan 24: the Epistles are fixed, the Gospels are not

Checking whether the "confirmed-wrong" free weekdays were simply missing
Menaion data found a real split.

- **Jan 19 (Macarius the Great) and Jan 24 (Xenia of Rome)**: the Epistle is
  genuinely fixed across every sampled year (`Gal 5:22-26; 6:1-2`, 5/5 for
  both) -- missing data, not drift. **Both added** as `greek`-tagged rows
  (pdist 999, reusing Pericope 647), purely additive; the existing `common` row
  stays correct for Slavic, confirmed against oca.org, which shows a different
  Epistle on those dates.
- **Jan 26 and the February dates**: no fixed pattern at all. Feb 4 alone shows
  five different non-repeating Epistles across five years.

The Gospel side of Jan 19/24 stayed wrong after this pass. It is now handled as
annual-ordo data -- see Part I.

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

## The GOA/Antiochian split, and the mixed allegiance it exposed (RESOLVED)

Comparing the two sources on every date both hold in the winter window: **56
dates, 46 identical, 10 different**. Three classes, of which two are
deterministic:

- **Weekday section divergence (4 days, one cycle).** In the 2018/19 cycle
  (`jump=7`, `triodion_start=315`), all four at two weeks before Triodion, GOA
  keeps the back-anchored Luke-section tail (`Mark 10:46-52`, `11:11-23`,
  `11:27-33`, `Luke 17:3-10`) where antiochian.org returns to the Matthew
  section (`Mark 5:24-34`, `6:1-7`, `6:30-45`, `Matthew 25:1-13`). Both have
  both rules; they disagree about when the Luke material is exhausted.
- **Sunday numbering divergence (2 days).** In cycle 2023, antiochian.org runs
  a week behind GOA at the end of the Luke Sunday sequence and terminates on a
  Luke Sunday where GOA terminates on a Matthew one.
- **Four annual-ordo and surplus days**, covered elsewhere.

**The uncomfortable part:** the app was following *both*. On dates where the
sources disagreed it matched GOA on weekdays 4 of 4, and antiochian.org on
Sundays 2 of 2. Nobody chose that -- the Sunday machinery had been validated
against antiochian.org's charts while the weekday tail fell out of the shared
Pascha-relative table. Resolved by the decision below, and by rebuilding the
interpolation against GOA.

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

## The pointer suspension: mechanism identified, rule not derivable, app left alone

Originally written about the surplus weeks alone. The same mechanism has a
second, earlier symptom -- see "The pre-Theophany symptom" at the end of
this section.

Picking this up after the interpolation fix, with a much larger goarch.org
sample. Four findings, and the conclusion is the opposite of what the earlier
"0/14 correct" framing suggested.

### 1. It is far bigger than the audit made it look

The audit could only *observe* Jan 24 and Jan 26 — every other weekday in the
span carries a fixed commemoration, so goarch.org prints the saint's name
instead of a week label. But the app still shows a continuous-cycle reading
alongside the saint's on those days, so the user-visible span is the whole
surplus region. `tools/greek/surplus_impact.py`, over 2010-2059:

- **34 of 50 cycles affected (68%)**
- **324 affected weekdays over 50 years = 6.5 per year**
- in an affected year, **9.5 days**, up to **18** in the longest seasons

This is the largest remaining source of Greek weekday divergence — an order of
magnitude more than the annual-ordo days (Jan 19/24/26) that consumed most of
the earlier investigation.

### 2. The mechanism is repetition, and it is proven

Cycle 2031 settles it. `tools/greek/surplus_map.py` lays the weeks out:

        b-5 = 14, b-4 = 15, b-3 = 14, b-2 = 15, b-1 = 16

Weeks 14 and 15 are each read **twice**, and not by inference — 2032-01-24 and
2032-02-07 both carry `Luke 16:10-15`, the Saturday of week 14, on a Saturday.
Same slot, same citation, two weeks apart. This is the Typikon's "omission and
repeat" operating at week granularity.

### 3. Forward continuation is definitively dead

`tools/greek/surplus_forward.py` tests the obvious hypothesis — that the
December pointer (`label_week = calendar_week + 1`, proven exceptionless
through Dec 31) simply keeps running. It does not: **0 matches, 22 misses**.
The forward pointer would be at week 19, which does not exist; the Luke section
has 16. That is precisely *why* there is a gap to fill.

### 4. The app is not producing noise here — it applies the proven rule

This is the finding that changes the recommendation. `tools/greek/surplus_app_rule.py`
checks whether the app extends the back-anchor backward — b-4 = week 13,
b-5 = week 12, continuing 16/15/14 outward:

        302 surplus days checked, 302 follow the extended rule. 100%.

So the app is not wrong-by-accident in the surplus region. It applies the
natural, coherent continuation of the rule that is *proven* correct for
b-1/b-2/b-3 (289/289). GOA instead stops counting backward and starts
repeating weeks.

### Why no rule was derived, and why that is probably fine

GOA's surplus fill is reproducible — configurations 11 years apart agree
exactly — but varies by `(lukan_jump, triodion_start, Nativity weekday)` with
no derivable logic. Across the harvested long cycles it variously repeats week
15, repeats week 14, alternates 14/15, reaches back to week 12, or switches to
the Matthew section (A15/A16). No formula fits.

A lookup table keyed on those three values *would* be deterministic and
year-independent, so it would satisfy this document's standing constraint. It
was rejected anyway: there are **~20 distinct long-season configurations**, only
12 of which are harvestable from cycles near enough to matter — the rest first
occur in 2118, 2132, 2172, 2189. Those are deep in goarch.org's uncurated
range, which is exactly where their generator is demonstrably unreliable (two
cycles in thirty put Triodion on the wrong Sunday; 2035 prints Publican and
Pharisee twice). Fitting a table to that would be encoding someone else's
fallback code, including entries we cannot check.

**Recommendation: leave the app as it is, and document the divergence.** The
cost is real and should not be minimised — the app knowingly differs from the
chosen source of truth on ~6.5 days a year. But the alternative is replacing a
coherent extension of a proven rule with a fitted table derived from the least
trustworthy part of the source. If this is revisited, the harvest is now cheap:
`tools/greek/surplus_map.py` and one `__daily()` call per cycle (see
`tools/greek/README.md`), and `data/goarch_daily_long_cycles.txt` holds full
daily Gospels for three clean long cycles to start from.

**The deterministic portion is therefore complete**: the Luke-section weekday
cycle is back-anchored to Triodion and counts backward 16, 15, 14, 13, 12; the
app implements exactly that; weeks 16/15/14 are confirmed against GOA at
289/289, and 13/12 are the rule's own continuation, where GOA substitutes
repeats.

## The annual-ordo days: implemented as a deliberate per-year overlay

### The Kanonion PDFs are parseable — and turn out not to be needed

Answered the load-bearing question by inspecting `2027 Kanonion - English.pdf`
in place (HEAD plus an in-memory structural read, no download): **180 KB,
PDF 1.6, unencrypted, FlateDecode throughout, 9 object streams, 2 images (a
logo).** An ordinary text PDF; any PDF library would read it. Far too small to
be scanned pages.

But it is not the shortest path. **goarch.org's web calendar already publishes
the same curated data**, and this project has already proven it can extract it.
The PDF matters only if an offline or more authoritative copy is wanted later.

### Scope

`tools/greek/ordo_coverage.py` checks every weekday Jan 19/24/26 slot across
GOA's curated range: **42 slots over 2011-2027, of which 38 disagreed with what
the app computed.** About 2.2 dates a year.

`tools/greek/ordo_resolve.py` then resolves each ordo Gospel against the
existing `Reading` table: **41 of 42 land on a plain pdist**, overwhelmingly
numbered Sundays of Matthew — which is what finding #7 was circling all along.
No new `Pericope` or `Reading` rows are needed.

The one holdout is **2013-01-26**, where goarch.org shows `Mark 1:1-8` — the
Sunday-before-Theophany Gospel — on a Saturday labelled "of the 15th Week".
That pericope exists only at float pdists, and the pairing looks like an error
on their side, so it is left to the ordinary cycle.

### Why this is data and not a formula

Restating the evidence, because it is what justifies reversing the standing
constraint. Past their Kanonion horizon GOA's software stops assigning these
days and falls back to a commons Gospel, `Matt 19:16-26`, invariantly. That
fallback matches the curated ordo in **1 of 15** sampled years. The curated
values span the 3rd through the 16th Sunday of Matthew with no derivable
pattern. There is no formula to find, and shipping GOA's own fallback would be
wrong 14 times in 15.

### Implementation

Held in the database as `models.OrdoReading`, keyed by
`(jurisdiction, year, month, day, source)` and carrying the target `pdist`
plus a provenance note. `Day._collect_ordo_readings()` loads the row set for
the date during `ainitialize`, and `Day.gospel_pdist` consults it first.

The lookup happens in `ainitialize` rather than in `gospel_pdist` because
`gospel_pdist` is a sync `cached_property` and the DB access has to stay
async -- the same reason `_collect_commemorations` exists. `Day.__init__`
defaults `ordo_readings` to `{}` so the property can read it unconditionally.

Pointing at a `pdist` rather than a `Pericope` means the ordo **replaces** the
computed reading instead of being listed beside it (overriding the pdist
changes which `Reading` row gets selected), and no synthetic rows are needed.
`_ORDO_JURISDICTIONS` maps a tradition to the jurisdiction whose ordo it
follows; Slavic is absent, so it cannot pick anything up.

**Why the database and not a constant in code.** The first cut was a dict in
`GreekYear`, which was defensible while the overlay had one jurisdiction: this
project's sqlite is a read-only build artifact (`Dockerfile`: *"The sqlite
database is read-only, so we build it into the image"*), no admin is
registered, and the fixture is loaded at image build time -- so a fixture row
and a Python constant cost exactly the same to change. What tipped it was the
decision to carry **both** the GOA and Antiochian ordos: a jurisdiction axis
makes this data rather than a constant, and puts it where the rest of the
lectionary lives so it is discoverable by anyone asking why a given date shows
what it shows.

Result: **41 of 42 curated Greek slots now match GOA**, up from 4.

Antiochian rows are loaded too (18, covering 2019-2026, from the existing
antiochian.org harvest). **Nothing reads them yet** -- no tradition maps to
that jurisdiction, and adding one is the separate refactor costed earlier in
this document. They are a faithful transcription and are stored so the data
half of that work is already done. They also make the axis concrete: of the 18
dates the two jurisdictions share, they agree on 14 and differ on 4.

### The maintenance commitment, stated plainly

This is **a per-year data overlay, the only one in this codebase**, and it
directly reverses the constraint recorded at the top of this document. It was
adopted because the evidence now shows no algorithm exists for these days, and
because the cost is small and bounded: about two rows a year.

It needs extending as GOA publishes each new Kanonion — currently good through
**January 2027**. Beyond that the app falls through to the ordinary cycle,
which is wrong but no worse than before. Re-harvest goarch.org, then
`tools/greek/load_ordo.py` repopulates the table and `dumpdata` regenerates
`fixtures/calendarium.json` -- see that script's docstring for the two
commands.

## Antiochian as its own tradition: built, measured, removed

A selectable Antiochian tradition was implemented in full -- `Tradition.Antiochian`,
`AntiochianYear`/`AntiochianDay`, a tradition lineage so it inherited Greek's
rows, the URL converter, the UI picker, the API -- and then reverted. The
measurements that killed it are worth keeping, because the idea is an obvious
one to have again.

### The gap is mostly not Antiochian

`tools/greek/antiochian_gap.py` and `tools/greek/goa_gap.py` measure each
tradition against its own source over a complete year (2026, the only year with
a full harvest of both):

| | days compared | wrong |
|---|---|---|
| app(Greek) vs goarch.org | 336 | **13** (96.1% correct) |
| app(Antiochian) vs antiochian.org | 365 | **16** |

`tools/greek/three_way.py` then splits those 16 by asking what goarch.org says
on the same date:

- **11 are shared bugs** -- goarch.org agrees with antiochian.org and the app
  differs from *both*. These are Greek-tradition defects; fixing them helps
  every tradition.
- **3 are audit artifacts** -- Holy Week, where antiochian.org lists the Matins
  and Liturgy Gospels while goarch.org lists one. The app has both and is right.
- **3 looked genuinely jurisdictional.**

So an Antiochian user switching from Greek to Antiochian would have gained
about one day a year.

### And the three jurisdictional ones are not stable rules

Each was checked across the whole harvest rather than trusting the 2026
snapshot. None survives:

- **Feb 6** -- Photius in **6 of 7 harvested years**; Julian of Homs only in
  2026. A row keyed on this date would be wrong six years in seven. (The
  "Implemented (final pass)" section above had already flagged 2026 as the lone
  exception here; this confirms it.)
- **Jun 14** -- Elisseus, then the Apodosis of Pentecost, then the 2nd Sunday of
  Matthew across years. `Acts 11:19-30` appears in 2026 only because the date
  fell on a Sunday; it is the Sunday *cycle* Epistle, where GOA reckons
  `Rom 2:10`. It is not a patronal commemoration, which is what it looked like
  from one year's data.
- **Jan 26** -- the Epistle differs every single year. A cycle reading, not a
  Menaion one.

**There is no set of Antiochian-specific data rows to add.** The genuine
jurisdictional differences live in the moveable cycles -- post-Pentecost
Epistle numbering, and the weekday-section divergence documented earlier --
and deriving those needs more years than antiochian.org serves (2018 through
roughly one year ahead). That is the same horizon wall the surplus weeks hit.

### What was kept

- **The dropdowns.** The tradition and calendar controls became `<select>`s,
  following the pattern the translation picker already used. An independent UI
  improvement, unrelated to the Antiochian question. The traditions were
  briefly relabelled OCA/GOA and are back to Slavic/Greek, with the
  jurisdictions carried as per-option tooltips the way the old toggles did.
- **`models.OrdoReading`'s `jurisdiction` column and its 18 Antiochian rows.**
  Nothing reads them -- no tradition maps to that jurisdiction any more. They
  are correct transcriptions and are kept so that re-adding the tradition, if
  antiochian.org's horizon ever widens, is a small change rather than a
  re-harvest.
- **API compatibility restored**: reverting the converter puts `antiochian`
  back to aliasing `greek`, so no URL changed meaning after all.

### What this points at instead

The 11 shared bugs. The app is 96.1% against GOA over a full year, and those
eleven days are most of the remainder. Two of them are the unsolved surplus
weeks; the rest are missing or wrong fixed-feast readings. Unlike the
Antiochian work, that is not blocked by a source horizon -- goarch.org is
sampleable to 2060 and antiochian.org corroborates. `tools/greek/three_way.py`
produces the list.

---

## Shared bugs: six Greek Menaion readings added (2026-08-27)

`tools/greek/three_way.py` compares the app against both sources at once and
splits its errors into two piles that need different fixes: dates where the two
sources **agree** and the app differs from both (a Greek-tradition defect), and
dates where the sources **disagree** (jurisdictional). For calendar 2026 the
split was 11 shared against 3 jurisdictional, with 3 more turning out to be
artifacts of the comparison rather than real.

Working the shared pile needed one methodological correction. Grouping the
differences by calendar date conflates a fixed saint with the moveable feasts
that periodically outrank it: April 25 is Mark the Apostle in five harvested
years, and Holy Thursday, Palm Sunday or Renewal Monday in the other three.
`tools/greek/classify_shared.py` groups by what actually fell on the date each
year, which makes the fixed readings visible.

Six rows added, all `greek`-tagged and additive, each confirmed across multiple
independent years of antiochian.org harvest **and** corroborated by goarch.org
for 2026:

| date | source | reading | evidence |
|---|---|---|---|
| Apr 25 | Gospel | `Luke 10.16-21` | Mark the Apostle, 5/5 years carrying that commemoration |
| Apr 30 | Gospel | `Luke 9.1-6` | James the Apostle, 2/2 |
| Jul 13 | Epistle | `Heb 2.2-10` | Synaxis of Gabriel, 4/5 (the exception is a Sunday) |
| Aug 31 | Epistle | `Heb 9.1-7` | Placing of the Sash, 5/5 |
| Aug 31 | Gospel | `Luke 10.38-42, 11.27-28` | Placing of the Sash, 4/5 |
| Dec 17 | Epistle | `Heb 11.33-12.2` | Daniel and the Three Youths, 7/8 |

Every pericope already existed; no new `Pericope` rows were needed. Two of
these (Apr 25 and Apr 30) override an existing `common` Gospel for the Greek
tradition while leaving it in place for Slavic --
`TestGreekMenaionReadings.test_slavic_is_unaffected` asserts that rather than
assuming it.

### Four more, after filling in the harvest

Three of the remaining differences looked like moveable-cycle problems or had
too little evidence. All three turned out to be fixed Menaion readings whose
evidence was simply missing, because the standing harvest is winter-weighted.
`tools/greek/harvest_dates.py` pulls specific calendar dates across years from
antiochian.org's API -- worth reaching for whenever a date has too few samples,
since the API is unrestricted within its horizon and this took one run.

| date | source | reading | evidence |
|---|---|---|---|
| May 7 | Epistle | `Acts 26.1-5, 12-20` | 3/3 of the years May 7 is a weekday |
| Jul 5 | Epistle | `Gal 5.22-6.2` | 8/8 years, including both Sundays |
| Jul 5 | Gospel | `Matt 11.27-30` | 6/8; the two exceptions are Sundays |
| Sep 24 | Gospel | `Luke 10.38-42, 11.27-28` | 4 consecutive recent years |

**May 7** was the one that looked like a Paschal-season Epistle-cycle bug. It is
not: `Acts 26:1, 12-20` is the Epistle for **Ss Constantine and Helen**, which
this project already carries as a `common` row on May 21, and May 7 is the
Appearance of the Cross over Jerusalem -- the vision granted to Constantine,
with Acts 26 being Paul recounting the light from heaven. It shows up only when
May 7 lands on a weekday. Note the shape: the *Epistle* is fixed while the
*Gospel* stays with the Paschal cycle, which is why the Gospel always matched.

**Jul 5** is a tagging problem rather than missing data. Slavic already carried
`Gal 5.22-6.2` -- tagged `slavic`, so Greek fell through to the cycle. The
Gospel genuinely differs: Slavic reads `Luke 6:17-23` at Liturgy and has
`Matt 11:27-30` only as its Matins Gospel.

**Sep 24** is a Greek commemoration Slavic does not keep -- the Miracle of the
Theotokos Myrtidiotissa -- hence the Theotokos Gospel where the `common` row
has `Luke 21:12-19` for St Thekla. The source changed here: antiochian.org
showed `Luke 5:12-16` in 2019-2021 and `Luke 10:38-42, 11:27-28` in every year
from 2022 through 2026, which goarch.org corroborates for 2026. The later,
stable value was taken.

**Result: 96.1% -> 99.1% against goarch.org over a full year**, 13 wrong days
down to 3.

### A note on the audits themselves

Two of the "differences" in the first run were the comparison's fault, not the
app's: `goa_gap.py` did not handle single-chapter books, so every Jude citation
failed to canonicalise. Fixing it moved the figure from 97.6% to 98.2% without
touching any data. When a gap analysis reports a suspiciously round pile of
errors in one book or one season, suspect the canonicaliser first -- an earlier
pass in this document reported 87.9% differing for exactly this reason.

### The pre-Theophany symptom (correction, 2026-08-27)

The surplus weeks are not the only place the missing suspension shows. An
earlier revision of this document described the two remaining 2026
differences -- 2026-12-30 and 2026-12-31 -- as "the surplus weeks". **They are
not.** They sit at eight weeks before Triodion, in late December, *before*
Theophany; the surplus weeks are after Leavetaking. Same mechanism, different
part of the season.

What happens there is that goarch.org's content disagrees with **its own
label**:

| date | GOA label | GOA reads | which is |
|---|---|---|---|
| 2026-12-30 (Wed) | Wednesday of the 15th Week | `Mark 10:17-27` | week 14 Thursday |
| 2026-12-31 (Thu) | Thursday of the 15th Week | `Mark 10:24-32` | week 14 Friday |

The app follows the label -- weekday-aligned and self-consistent, which is also
what GOA's own labelling says. GOA's content pointer is running behind because
the Nativity cluster consumed days it never made up.

Frequency: **1-2 days a year**, and only when Nativity falls late enough in the
week for the cluster to eat them. Nativity was a Friday in 2026 and a Saturday
in 2021 and both show the lag; it was a Thursday in 2025, which does not.

For scale, counting every Luke-section day in the harvest whose content
contradicts its own label gives **13**: seven in January (the annual-ordo days,
now carried as data), three in December and one in February (this), and two in
November 2020 that look like source glitches rather than the mechanism.

Note what this means for the "303 labelled days, zero exceptions" result
earlier in this document: that finding is about the **label** being
calendar-locked, which it is. The *content* can still diverge from the label,
and these thirteen days are where it does.

### Showing both jurisdictions where the ordos disagree (2026-08-27)

Choosing GOA as the meaning of `greek` left Antiochian readers served the Greek
Archdiocese's answer on the handful of dates the two ordos differ. Rather than
pick a winner and hide the alternative, both are now shown with a parenthetical
saying whose each is:

        index    (Gospel, GOA)                     Matthew 22.1-14
                 (Gospel, Antiochian)              Matthew 19.16-26

        passage  (Gospel, Greek Archdiocese)       Matthew 22.1-14
                 (Gospel, Antiochian Archdiocese)  Matthew 19.16-26

Two forms, because the two places have different room. The reference index at
the top of the readings page is a tight column of links, so it takes the short
label; the passage heading further down -- and the API's `description` -- takes
the full one. The template is `{{ reading.short_desc|default:reading.desc }}`,
so every other reading, which has no short form, is untouched and still shows
its `desc` in both places.

This is the treatment the project already gives a saint's proper reading
standing beside the cycle's, so it needed no new display machinery -- the
existing `Reading.desc` renders in parentheses in the templates and surfaces in
the API as a reading's `description`.

`Day._collect_ordo_readings` now loads **every** jurisdiction's rows for the
date, not just the tradition's own. `gospel_pdist` still uses ours, so the
primary reading is unchanged; `Day._add_ordo_alternatives` appends the other
jurisdiction's where it differs and labels both. The label is set on the
in-memory `Reading` only -- nothing is written.

A jurisdiction is named only when there is another to contrast it with:

| situation | shown |
|---|---|
| the ordos disagree | both readings, each labelled |
| the ordos agree | one reading, no label |
| only one jurisdiction has published | one reading, no label |

That last row matters more than it looks: antiochian.org's feed does not reach
before 2018, so most of the `OrdoReading` table has a Greek row and no
counterpart. Labelling those "Greek Archdiocese" would imply a contrast that
was never observed.

This also puts the 18 Antiochian rows to work. They had been stored but unread
since the Antiochian tradition was removed.

### Cross-checked against oca.org: the ten Menaion rows are correctly `greek`

The ten Menaion readings added above were scoped `greek` because no OCA source
was available at the time to say whether Slavic keeps them too. oca.org's daily
readings turn out to be plainly fetchable at
`https://www.oca.org/readings/daily/YYYY/MM/DD` (and a whole year at
`/readings/monthly/YYYY`), so the question was settled directly.

**Nine of the ten are correctly `greek`.** On each date oca.org either gives a
different reading or none at all:

| date | Greek reads | OCA reads |
|---|---|---|
| Apr 25, Mark the Apostle | `Luke 10:16-21` | `Mark 6:7-13` |
| Apr 30, James the Apostle | `Luke 9:1-6` | `Luke 5:1-11` |
| May 7 | `Acts 26:1-5, 12-20` | `Gal 1:11-19` / `John 10:1-9`, for St Alexis Toth |
| Jul 5, Athanasius of Athos (Gospel) | `Matt 11:27-30` at Liturgy | `Luke 6:17-23` at Liturgy, `Matt 11:27-30` at Matins |
| Jul 13, Synaxis of Gabriel | `Heb 2:2-10` | daily cycle only |
| Aug 31, Placing of the Sash (both) | `Heb 9:1-7` / `Luke 10:38-42, 11:27-28` | daily cycle only |
| Sep 24 | `Luke 10:38-42, 11:27-28` | daily cycle only |
| Dec 17, Daniel and the Three Youths | `Heb 11:33-12:2` | daily cycle only |

May 7 and Sep 24 are worth noting: oca.org *does* list the commemoration --
the Appearance of the Cross, and an icon called "THE MYRTLE TREE", which is
Myrtidiotissa -- but assigns it no proper reading. Commemorating a saint and
giving them a Liturgy reading are separate things, and only the second one
matters here.

**The tenth is shared but should still stay as two rows.** Both traditions read
`Gal 5:22-26; 6:1-2` on Jul 5, so a single `common` row looks tempting. It
would be wrong: the two carry different attributions, and both are accurate.
Slavic's says *"either Saint"*, because OCA commemorates Athanasius **and** the
uncovering of the relics of Sergius of Radonezh that day and the Epistle serves
either; Greek's names Athanasius. Merging would force one tradition's
attribution on the other.

**Incidental confirmation**: on all eight dates the app's *Slavic* output
matches oca.org exactly, including the Vespers and Matins readings. That is the
first direct check of the Slavic data against its own source anywhere in this
document.
