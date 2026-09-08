# Scoping a fasting-model refactor

Written 2026-09-02, while the reasoning was fresh. **Nothing here is
implemented.** It came out of investigating why Jul 24 lacked a wine-and-oil
allowance (`docs/oca-audit.md`), which ended with Brian's observation that
combining the two cycles ought to be arithmetic and clearly is not.

## The diagnosis

`Day.fast_exception` is one integer doing three unrelated jobs:

1. **A dietary rung** -- what may be eaten. Indices 1, 2, 5, 6, 7, 11.
2. **A precedence claim.** Indices 3 and 4 are dietarily identical to 1 and 2
   and exist only to win a comparison. orthodox_calendar's own reference says
   so outright: `3 Wine & Oil Allowed (cannot be overriden by 2)`,
   `4 Fish, Wine & Oil Allowed (overrides 3)`.
3. **A sentinel.** `0` is "no annotation", `10` is "no overrides". Neither is a
   diet.

The two cycles are then combined with

```python
self.fast_exception = max(d.fast_exception for d in self.days)
```

Because jobs 2 and 3 are encoded in the magnitude, that `max()` cannot be
arithmetic on leniency, and is not. It resolves:

| collision | max | result | which side won |
|---|---|---|---|
| 1, 2 | 2 | Fish, wine, oil | the more lenient |
| 2, 3 | 3 | Wine and oil | the **stricter** |
| 1, 9 | 9 | Strict | the stricter |
| 2, 10 | 10 | Strict | the stricter |
| 1, 11 | 11 | Fast free | the more lenient |
| 7, 1 | 7 | Meat fast | the more lenient |
| 8, 2 | 8 | Wine and oil | the **stricter** |

It is a priority encoding whose integer ordering was reverse-engineered so that
`max()` picks the intended winner in each known collision. Everything it gets
wrong is then patched in `_apply_fasting_adjustments`, which is why that method
reads as a pile of weekday and season special cases rather than a rule -- and
why adding one more patch to it felt wrong enough to stop.

## The clean ladder already exists, and is unused

`datetools.DietaryAllowance` is exactly the monotonic strict-to-free ladder this
wants, with `FAST_EXCEPTION_TO_DIETARY_ALLOWANCE` mapping every legacy index
onto it. Its own docstring says `FastExceptions` "mixes real dietary rungs with
app-internal bookkeeping values".

It is referenced in **one line of the application** -- `day.py`'s
`fast_abstentions_desc`, for display. The combination logic never sees it.

## The shape to aim at

Separate the three jobs, then combine arithmetically:

- Resolve each contributing row to a `DietaryAllowance` rung.
- Combine with a stated rule rather than an emergent one. The natural one is
  that the Paschal cycle sets a floor and the festal cycle may lift it, with
  most-lenient-wins among festal rows.
- Make "no overrides" an explicit flag on the row, not a larger integer.
- Keep `fast_exception` as a presentation concern if the API must stay
  compatible -- `short_display` showed that these fields are public
  (`calendarium/api.py`), so the legacy index probably has to survive at the
  serialisation boundary even if it stops driving anything.

Most of `_apply_fasting_adjustments` should then dissolve: the weekday cases
become a season's floor for Wednesday and Friday, and the rank cases become "a
commemoration of rung N lifts the floor to N".

## Scale

Small, which is the encouraging part. Of 858 `Day` rows the awkward values are
16 at index 3, 5 at index 4, 8 at index 10 and 2 at index 8 -- about 30 rows.
The bulk are index 0 (718), 11 (36), 2 (34) and 1 (27).

## How to do it safely

1. **Characterisation test first. Done 2026-09-08.**
   `tools/fasting/characterize.py` writes
   `calendarium/tests/data/fasting-characterization.txt`, and
   `calendarium/tests/test_fasting_characterization.py` regenerates and compares
   it -- 3,652 days, five years across the whole Paschal range, both traditions,
   4 seconds. Each line carries the inputs as well as the outputs, so a diff
   names the date, tradition, rank, season and contributing rows rather than
   just moving a number. Refactor until it is byte-identical, then change
   behaviour deliberately and visibly.
