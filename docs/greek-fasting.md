# Greek vs. Slavic fasting rules

## Background

The app's fasting-rule code (`Day._apply_fasting_adjustments`) was written to
follow OCA's published outline
(https://www.oca.org/liturgics/outlines/fasting-fast-free-seasons-of-the-church).
Brian asked whether Greek/Antiochian practice diverges, since he knew it
varied "a bit." Investigated each of the four fasting seasons in turn against
OCA (Slavic baseline) and multiple Antiochian Archdiocese sources.

**Scope note**: differences in food-category interpretation (e.g. whether
"oil" means olive oil specifically or all vegetable oils, or how
permissively shellfish/cephalopods are treated) are informal/customary, not
something this app's data model tracks at all (it only models aggregate
levels like "Wine and Oil are Allowed," not ingredient-level detail) --
explicitly out of scope per Brian.

**Primary source**: Brian has a full Antiochian Archdiocese typikon at
`~/Documents/Orthodox Studies/54-typikon-full.pdf` (583 pages) -- genuinely
authoritative (footnote 344 explicitly cites "The Clergy Guide of the
Self-Ruled Antiochian Orthodox Christian Archdiocese of North America").
Converted to text via `pdftotext -layout` for grepping when the empirical
antiochian.org method below doesn't fully resolve something. It's primarily
a service-order/rubrics reference (hymns, readings, structure), not a
dedicated fasting-rules chapter, so don't expect a clean day-by-day table --
search for specific terms (a saint's name, "Great Canon," "Wednesdays and
Fridays," etc.) rather than a single section.

## Findings, by fast

### Nativity Fast (Nov 15 - Dec 24) -- genuine, confirmed structural difference

Confirmed via two independent, detailed Antiochian parish sources that agree
with each other precisely (stgeorgeaz.org, sttimothy.us), both distinct from
the OCA-modeled pattern our code already implemented:

**Phase 1 (Nov 15 - Dec 12)**
- Slavic (OCA, pre-existing code): Mon/Wed/Fri strict; Tue/Thu wine+oil;
  Sat/Sun fish+wine+oil.
- Greek (Antiochian): Wed/Fri strict; every other day (Sun/Mon/Tue/Thu/Sat)
  gets fish+wine+oil -- a simpler two-way split, Monday grouped with the
  lenient days rather than with Wed/Fri.

**Phase 2, the "stricter period"**
- Slavic: starts ~5 days out (`nativity-6` to `nativity-1`), only removes
  fish -- Tue/Thu keep their wine+oil allowance throughout.
- Greek: starts **Dec 13** (`nativity-12`), a full week earlier, and is
  stricter -- wine+oil is restricted to Sat/Sun only, so Mon/Tue/Thu drop to
  full strictness (same as Wed/Fri), not just losing fish.

One general Antiochian summary found early in the research contradicted this
(grouping Monday with Wed/Fri, same as Slavic) -- judged to be an imprecise
generalization, since it's contradicted by two independent sources that are
specific to the Nativity Fast and agree with each other exactly.

### Apostles' Fast -- no difference found

A dedicated Antiochian source states explicitly: Mon/Wed/Fri strict, Tue/Thu
wine+oil, Sat/Sun fish -- identical to the Slavic/OCA pattern our code
already implements. Notable: it's specifically the Nativity Fast's first
phase that's unusually lenient in Greek practice, not a general "Greek fasts
are more lenient" pattern -- the Apostles' Fast (sharing the exact same
weekly structure) shows no such leniency in either tradition.

### Dormition Fast (Aug 1-14) -- no difference found

Every source checked describes the same structure: weekdays strict, weekends
wine+oil, Transfiguration (Aug 6) gets fish. Confirmed our existing data
already grants the Transfiguration exception correctly and identically for
both traditions (`Day.fast_exception=4` on that date, tagged `common`).

### Great Lent / Holy Week -- ordinary weekdays identical, three named exceptions differ

Repeated web searches across several Antiochian sources kept returning the
same weekly structure already in our code (weekdays strict/xerophagy,
weekends wine+oil, fish on Annunciation and Palm Sunday) plus the same list
of named weekday feasts OCA's page grants a wine-and-oil exception to (Feb 24,
Mar 9, Mar 24, Mar 26, the fifth week's Wed/Thu Great Canon vigil, Friday's
Akathist vigil). **This turned out to be a methodology trap**: one of the
"Greek Orthodox Church" sources that matched OCA's full list verbatim was
explicitly attributed on its own page to "These Truths We Hold" -- a
St. Tikhon's Seminary (OCA) publication being reused as boilerplate by a
GOARCH-affiliated parish, not an independent Antiochian source at all. Brian
caught this and asked for an empirical check instead of more web research.

