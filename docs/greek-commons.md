# Greek Menaion "Commons" project

## Background

The [greek-weekday-drift](greek-weekday-drift.md) investigation closed out
the *mechanism* side of the Greek tradition (Sunday-of-Luke numbering,
Theophany interpolation, the ordinary continuous weekday cycle). While
investigating a user-reported discrepancy (Sept 29, 2026: antiochian.org
shows `Gal 5:22-26;6:1-2` for Ven. Cyriacos, a day this project computed as
`Eph 5:20-26`), it became clear the remaining gap isn't about mechanism at
all -- it's **missing Menaion data**: individual saints whose own "proper"
or "commons" Epistle/Gospel citation differs from whatever the ordinary
continuous cycle would otherwise show that day, exactly like the Jan 15 -
Feb 10 set already implemented, just not confined to that window.

**Full-year audit** (2026 calendar year, already fully harvested to
`data/antiochian_raw/`, zero gaps): comparing our computed Greek
Epistle/Gospel against antiochian.org for all 365 days found **113
mismatches**. Of those, 36 fall inside Cheesefare-week-through-Holy-Week
(Feb 18 - Apr 12, 2026) -- a different liturgical structure (Lenten weekday
OT readings, Presanctified Liturgy) that a simple Epistle/Gospel citation
comparison can't evaluate correctly; that's a separate future investigation.
The remaining **77** are (with a few exceptions -- see "Known non-commons
exceptions" below) individual saints' missing commons.

## Critical lesson: single-year data is not reliable

Before trusting *any* citation from a single year, cross-check against as
many other years as are already harvested. Two confirmed examples of a
saint being "promoted" to a named, primary feast with distinctive commons
in one specific year, while every other sampled year shows the usual
generic label and citation:

- **Jan 24, 2026**: antiochian.org names "XENIA OF ST. PETERSBURG,
  FOOL-FOR-CHRIST" with her own commons (`Gal 3:23-4:5` / `Mark 5:24-34`).
  Six of the other seven years on file (2019, 2021-2025) show a generic
  weekday label and `Gal 5:22-26;6:1-2` -- the citation already correctly
  implemented this session for **Xenia of Rome** (a different saint
  commemorated the same day). 2026 is the outlier, not the rule.
- **Feb 6, 2026**: antiochian.org names "THE MARTYR AND HEALER JULIAN
  (ILYAN) OF HOMS" with his own commons. Five of six other years (2019,
  2021, 2023, 2024, 2025) show "PHOTIUS THE GREAT" with `Heb 7:26-28;8:1-2`
  / `John 10:9-16` -- already correctly implemented this session. Again,
  2026 is the outlier.

**Rule going forward: never implement a citation confirmed by only one
year.** Check `data/antiochian_raw/` for every other year already harvested
for that exact month/day first; harvest more if fewer than ~4-5 years are
on file before treating a pattern as confirmed.

## Research aid: saint-category clusters (informal, not a schema)

To move faster than checking each of the 77 saints individually from
scratch, the full 2026 year was classified by saint category (via keyword
matching on antiochian.org's `feastDayTitle` -- Apostle, Prophet, Hierarch,
Hieromartyr, Martyr split by gender, Virgin-Martyr, Unmercenary, Venerable,
Equal-to-the-Apostles, Fool-for-Christ), then grouped to see how consistent
the Epistle/Gospel citation is *within* a category. This is a strong prior
for "what to expect," not a computed rule -- see the schema decision below
for why.

Clean, high-confidence clusters found so far:

| Category | Citations (Epistle / Gospel) | Confidence |
|---|---|---|
| Unmercenary physicians | `1 Cor 12:27-31;13:1-8` / `Matt 10:1,5-8` | 2/2 clean, and independently reconfirmed at 7/7 years for Cosmas & Damian specifically |
| Female Greatmartyr (group A: Marina, Catherine, Barbara, +1) | `Gal 3:23-29;4:1-5` / `Mark 5:24-34` | 4/6, reconfirmed at 6-8/8 years each for Catherine and Barbara specifically |
| Female Greatmartyr (group B: Euphemia, both her occurrences) | `2 Cor 6:1-10` / `Luke 7:36-50` | 2/2, but contradicts group A -- **the "female greatmartyr" category needs at least one more split that hasn't been identified yet.** This is exactly the ambiguity the physical Book of the Epistles' "Common Services" section should resolve. |