2. The Greek path has its own `_apply_fasting_adjustments`, so both need
   covering.
3. The API exposes these fields; check `calendarium/tests/data/january.json` and
   the API schema before changing anything user-visible.

## What the characterisation revealed

The pinned data has **36 distinct row-collision patterns and only 6 distinct
dietary outcomes**, which is the first encouraging sign: the output space is
tiny, close to `DietaryAllowance`'s seven rungs.

More useful, **six patterns resolve differently in different contexts** -- the
same contributing rows producing a different answer -- and that is precisely
the work `_apply_fasting_adjustments` is doing. `rows=(0,4)`, a single row
claiming fish, is the clearest window:

| outcome | season | feast levels | weekdays |
|---|---|---|---|
| exc 4, keeps fish | Lent, Dormition | **7-8** | any |
| exc 1, wine and oil | Dormition | 4-5 | Sat, Sun |
| exc 0, strict | Dormition | 4-5 | Mon-Fri |

**The discriminator is `feast_level`, plus season and weekday. It is not
precedence.** The same shape appears in `rows=(0,1)`, where a wine-and-oil claim
is zeroed on six Dormition days at feast level 3, and inverted in `rows=(0,0)`,
where *no* row claims anything and the Apostles' and Nativity fasts still
produce wine and oil on Tuesday and Thursday and fish at the weekend -- a floor
rather than a claim.

That settles the design question raised before starting: the row does not need a
stored precedence field. What indices 3 and 4 encode is "this claim is
important enough to survive the season's cap", and the rank that makes it
important is already on the row as `feast_level`. Palm Sunday is 8, the
Annunciation 7, the Transfiguration 8; the index-3 rows are all Paschal-cycle
rows at level 0, which set the floor rather than making a festal claim.

A first guess was that this generalises: the season sets a floor and a cap, and
a festal claim lifts the floor only if its rank clears the season's bar. The
sources say otherwise -- see below. **The mechanism differs by season**, and a
single rank-threshold model would be wrong for Lent.

## What the published rules actually say (checked 2026-09-08)

Checked before deriving anything from the data, so the parameters are sourced
rather than fitted. The Antiochian typikon at
`~/Documents/Orthodox Studies/54-typikon-full.pdf` is a service-order and
rubrics reference and contains no rank-based fasting rules; its fasting notes
are scattered and tied to individual feasts. The usable source is OCA's
guidelines page, which quotes the Typikon and the Lenten Triodion verbatim:
<https://www.oca.org/liturgics/outlines/fasting-fast-free-seasons-of-the-church>

| season | what the rule keys on | source |
|---|---|---|
| ordinary Wed/Fri | nothing; strict, and rank relaxations are called "local variations" | OCA guidelines |
| Great Lent | weekday/weekend, plus **named dates** | Ware, *The Lenten Triodion*, quoted by OCA |
| Apostles' & Nativity | weekday, plus **saint's rank** | Typikon Ch. 33, quoted verbatim |
| Dormition | weekday, plus a named feast | OCA guidelines |

**Apostles' and Nativity are explicitly rank-based.** Ch. 33: "on Tuesday and
Thursday we do not eat fish, but only oil or wine. On Monday, Wednesday and
Friday, we eat neither oil nor wine.... On Saturday and Sunday we eat fish. If
there occur on Tuesday or Thursday a Saint who has a [Great] Doxology, we eat
fish; if on Monday, the same; but if on Wednesday or Friday, we allow only oil
and wine.... If it be a Saint who has a Vigil on Wednesday or Friday ... we
allow oil and wine and fish.... But from the 20th of December until the 25th,
even if it be Saturday or Sunday, we do not allow fish."