**Empirical method**: `data/antiochian_raw/*.json` (harvested via
`ingest_antiochian.py`'s `Antiochian` client) has a `fastDesignation` field --
Antiochian's own official per-day fasting designation, not a paraphrase.
`parse_fast_designation`/`DietaryAllowance` in that script already give it a
clean, monotonic vocabulary. Checked every OCA-rule-#3/#4 date across 4-5
independently-harvested years each (using `SlavicYear(year).pascha` to
compute the real calendar date of pdist-anchored occasions like "5th
Wednesday of Lent," since those move every year):

- **Confirmed genuinely stricter in Antiochian practice** (fully strict on
  an ordinary Lenten weekday in every valid-Lent-year sample):
  - Mar 24 (Forefeast of the Annunciation) -- 4/4 years (2020, 2022, 2025, 2026).
  - Fifth week Wednesday (OCA's "Great Canon" exception) -- 4/4 years (2020, 2022, 2024, 2025).
  - Fifth week Friday (OCA's "Akathist Hymn" exception) -- 5/5 years (2020, 2022, 2024, 2025, 2026).
- **Confirmed shared/universal** (wine+oil granted, matching OCA): Mar 9
  (40 Martyrs of Sebaste) -- 2/2 valid years; Apr 25 (Apostle Mark) -- 1/1
  valid year (Pascha timing meant most sampled years fell outside Lent
  entirely for this one, so treat as suggestive rather than fully confirmed).
- **Genuinely mixed, no rule found**: fifth week Thursday itself (the actual
  Great Canon day) -- strict in 2020/2024, wine+oil in 2022/2025, no
  discernible pattern; Mar 26 (Synaxis of the Archangel Gabriel) -- wine+oil
  in 3/4 years but the title didn't actually credit Gabriel in two of those,
  strict in the one year (2026) the title did name him specifically. Left
  unresolved -- not confident enough either way to act on.
- **Never appears in Antiochian's own titles at all**, across every
  valid-Lent-year sample, consistent with being Slavic/American-specific
  (though Pascha timing meant none of the sampled years put these dates
  inside actual Lent, so this is suggestive rather than a clean
  strict-vs-exception test): Feb 27 (Raphael of Brooklyn -- notably, despite
  being the founding figure of Antiochian Orthodoxy in America), Mar 31
  (Innocent of Alaska), Apr 7 (Tikhon of Moscow).

The three confirmed items were implemented as a genuine `Day`-row data split
(not a code change) -- see Implementation below.

**Follow-up corroboration from the typikon PDF** (see Background above):

- Its official "Wednesdays and Fridays when exceptions to the fast are
  permitted" chapter (citing the Antiochian Archdiocese's own Clergy Guide)
  grants the *fish* exception only to Annunciation, Palm Sunday, and
  Transfiguration -- nothing for the Forefeast of the Annunciation, Synaxis
  of Gabriel, or any minor saint. A stricter tier than wine+oil, but
  consistent with (not contradicting) the empirical Mar 24 finding.
- Zero mentions of "Innocent" or "Tikhon" across all 583 pages -- about as
  strong a confirmation as available that they're absent from Greek
  practice entirely.
- No mention anywhere of the Great Canon or Akathist granting any food
  exception, despite extensive discussion of those services' own structure --
  further corroborates the empirical "fully strict" fifth-week finding.
- A footnote confirms Feb 24 and Mar 9 both get their own liturgical
  treatment (specifically which day gets the Presanctified Liturgy's
  stichera) when they fall in Lent -- supports treating Mar 9 as
  confirmed-shared and Feb 24 as likely following suit, though this is
  about a different question (service structure, not wine+oil) so isn't a
  direct proof.
- **New, unrelated finding**: an editor's note states the Antiochian
  Archdiocese keeps St. Raphael of Brooklyn -- their own founding bishop in
  America -- on the first Saturday of November, not Feb 27 (his OCA/Slavic
  date). A genuine differing-commemoration-date case, same shape as
  Catherine of Alexandria/Theophan the Recluse in `docs/greek-commons.md`
  pass 12. Fixed here rather than there since it surfaced during this
  investigation -- see Implementation below.

## Implementation

`calendarium/liturgics/day.py`'s `Day` class was split, mirroring the
`ByzantineYear`/`SlavicYear`/`GreekYear` pattern in `year.py`:

- `Day` is now the shared base (everything except fasting adjustments) --
  `_apply_fasting_adjustments` is an abstract stub there.
- `Day.__new__` dispatches on the `tradition` argument (via a `_DAY_CLASSES`
  map defined after both subclasses) to actually construct a `SlavicDay` or
  `GreekDay` instance. Every existing call site (`liturgics.Day(...)`, used
  throughout views/api/feeds/ical/skills) is unchanged -- they all already
  pass `tradition=`, and now transparently get back the right subclass.
- `SlavicDay._apply_fasting_adjustments` is the original method, moved
  verbatim -- no behavior change.
- `GreekDay._apply_fasting_adjustments` is a full copy with the Lenten/
  Dormition/Apostles-fast cases unchanged (confirmed identical above) and a
  new Nativity Fast case implementing the two-phase pattern described above.

**Bug caught during implementation, fixed before landing**: the first draft
of `GreekDay`'s stricter-period logic capped any `fast_exception > 1` down to
1 (wine+oil), copying the style of the existing Wed/Fri cap. But
`FastExceptions` isn't a simple leniency ordering -- indices 7-10 (`"Meat
Fast"`, `"Strict Fast (Wine and Oil)"`, `"Strict Fast"`, `"No overrides"`)
are *stricter* than index 1 despite the higher number. This caused Dec 24,
2026 (a Thursday with a deliberately strict `fast_exception=9` baseline) to
get incorrectly loosened to wine+oil under the new Greek logic. Fixed by
bounding the cap to `1 < fast_exception <= 6` (the actual lenient range: fish/
wine/oil/caviar variants) rather than `fast_exception > 1`. Confirmed fixed
and now identical to Slavic's output across 2023 (Sunday), 2026 (Thursday),
and 2027 (Friday) Dec 24s -- three different weekday branches of the logic.
Tested in `TestGreekFasting.test_nativity_eve_strict_baseline_not_weakened_by_greek_stricter_period`.

**Great Lent's three confirmed exceptions** (Mar 24, and the pdist-anchored
fifth-week Wednesday/Friday, pdist -18 and -16) were implemented as a data
split rather than a code change, since `SlavicDay`/`GreekDay`'s Lenten-fast
case is identical for both traditions -- the divergence lives entirely in
the `Day.fast_exception` baseline. Each date's single `common` row (which
carried the wine+oil `fast_exception` OCA's rule grants) was retagged
`slavic` and deleted the `common` copy, then a new `greek` row was added with
`fast_exception=0` (matching how ordinary strict Lenten weekdays are already
represented elsewhere in this data, e.g. Monday/Tuesday of the fifth week).
Tested in
`TestGreekFasting.test_lenten_wine_oil_exceptions_greek_stricter_than_slavic`.

**St. Raphael of Brooklyn** (Feb 27 Slavic vs. first Saturday of November
Greek) needed a new mechanism, since "first Saturday of a fixed calendar
month" isn't Pascha-relative like the existing floating occasions
(Demetrius Saturday, Synaxis of the Unmercenaries, etc. -- those are all
"nearest Saturday/Sunday to a fixed date"). Added `ByzantineYear.
raphael_brooklyn` alongside those (same file, same pattern: `date_to_pdist`
+ roll forward to the target weekday) and a new `FloatIndex.RaphaelBrooklyn
= 1039`, included unconditionally in the shared `floats` dict -- harmless
for Slavic since no Day rows exist at that pdist for that tradition,
matching the `LeavetakingTheophanyWeekday` precedent. Feb 27's `common` row
retagged `slavic`; a new `greek` row added at `pdist=FloatIndex.
RaphaelBrooklyn, month=0, day=0`. Tested in
`TestYear.test_raphael_brooklyn_first_saturday_of_november` (pdist
arithmetic, three different Nov-1 weekdays) and
`TestTraditionOverlay.test_raphael_brooklyn_differing_commemoration_date`
(end-to-end Day).

## Remaining / not investigated

- **Feb 24** (First/Second Finding of the Head of John the Baptist): never
  landed inside actual Great Lent in any of the 4 years sampled (Pascha
  timing kept it in the pre-Lenten Cheesefare/Meatfare season every time) --
  no valid empirical test yet, positive or negative. Our own `common`
  baseline also shows no override here (`fast_exception=0`), which may be a
  pre-existing Slavic-side gap independent of the Greek question -- not
  picked up here.
- **Fifth week Thursday** (the actual Great Canon day) and **Mar 26**
  (Synaxis of the Archangel Gabriel): genuinely mixed empirical results (see
  above), not confident enough to act on either way.
- **Feb 27 / Mar 31 / Apr 7** (Raphael of Brooklyn / Innocent of Alaska /
  Tikhon of Moscow): never named in Antiochian's titles across the sampled
  years, but never landed on a clean ordinary-weekday-in-Lent test either --
  suggestive of being Slavic/American-specific, not confirmed by a direct
  strict-vs-exception comparison.
- Contrary to the original expectation that this whole project might be
  pure code logic: the Nativity Fast difference was code-only, but Great
  Lent's three confirmed exceptions needed an actual `Day`-row data split
  instead (see Implementation above) -- both kinds of change turned out to
  be needed, just for different fasts.

## Bug found 2026-08-24: 9 dates with stale/never-ingested fast_exception

Brian noticed Aug 28, 2026 showing "Wine and Oil are Allowed" for Greek
tradition when antiochian.org and goarch.org both show a strict fast that
day. Not a rule-logic gap like the findings above -- the `common`-tradition
row for that Friday is correctly strict (`fast=1, fast_exception=0`); the
bug was in a separate `greek`-tradition `Day` row for 8/28 (blank title,
`feast_level=0`) carrying `fast_exception=1` with nothing to justify it.

Found 9 such rows total (`title=''`, `feast_name=''`, `feast_level=0`,
`fast_exception>0`, `tradition='greek'`) by querying the DB directly.
Cross-checked each against its own already-cached `data/antiochian_raw/
*.json` fetch using `ingest_antiochian.py`'s own `fast_exception_for()` --
which parses correctly -- and every single one of the 9 mismatched what
its own cached source actually says. 7 of the 9 shared the exact same
stale value (`fast_exception=2`), suggesting these were placeholder rows
that were never actually run through the fastDesignation-parsing step at
all, not a parsing bug (the parser itself checks out fine against all 9
sources). Corrected all 9 directly from the cached raw JSON:

| Date | antiochian.org | Was | Now |
|---|---|---|---|
| Mar 31 | Strict | Wine & Oil (1) | Strict (0) |
| May 7 | No Fast | Fish/Wine/Oil (2) | No Fast (11) |
| May 11 | No Fast | Fish/Wine/Oil (2) | No Fast (11) |
| Jul 15 | Strict | Fish/Wine/Oil (2) | Strict (0) |
| Jul 26 | No Fast | Fish/Wine/Oil (2) | No Fast (11) |
| Aug 28 | Strict | Wine & Oil (1) | Strict (0) |
| Sep 25 | Strict | Fish/Wine/Oil (2) | Strict (0) |
| Oct 1 | No Fast | Fish/Wine/Oil (2) | No Fast (11) |
| Dec 13 | Fish/Wine/Oil | Fish/Wine/Oil (2) | Wine & Oil (1) |

168/168 tests pass; fixture diff is exactly these 9 `fast_exception`
values (no other fields touched). Slavic tradition's own Aug 28 row
(Ven. Job of Pochaev, polyeleos rank) was left untouched -- that
exception has an actual feast-rank basis and wasn't part of this bug.

**Not investigated further**: whether other `greek`-tradition rows (not
matching this exact blank-placeholder shape) have similar staleness --
this pass only searched for the specific pattern that surfaced the bug.

### Correction: the 4 "Strict" dates initially used the wrong index

Brian noticed Aug 28 now displaying an explicit "Strict Fast" label,
when other ordinary full-abstention Wed/Fri days (e.g. 8/21, 8/26) show
no label at all for the identical restriction -- only genuinely notable
strict-fast days (Beheading of John the Baptist, 8/29) get that
callout. The `DIETARY_ALLOWANCE_TO_FAST_EXCEPTION` table in
`ingest_antiochian.py` maps `DietaryAllowance.Strict` to
`fast_exception=9` ("Strict Fast"), and that mapping was used verbatim
for the Mar 31 / Jul 15 / Aug 28 / Sep 25 fixes above without checking
it against how the rest of the corpus actually represents an ordinary
strict day.

`FAST_EXCEPTION_TO_DIETARY_ALLOWANCE` in `datetools.py` shows indices
0, 9, and 10 all map to the identical `DietaryAllowance.Strict` rung
(same abstentions either way) -- they're display-text variants for
different narrative contexts, not different dietary outcomes. Checking
the DB directly: `fast_exception=9` appeared *nowhere* in the entire
`greek`-tradition table except these 4 rows just added, while `0`
(blank, no special text) is the convention used consistently elsewhere,
including for other full-abstention-but-unremarkable rows ("Forefeast
of Annunciation", "Wednesday of the Fifth Week of Lent"). Corrected all
4 from 9 to 0 to match. The other 5 dates (`11`/Fast Free, `1`/Wine and
Oil) weren't affected by this mistake -- `11` is a code-recognized
sentinel (`_apply_fasting_adjustments` forces `NoFast` on sight of it)
and `1` already matched precedent elsewhere.

168/168 tests pass after the correction; fixture diff is exactly these
4 rows' `fast_exception`, 9 -> 0.

### Related open question: does Aug 28's vigil reading set actually apply to Greek tradition?

While investigating the fast_exception bug above, Brian separately
noticed the Aug 28 scripture readings shown for Greek tradition (all
`Reading` rows for that date are tagged `tradition='common'`, so both
traditions get the same set) include a full vigil package -- 3 Vespers
Old Testament lessons (Wisdom of Solomon), a Matins Gospel, and a
"St Job" Epistle/Gospel pair (Galatians 5.22-6.2 / Luke 6.17-23) for
Ven. Job of Pochaev, a specifically Slavic/ROCOR saint. OCA's own page
lists exactly this same 8-reading set (confirmed directly), so it's
certainly correct for Slavic.

For Greek: antiochian.org's own reading citations for 8/28 show only
the ordinary Epistle/Gospel (2 Cor 11.5-21 / Mark 4.1-9) -- no "St Job"
variant, no vespers/matins citations -- but the page *does* separately
link a "Great Vespers" service text, which turned out (on inspection)
to actually be for Aug 29's Beheading of John the Baptist feast (served
the evening before, cross-linked from both days -- confirmed the same
file is linked from Aug 29's own page too, alongside Festal Orthros and
Divine Liturgy Variables). So that PDF doesn't settle anything about
Aug 28 itself. Checked goarch.org as well; also inconclusive.

**Left as-is**: no confirming evidence either way that Job of Pochaev's
vigil should or shouldn't extend to Greek tradition here, and per this
project's standing rule, data isn't changed on inference alone. If this
comes up again, the open question is specifically whether Antiochian/
GOARCH assign vigil rank to Job of Pochaev (or any other of 8/28's
several co-commemorated saints -- Moses the Black, the 33 Martyrs of
Nicomedia, Synaxis of the Kiev Cave Fathers) the way OCA does, not
whether the vigil itself is real (it evidently is, for Slavic).