Noisier clusters, not yet resolved into sub-rules (Apostle, Hierarch, Martyr
(male) all show a plurality citation but with real variation, likely needing
finer subdivision -- e.g. "Apostle who wrote a Gospel" vs. not, or further
splits by the specific type of martyrdom):

- **Apostle** (14 sampled days): `1 Cor 4:9-16` is the plurality Epistle
  (5/14), Gospel is scattered.
- **Hierarch** (7 days): `Heb 7:26-28;8:1-2` plurality (3/7).
- **Martyr, male** (3 days): no plurality found yet, too small a sample.

**When you have access to it**: cross-check this table (and the individual
per-saint citations below) against the physical *Book of the Epistles*
(Antiochian Village Press) — its "Common Services" appendix should give the
authoritative category list and boundaries, resolving ambiguities like the
Euphemia split above without needing more antiochian.org sampling.

## Schema decision: direct per-saint linking, not a computed category system

Considered building the category clusters above into a live, computed
lookup (assign a category to each `Commemoration`/saint, derive the Reading
at request time). **Rejected in favor of keeping the existing pattern**:
one `Reading` row directly linking a specific saint's fixed date to a
specific `Pericope`, exactly like the ~5,500 Slavic rows and the Jan15-Feb10
Greek set already use.

Reasoning: Euphemia is a clean counterexample proving category alone is
insufficient -- a computed "female greatmartyr" rule would get her wrong
both times she's commemorated. The physical Book of the Epistles itself
has two sections (a fixed-date section linking specific saints directly to
specific pericopes, and a separate commons-by-category appendix used only
as a fallback), which is exactly this same precedent. Direct linking also
means a future correction (e.g. from the physical-book cross-check) is a
one-row fix, not a rule change with wide blast radius.

The category clusters remain useful purely as a **research aid** — a fast
way to guess the likely citation and sanity-check it — not as the
implementation mechanism.

## Known non-commons exceptions in the 77

A few of the 77 mismatches are not missing saint commons and need different
handling:

- **Jan 14, Leavetaking of Theophany** (when it falls on an ordinary
  weekday): confirmed fixed at `Acts 2:38-43` / `Luke 4:1-15` (5/8 years;
  the other 3 show different content because Leavetaking landed on a
  different calendar date those years — it's genuinely floating,
  `theophany + 8`, not month/day-anchored). **Now implemented** — see
  "pass 6" below.
- **Feb 7 area, "Saturday of the Prodigal Son"**: a genuine Triodion
  pre-Lenten floating occasion (Pascha-relative), not a fixed saint.
  **Now implemented** — see "pass 6" below.
- **Feb 17, Theodore the Tyro**: has *two* commemorations — a floating
  "Miracle of the Kolyva" on the 1st Saturday of Great Lent (Pascha-relative;
  checked in "pass 6" below and found to be **already correct** — no gap),
  and a fixed calendar date (Feb 17, his martyrdom) which was already
  implemented as a plain month/day row (3/3 years confirmed, "pass 1").
- **Dec 17, Dec 30-31**: no consistent pattern across any sampled years for
  these specific calendar dates — these fall inside the already-documented,
  permanently-accepted "unsolved recovery mechanism" window from
  `greek-weekday-drift.md`, not a new gap.

## Implemented, pass 1

13 dates added as `greek`-tagged `Reading` rows (24 Epistle+Gospel pairs +
1 Epistle-only), each confirmed against 3-8 independent antiochian.org
years before implementing (see `data/antiochian_raw/` for the raw
citations by date). Only one new `Pericope` was needed (`Hebrews 8.1-6`,
for Paul the Confessor) — every other citation already existed under an
equivalent verse-range notation, reused directly:

| Date | Saint | Epistle | Gospel |
|---|---|---|---|
| Feb 3 | Afterfeast of the Presentation | Heb 9.11-14 | Luke 2.25-38 |
| Feb 11 | Blaise the Hieromartyr | Heb 4.14-5.6 | Matt 10.1,5-8 |
| Feb 17 | Theodore the Tyro (fixed date) | 2 Tim 2.1-10 | Luke 20.46-21.4 |
| Sep 29 | Cyriacos the Hermit | Gal 5.22-6.2 | *(gospel already correct)* |
| Nov 1 | Cosmas & Damian | 1 Cor 12.27-13.8 | Matt 10.1,5-8 |
| Nov 6 | Paul the Confessor | Heb 8.1-6 | Luke 12.8-12 |
| Nov 9 | Nektarius the Wonderworker | Eph 5.8-19 | Matt 4.25-5.12 |
| Nov 12 | John the Merciful | 2 Cor 9.6-11 | Matt 5.14-19 |
| Nov 16 | Matthew the Apostle | Rom 10.11-11.2 | Matt 9.9-13 |
| Nov 25 | Catherine the Greatmartyr | Gal 3.23-4.5 | Mark 5.24-34 |
| Dec 4 | Barbara the Greatmartyr | Gal 3.23-4.5 | Mark 5.24-34 |
| Dec 12 | Spyridon the Wonderworker | Eph 5.8-19 | John 10.9-16 |
| Dec 15 | Eleutherios the Hieromartyr | 2 Tim 1.8-18 | Mark 2.23-3.5 |

Follow-up in the same pass: 4 more Epistle-only dates that already had 6-7
years of harvested data but were missed the first time through (Nov 10
Apostles of the 70, Nov 11 Menas/Victor/Vincent, Nov 17 Gregory the
Wonderworker, Nov 24 Hieromartyrs Clement & Peter).

## Implemented, pass 2 (harvested 4 more years: 2019, 2021, 2023, 2025)

Harvested `2019/2021/2023/2025` for the ~50 remaining Apr-Oct dates (208
requests total, respecting the 2s delay), bringing each to 4-5 independent
years. **37 more dates** confirmed and added (66 Epistle/Gospel rows, 5 new
Pericopes: `Luke 6.17-19,9.1-2,10.16-21`, `Mark 3.13-21`,
`Titus 1.1-5,2.15,3.1-2,12-15`, `Galatians 4.22-27`, `Colossians 1.24-2.1`).

One structural correction found during this pass: for several dates, the
*Gospel* turned out to be the fixed commons and the *Epistle* the one that
varies year to year — the opposite of what the 2026-only data suggested.
Always check both independently rather than assuming symmetry:

| Date | Saint | Epistle | Gospel |
|---|---|---|---|
| May 2 | Removal of Relics of Athanasius | Heb 13.7-16 | Matt 5.14-19 |
| Jun 4 | Metrophanes | Heb 7.26-8.2 | John 10.1-9 |
| Jun 8 | Removal of Relics of Theodore | Eph 2.4-10 | Matt 10.16-22 |
| Jun 30 | Synaxis of the Twelve Apostles | 1 Cor 4.9-16 | Matt 9.36-10.8 |
| Jul 1 | Cosmas & Damian (2nd feast) | 1 Cor 12.27-13.8 | Matt 10.1,5-8 |
| Jul 2 | Deposition of the Robe | Heb 9.1-7 | Luke 1.39-49,56 |
| Jul 7 | Kyriake | Gal 3.23-4.5 | Mark 5.24-34 |
| Jul 8 | Procopius | 1 Tim 4.9-15 | Luke 6.17-19,9.1-2,10.16-21 |
| Jul 11 | Euphemia (1st feast) | 2 Cor 6.1-10 | Luke 7.36-50 |
| Jul 13 | Synaxis of Archangel Gabriel | *(varies)* | Luke 10.16-21 |
| Jul 15 | Cyricus & Julitta | 1 Cor 13.11-14.5 | Matt 17.24-18.4 |
| Jul 17 | Marina | Gal 3.23-4.5 | Mark 5.24-34 |
| Jul 22 | Mary Magdalene | 1 Cor 9.2-12 | Luke 8.1-3 |
| Jul 26 | Paraskeve | Gal 3.23-4.5 | Mark 5.24-34 |
| Aug 1 | Holy Maccabee Children | Heb 11.33-12.2 | Matt 10.16-22 |
| Aug 7 | Afterfeast of Transfiguration | *(varies)* | Mark 9.2-9 |
| Aug 21 | Thaddaeus | *(varies)* | Mark 3.13-21 |
| Aug 25 | Bartholomew relics | Titus 1.1-5,2.15,3.1-2,12-15 | Matt 5.14-19 |
| Sep 5 | Zacharias | *(varies)* | Matt 23.29-39 |
| Sep 9 | Joachim & Anna | Gal 4.22-27 | Luke 8.16-21 |
| Sep 10 | Menodora, Metrodora, Nymphodora | *(varies)* | John 3.16-21 |
| Sep 11 | Theodora of Alexandria | *(varies)* | John 12.19-36 |
| Sep 15 | Nikitas | Col 1.24-2.1 | Matt 10.16-22 |
| Sep 16 | Euphemia (2nd feast) | 2 Cor 6.1-10 | Luke 7.36-50 |
| Sep 24 | Myrtidiotissa Miracle | 2 Tim 3.10-15 | *(varies)* |
| Sep 30 | Gregory the Illuminator | 1 Cor 16.13-24 | Matt 24.42-47 |
| Oct 2 | Cyprian | 1 Tim 1.12-17 | *(varies)* |
| Oct 3 | Dionysius the Areopagite | Acts 17.16-34 | *(varies)* |
| Oct 6 | Thomas the Apostle | 1 Cor 4.9-16 | John 20.19-31 |
| Oct 9 | James, Son of Alphaeus | 1 Cor 4.9-16 | Matt 9.36-10.8 |
| Oct 16 | Longinus the Centurion | *(varies)* | Matt 27.33-54 |
| Oct 17 | Prophet Hosea | Rom 9.18-33 | *(varies)* |
| Oct 19 | Prophet Joel | Acts 2.14-21 | *(varies)* |
| Oct 20 | Artemius | 2 Tim 2.1-10 | *(varies)* |
| Oct 21 | Hilarion the Great | 2 Cor 9.6-11 | *(varies)* |
| Oct 28 | Protection of the Theotokos | Heb 9.1-7 | Luke 10.38-42,11.27-28 |
| Oct 31 | Apostles Stachys, Amplias, et al | Rom 16.1-16 | *(varies)* |

(Hosea/Joel/Artemius/Hilarion/Cyprian/Dionysius/Stachys-et-al are not named
in antiochian.org's own `feastDayTitle` most years — always shown as a
generic "Nth week" label — but our own `Day` table already lists them as
minor commemorations that day, and the citation content directly confirms
the match, e.g. Acts 2:14-21 is Peter's Pentecost speech quoting Joel
2:28-32.)

## Implemented, pass 3 (stragglers)

Resolved 4 more of the previously-unresolved dates by recognizing they're
all "Apostles of the Seventy" whose names are directly confirmed by their
citation's content (e.g. Silas & Silvanus are literally named in Acts
15:40, their own Epistle):

| Date | Saint | Epistle |
|---|---|---|
| Jul 14 | Apostle Aquila of the 70 | Rom 16.1-16 |
| Jul 28 | Apostles Prochorus, Nicanor, Timon, Parmenas | Acts 6.1-7 |
| Jul 30 | Apostles Silas & Silvanus | Acts 15.35-41 |

**Oct 1, Ananias of the Seventy**: fixed properly this time — added
`Acts 9.10-19` (new Pericope) as a `greek` Epistle row, *and* added Ananias
to the `Day` table's `saint` field for Oct 1 (previously empty), since he's
a universal Orthodox commemoration missing from our OCA-derived data
entirely, not a Greek-specific one. Both traditions now list him.

**Bug found and fixed while checking this**: Greek was incorrectly showing
Slavic's Oct 1 Protection-of-the-Theotokos Epistle/Gospel (`Heb 9.1-7` /
`Luke 10.38-42,11.27-28`), since those rows were tagged `common` and Greek
falls back to `common` when no override exists — but Greek celebrates
Protection on Oct 28 instead (already correctly implemented), and doesn't
observe it on Oct 1 at all. Retagged both rows `slavic`-only.