Against the pinned data, the app's **base weekly pattern matches exactly** --
Mon/Wed/Fri strict, Tue/Thu wine and oil, Sat/Sun fish, and the December
tightening. **The rank clause is entirely unimplemented**: feast level 3,
doxology, behaves identically to level 0 on every weekday. Level 5, vigil, does
get fish on Wednesday, but from per-date data rather than from a rule, and
level 4 is inconsistent for the same reason.

**Lent is not rank-based.** Ware gives a named list of nine dates that take wine
and oil on a weekday of weeks 2-6, and names the Annunciation and Palm Sunday
for fish. The data agrees that rank is not the discriminator: on Lenten
weekdays *every* feast level has both outcomes --

| level | strict | wine and oil |
|---|---|---|
| 2 | 4 | 4 |
| 3 | 13 | 9 |
| 4 | 9 | 10 |
| 5 | 1 | 2 |

so no threshold separates them. (The two fish days are levels 7 and 8, which
fits a rank bar, but the source names them rather than ranking them, and two
dates cannot distinguish the two readings.)

**Dormition is the cleanest and already correct.** Strict on weekdays, wine and
oil at the weekend at every level 0-5, and the Transfiguration at level 8 takes
fish -- matching "wine and oil are allowed only on Saturdays and Sundays (and
sometimes on a few feast days and vigils)".

### What this means for the model

A row's `fast_exception` already *is* the named-date grant, which is why Lent
works today. What cannot live in data is the rank rule, because it keys on
weekday, and whether a fixed date falls on a Wednesday changes yearly -- the
same argument that moved the abbreviated-readings Sunday rule into code.

So the shape is:

- the **season** supplies a floor per weekday, and a cap;
- a **data row** supplies a named grant, as now;
- a **rank rule** supplies a further grant, per season -- only the Apostles' and
  Nativity fasts have one, and Ch. 33 states it precisely;
- the result is the most lenient of those, then the season's cap applied.

The Dormition cap is what currently reads as `if feast_level < 7 and
fast_exception > 0: fast_exception = 0`, and the Lenten cap is the `== 2` fish
strip. Both become one parameter each instead of a special case.

## The mock-up, and what it found (2026-09-08)

`tools/fasting/prototype.py` implements the model above and resolves every day
the characterisation pins, comparing its answer to the live one at the dietary
rung. It is not wired into the app.

**1824 of 1826 Slavic days, 99.9%** -- every season exact except two days.
Writing the rule out loud needed three concepts the legacy integer hides:

- **claims versus caps.** Most rows say "this date allows at least X". A few say
  "at most X": Clean Week's no-overrides, the strict eves, and Holy Saturday,
  which allows wine but *not* oil -- "on this one Saturday, alone among
  Saturdays of the year, olive oil is not permitted" -- and so must beat a
  saint's wine-and-oil claim rather than lose to it. Holy Saturday is both: it
  lifts the strict floor and caps above itself.
- **the ladder is not linear at one point.** `WineOilCaviar` excludes exactly
  what `WineAndOil` does; it is a callout, not a stricter rung. A season cap
  meaning "no fish" must let a caviar claim through rather than clamp it.
- **a season cap is a clamp, not an assignment** -- which is where the two
  remaining differences come from.

### The two differences are a bug in current behaviour

Nativity Eve carries `fast_exception = 9`, "Strict Fast", every year. What the
app does with it depends on the weekday:

| weekday | current | |
|---|---|---|
| Sunday | wine and oil | correct -- the eve-on-weekend rule |
| Monday, Thursday | strict | correct |
| **Wednesday, Friday** | **wine and oil** | **wrong** |

The Apostles'/Nativity rule for Wednesday and Friday reads
`if feast_level < 4 and fast_exception > 1: self.fast_exception = 1`. It is
meant to *remove* fish from a lenient claim, but it is written as an assignment,
so it also *raises* a strictness assertion. Nativity Eve therefore becomes more
lenient on precisely the two strictest weekdays. The prototype gets it right by
construction, because a cap there can only lower.

