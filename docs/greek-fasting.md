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

### Great Lent / Holy Week -- no structural difference found

Repeated searches across several Antiochian sources kept returning the same
weekly structure already in our code: weekdays strict/xerophagy, weekends
wine+oil, fish on Annunciation and Palm Sunday. The differences that did
surface were the food-category nuances noted above (out of scope), plus what
looks like a pre-existing data completeness gap independent of tradition
(a couple of well-known Lenten wine+oil feast-day exceptions -- Feb 24,
Mar 9 -- appear to be missing their `fast_exception` override in our
existing Slavic-modeled data). Not investigated further; unrelated to the
Greek/Slavic question.

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

## Remaining / not investigated

- The possible Feb 24 / Mar 9 Lenten wine+oil data gap noted above -- appears
  unrelated to Greek/Slavic tradition, not picked up here.
- No data changes ended up being needed for this project, despite the
  original expectation -- everything found was expressible as weekday-based
  code logic (`GreekDay._apply_fasting_adjustments`), not per-date
  `fast`/`fast_exception` baseline changes.
