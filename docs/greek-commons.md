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

## Implemented this pass

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

## Remaining work

The rest of the 77 (roughly 50 dates, April - October) currently have only
a single year (2026) of harvested data each — per the "single-year data is
not reliable" lesson above, **do not implement these from 2026 alone**.
Next step: harvest 3-4 more independent years for each before treating any
citation as confirmed. `ingest_antiochian.py`'s `Antiochian` class (see
this doc's sibling investigation for usage) is the tool; keep respecting
its default 2s per-request delay.

The Lent/Holy Week season (36 of the 113 full-year mismatches) needs a
different comparison method entirely (checking OT/Vespers readings against
this project's own Lenten-daily-readings logic, not Epistle/Gospel citation
matching) before it's known whether there's a real gap there at all.