This is the concrete answer to "what does the refactor buy": the explicit model
found a bug the emergent one produced and hid, and the bug is of a kind the
architecture invites.

### Both traditions, and the legacy index too

Extended to Greek, whose only structural difference is the Nativity fast: it
splits into two seasons, everything but Wednesday and Friday being a fish day
until Dec 12 and Monday, Tuesday and Thursday dropping to full strictness from
Dec 13 (`docs/greek-fasting.md`).

The prototype also reproduces the legacy `fast_exception` index, because
`calendarium/api.py` publishes it. A row that decides the outcome reports its
own value; where the season decides, one canonical index per rung is used. That
keeps indices 3 and 4 -- whose whole purpose was precedence -- reporting as
themselves even though the model no longer needs them to.

With the Wednesday/Friday quirk emulated behind
`Season.legacy_wed_fri_assignment`, the prototype reproduces **3652 of 3652
days exactly**, in both traditions, on both the dietary rung and the legacy
index. Running it with `--fixed` turns the flag off and changes exactly the four
Nativity Eve days and nothing else.

That is the licence to swap the implementation: the refactor lands
byte-identical with the flag on, and removing the flag is a four-line diff in
the characterisation file.

## Step 1 done: the model is the implementation (2026-09-08)

`calendarium/fasting.py` now holds the seasons and the rule; both
`SlavicDay._apply_fasting_adjustments` and `GreekDay`'s are two lines that call
it. `calendarium/liturgics/day.py` loses 145 lines and gains 9.

**The characterisation test passes unchanged** -- 3,652 days, both traditions,
identical on the dietary rung and on the legacy `fast_exception` index. The
Wednesday/Friday quirk is preserved deliberately behind
`Season.legacy_wed_fri_assignment` so this step could be proven to change
nothing at all.

One thing the swap turned up that the prototype had missed: on a **NoFast** day
the old code left `fast_exception` as the row maximum rather than treating the
day as fast-free, because `NoFast` matched none of its cases and fell through. A
feast row on a free day therefore still shows "Fish, Wine and Oil are Allowed".
`NO_FAST` is a real season now for that reason, and the characterisation caught
the difference on the first run.

### Still to do

- **Remove `legacy_wed_fri_assignment`.** That is the Nativity Eve fix, and it
  is a four-line diff in the characterisation file.
- **Turn on `Season.apply_grants`.** The Ch. 33 rank clause is written in
  `_CH33_GRANTS` and switched off, so the refactor changed nothing. Enabling it
  is a real behaviour change and wants its own commit and its own review of the
  characterisation diff.

## What is deliberately *not* in scope

The rank questions that surfaced during the investigation are behaviour
decisions, not refactoring, and should be settled separately once the model can
express them cleanly:

- Whether an ordinary Wednesday or Friday takes wine and oil for a
  polyeleos-rank commemoration. **A rule for this was added and then backed out**
  before shipping, precisely because it was another patch on the pile. Evidence
  stands at seven confirmations from holytrinityorthodox.com plus Brian's St
  Tikhon's calendar, against OCA's published guidelines, which call such
  relaxations "local variations". See `docs/oca-audit.md`.
- Whether the threshold is doxology (level 3) rather than polyeleos (level 4),
  and whether vigil rank (level 5) should take fish. The Typikon text OCA quotes
  uses exactly those two ranks, but scoped to the Apostles' and Nativity fasts.
- Implementing that Typikon rule inside those two fasts, where it *is* stated.
  The current code there only ever reduces an exception, never grants one, and
  the section above confirms level 3 behaves exactly like level 0 there. This is
  the best-evidenced of the three and the natural first behaviour change once
  the refactor lands -- but it is still a behaviour change, and belongs in its
  own commit with the characterisation diff visible.
