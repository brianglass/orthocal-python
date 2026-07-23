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
  `theophany + 8`, not month/day-anchored). Needs a `floats`-style fix in
  `GreekYear` (a new `FloatIndex` entry keyed to `self.theophany + 8`), not
  a plain Reading row. Not yet implemented.
- **Feb 7 area, "Saturday of the Prodigal Son"**: a genuine Triodion
  pre-Lenten floating occasion (Pascha-relative), not a fixed saint. Every
  sampled year shows different content — needs its own Triodion-floats
  investigation, out of scope here.
- **Feb 17, Theodore the Tyro**: has *two* commemorations — a floating
  "Miracle of the Kolyva" on the 1st Saturday of Great Lent (Pascha-relative,
  not handled here), and a fixed calendar date (Feb 17, his martyrdom) which
  **is** now implemented as a plain month/day row (3/3 years confirmed).
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

## Remaining work

- **Dates in the movable Paschal season** (May-June dates that fall between
  Pascha and Pentecost in most years — May 7, May 30, Jun 2, Jun 14 were
  checked and set aside): a fixed month/day comparison doesn't mean much
  here since the Paschal cycle's calendar position varies by ~5 weeks
  year to year. Not part of this project — already governed by the
  existing pdist-anchored Paschal cycle.
- **A few dates with no resolved pattern yet**: Jul 14, Jul 19, Jul 28,
  Jul 30, Aug 5, Aug 26, Sep 2 — either inconsistent across the 5 sampled
  years or showing a citation with no obvious saint attached in our `Day`
  table. Needs more investigation, possibly more years.
- **Oct 1 (Ananias the Apostle)**: confirmed citation (`Acts 9:10-19`, the
  passage about Ananias baptizing Saul) but our `Day` table has **no
  saint listed for Oct 1 at all** — likely dropped because OCA's data for
  that date is dominated by the Protection of the Theotokos (which Greek
  celebrates Oct 28 instead). This needs a `Day`-table fix, not just a
  `Reading` row — out of scope for a quick fix.
- **The Lent/Holy Week season** (36 of the original 113 full-year
  mismatches) needs a different comparison method entirely (checking
  OT/Vespers readings against this project's own Lenten-daily-readings
  logic, not Epistle/Gospel citation matching) before it's known whether
  there's a real gap there at all.