**Deeper issue found, not fixed**: `Day.feast_name`/`feast_level` are not
tradition-tagged at all (unlike `Reading`), so Greek's `Day(2026,10,1)`
still reports `feasts == ['Protection (Pokrov)...']` and `feast_level == 6`
even after the Reading fix above — the site's overall feast/title display
for Greek on Oct 1 is still wrong, just the actual Epistle/Gospel content
isn't anymore. Fixing this properly means adding a tradition axis to the
`Day` model itself, contradicting the original tradition-axis plan's
assumption that "no confirmed differences exist in the `Day` model." Given
this is exactly the kind of case, there may be other Greek/Slavic
fixed-feast-date mismatches lurking the same way. Not investigated further
this pass — flagging for a future, dedicated look.

## Implemented, pass 4 (final stragglers)

All 4 remaining dates from pass 3 resolved:

- **Aug 5, Martyr Eusignius**: `1 Pet 1.1-25,2.1-10` — 5/5 clean, just
  didn't have an obvious thematic fit so it was set aside for a second
  look; the consistency alone was already sufficient evidence.
- **Sep 2, Anthony & Theodosius of Kiev Caves**: `Rom 8.28-39` — 4/5 clean
  (2019 differs), same story.
- **Aug 26, Martyrs Adrian & Natalia**: harvested 4 more years (2018, 2020,
  2022, 2024) to break the 2/3 tie found in pass 3. Result: `Heb 10.32-38`
  in every year from 2022 onward (5/8 total, with a clear cutover point) —
  `Heb 6.9-12` (2019-2021) looks like an older citation antiochian.org
  itself corrected around 2022. Implemented `Heb 10.32-38`.
- **Jul 19, "Sunday of the Fathers of the 4th Ecumenical Council"**: turned
  out *not* to be a separate floating occasion at all — it's the exact
  same Sunday our existing `fathers_six` float already computes correctly
  (nearest Sunday to July 16), just with the wrong citation tagged
  `common`. Harvested all 8 available years landing on this Sunday
  (2018-2024, 2026) — every single one shows `Titus 3:8-15` / `Matt
  5:14-19` for Greek, vs. our `common` table's `Heb 13:7-16` / `John
  17:1-13` (which stays correct for Slavic). Added as a `greek` override
  at `FloatIndex.FathersSix`.

**Wiring lesson**: float-pdist overrides (like `FathersSix` above) must
reuse the *exact same* `ordering` value as the `common` row they're meant
to replace, not the `821`/`921` convention used for the plain month/day
saint-day rows elsewhere in this doc — `_prefer_tradition`'s slot key is
`(pdist, month, day, source, ordering, desc)`, so a mismatched ordering
creates a duplicate instead of an override. Caught by checking the actual
rendered output before committing, not just trusting the write succeeded.

With this, all 77 dates from the original full-year audit are now
resolved except the Lent/Holy Week season (see below).

## Implemented, pass 5 (Lent/Holy Week)

The 36 "mismatches" from the original full-year audit were almost entirely
a false-positive artifact of the audit script itself: it assumed
antiochian.org's `reading1`/`reading2` fields are always Epistle/Gospel,
but during Lent they're the day's OT Vespers readings (Isaiah/Genesis/
Proverbs), and during Holy Week they're a mix of Passion Gospels and Hours
readings — comparing those against our `source='Epistle'`/`'Gospel'` rows
was comparing unrelated content. Rewrote the audit to pull *all* of a
`Day`'s readings regardless of source and match by (book, verse), which
cut the 36 down to **4 genuine mismatches** across the entire 54-day
window (Feb 18 - Apr 12, 2026) — the ordinary weekday/Vespers OT cycle
during Lent is already fully correct and shared between traditions
(confirmed directly, e.g. Clean Monday's `Isaiah 1.1-20`/`Genesis 1.1-13`/
`Proverbs 1.1-20` already matches exactly for both).

Of the 4:

- **Cheesefare Thursday**: `Luke 23.1-31,33,44-56` (Greek) vs. our
  existing `Luke 23.2-34,44-56` (Slavic) — confirmed 3/3 independent years
  (2018, 2023, 2026). A real, if minor, verse-selection difference, not
  just a boundary variant. Added as a `greek` Gospel override (new
  Pericope).
- **Holy Friday**: `1 Cor 5:6-8` (Greek) vs. our existing Vespers Epistle
  `1 Cor 1.18-2.2` (Slavic) — confirmed 2/2 years (2021, 2026). Added as a
  `greek` override on the `Vespers`-desc Epistle slot (new Pericope).
- **Holy Thursday's compound Gospel reading**: our version and
  antiochian's differ by a few verses within an already-massive 6-part
  compound citation (`Matt 26:2-20;...` vs `Matt 26:1-20;...`, etc.) —
  likely citation-notation variance given how close it already is, not
  investigated further.
- **5th Saturday of Lent ("Akathist Saturday")**: antiochian shows
  `Luke 1:39-49,56` (the Magnificat, a natural fit for the Akathist to the
  Theotokos); we currently show a plain `Mark 8.27-31` with no thematic
  connection at all, from an existing but apparently-unrelated
  `'Theotokos'`-desc floating override. Only one year of data (2026) — not
  implemented yet per the "single-year data is not reliable" lesson.
  Needs either more years (this is Pascha-relative, so must be matched by
  occasion/title across years, not calendar date) or the physical book.

## Implemented, pass 6 (floating occasions)

The three floating occasions flagged throughout this doc, resolved:

- **Leavetaking of Theophany, ordinary weekday** (`theophany + 8`, when not
  Saturday/Sunday — those are already covered by the existing
  `SatAfterTheophany`/`SunAfterTheophany` floats): confirmed
  `Acts 2:38-43` / `Luke 4:1-15` for Greek across 5 independent years
  (2019, 2021, 2022, 2025, 2026 cycles); Slavic reads the ordinary
  continuous cycle here with no override, already correct. Added a new
  `FloatIndex.LeavetakingTheophanyWeekday`, computed unconditionally in the
  shared `ByzantineYear.floats` (harmless for Slavic since no rows exist at
  that pdist for that tradition — only `GreekYear` needs the actual
  Reading rows). Tested in `test_liturgics.py`
  (`test_leavetaking_theophany_weekday_float`,
  `test_leavetaking_theophany_weekday_reading`).
- **Theodore the Tyro's Kolyva miracle, 1st Saturday of Great Lent**:
  checked against real data (`2 Tim 2:1-10` / `Mark 2:23-28,3:1-5`) and
  found this **already matches our existing shared `common` table exactly**
  — no gap, nothing to implement. (This pdist already carries an
  unrelated-looking `desc='1st Saturday of Lent'` tag that turned out to be
  exactly the right content all along.)
- **Prodigal Son Saturday** (a Triodion pre-Lenten floating Saturday):
  Gospel already matched (`Luke 20:46-47;21:1-4`); Epistle needed fixing.
  Harvested enough years to get 6 usable samples (one excluded — displaced
  by Blaise's fixed Feb 11 that particular year) — `1 Timothy 6:11-16` wins
  4/6, `Philemon 1:1-25` appears in the other 2 (2019, 2024 cycles, likely
  a stale/superseded citation, same pattern as the Aug 26 Adrian & Natalia
  case in "pass 4"). Added `1 Tim 6:11-16` as a `greek` Epistle override.

**Wiring note**: like the `FathersSix` override in "pass 4", this required
matching the existing `common` row's exact `ordering` value, not the
`821`/`921` convention — checked and got right this time before committing.

## Implemented, pass 7 (Day.tradition axis)

Added a `tradition` field to the `Day` model, mirroring `Reading`'s
pattern exactly: `choices=('common', 'slavic', 'greek')`, default
`'common'`, migration retags all 832 existing rows `'common'`. Added
`_prefer_tradition_days` (like `_prefer_tradition` but slotted on
`(pdist, month, day)` since `Day` has no source/ordering/desc) and wired
it into `Day._collect_commemorations`'s query, exactly like `Reading`
already does.

**Scope-finding pass**: compared every `Day` row with a non-empty
`feast_name` (155 rows) against the full 2026 antiochian.org harvest —
not just `feastDayTitle` (too noisy: many false positives from a saint
simply not being *primary* that specific year, e.g. Sunday collisions),
but the full `feastDayDescription` text, to properly distinguish "Greek
doesn't observe this at all" from "Greek observes it, just didn't
headline it in 2026." That check confirmed your prediction — found 7
genuine cases (not just the 1 that started this):

| Date | Feast (Slavic-only) | Confirmed via |
|---|---|---|
| Oct 1 | Protection of the Theotokos | The original bug (Greek: Oct 28 instead) |
| Feb 5 | Repose of St. Theodosius of Chernigov | Absent from full description |
| May 7 | St. Alexis Toth | Absent from full description |
| Jul 5 | Uncovering of Relics, Sergius of Radonezh & Athanasius of Athos | Absent from full description |
| Aug 9 | Ven. Herman of Alaska (this date only — his Dec 13 commemoration *is* shared) | Absent from full description |
| Oct 31 | Hieromartyr John Kochurov | Absent from full description |
| Nov 23 | Right-Believing Great Prince Alexander Nevsky | Absent from full description |

All 7: retagged the existing row `'slavic'`, added a `'greek'` counterpart
with `feast_name=''`/`feast_level=0` (so Greek's fasting-exception logic,
which keys off `feast_level`, no longer gets an unearned relief from a
feast Greek doesn't observe) and an empty `saint` field (except Oct 1,
which keeps Ananias — see below). `fast`/`fast_exception` copied as-is
from the Slavic row, since those reflect the calendar season, not the
specific saint.

**Note on Oct 1 specifically**: the `saint` field already had "Holy
Apostle Ananias of the Seventy" added directly to the shared row earlier
this session, before this `tradition` axis existed. Kept him on *both* the
new `slavic` and `greek` rows — he's a genuine shared commemoration; only
`feast_name` (Protection) needed the split.

**Found but not fixed — a second, smaller leak**: `_add_supplemental_commemorations`
(the separate `Commemoration`/abbamoses.com stories table) is *also* not
tradition-tagged, and it fills gaps opportunistically — once Greek's
`feast_name` for Oct 1 went empty, `_add_supplemental_commemorations`
started pulling in the "Protection" story from that table as a
supplemental saint entry, since it's no longer redundant with an
existing title. Same issue for Alexis Toth on May 7. Not fixed this pass;
same category of problem as `Day.feast_name`, on a different table.

## Remaining work

- **Dates in the movable Paschal season** (May-June dates that fall between
  Pascha and Pentecost in most years — May 7, May 30, Jun 2, Jun 14 were
  checked and set aside): a fixed month/day comparison doesn't mean much
  here since the Paschal cycle's calendar position varies by ~5 weeks
  year to year. Not part of this project — already governed by the
  existing pdist-anchored Paschal cycle.
- **The ~90 other `feast_name` dates never checked this pass**: this
  scope-finding pass only fully verified 7 of the ~90 non-Pascha-relative
  `feast_name` dates found. The rest are unclassified — some are
  certainly false positives (same feast, different name across
  traditions, e.g. "Holy Apostle Jude" / "Thaddeus" on Jun 19, or "Holy
  Apostle John the Theologian" / "Synaxis of the Holy Manna" on May 8 —
  both look like naming variants for the same occasion, not real gaps),
  but a full pass needs the same "check the full description, not just
  the title" method used for the 7 above before trusting any conclusion.
- **`Commemoration`/abbamoses.com tradition-tagging**: see "pass 7" above
  — same category of gap as `Day.feast_name`, not yet fixed.
- **5th Saturday of Lent (Akathist Saturday)**: still needs more years of
  data (Pascha-relative, matched by occasion not calendar date).
- **Holy Thursday's compound Gospel reading**: minor verse-boundary
  variance, likely not worth chasing further.
