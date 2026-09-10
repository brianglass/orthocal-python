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

## Step 2 done: Nativity Eve is strict again (2026-09-08)

`legacy_wed_fri_assignment` is removed, which fixes the bug the prototype found.
The characterisation diff is exactly four lines in each direction -- Dec 24 in
2025 and 2027, both traditions, the two years it falls on a Wednesday or a
Friday -- going from wine and oil to a full abstention.

The day is coherent now, and matches Theophany Eve, which was always correct
because the ordinary fast never carried the buggy clamp:

| weekday | Nativity Eve |
|---|---|
| Sunday | wine and oil -- the eve-on-weekend rule |
| every other day | strict |

Nothing else moved: 190 tests pass and `calendarium/tests/data/january.json` is
untouched, since Jan 5 resolves through `ORDINARY` rather than the Nativity
season.

## Step 3 held: Ch. 33's rank clause is not settled (2026-09-09)

Enabling `apply_grants` changes **70 of 3652 days**, all loosenings, and all
exactly what Ch. 33 states: doxology rank and above takes fish on Monday,
Tuesday and Thursday, and wine and oil on Wednesday and Friday. Levels 5 and up
are unaffected because the data already grants them fish.

It was measured against antiochian.org and **not committed**, for three reasons.

**The measurement was of a half-applied change.** `apply_grants` reached the
Slavic `APOSTLES` and `NATIVITY` and the shared Greek Apostles season, but not
`NATIVITY_GREEK_EARLY` or `NATIVITY_GREEK_STRICT`, which are separate objects.
Greek would have had Ch. 33 ranks during one fast and not the other.

**antiochian.org is the wrong yardstick for it.** Agreement moved 56/90 to
60/90, which looked like weak support -- but each jurisdiction keeps its own
typikon, so Antiochian practice departing from the rule OCA quotes is not
evidence against that rule. It is evidence they are different churches. Judging
a Slavic change by an Antiochian source was the error.

**So it still wants a Slavic source.** holytrinityorthodox.com publishes a
dietary line per day; four or five doxology-rank days in the Apostles' or
Nativity fast falling on a Monday, Tuesday or Thursday would settle it.

The rule stays written and switched off in `_CH33_GRANTS`, with its citation.

## The "Antiochian typikon" is the Typikon of the Great Church (2026-09-09)

**Correcting the framing used throughout the section below.** The PDF at
`~/Documents/Orthodox Studies/54-typikon-full.pdf` is not an Antioch-specific
book. Its own foreword identifies it as Rizkallah Arman's 1951 Arabic
translation, checked against "the Typikon of the Great Church of
Constantinople", and states plainly: "The Orthodox Churches in the East now use
the Typikon of the Great Church of Christ in Constantinople originally received
from St. Sabbas with some changes."

That is the Violakis typikon -- **the same one the Greek Orthodox Archdiocese
follows**. The same file is published as "The Book of the Typikon" at
equip-orthodox.com.

Three consequences, and they matter:

- **Chapter X's Wednesday/Friday exceptions apply to the Greek tradition
  generally, GOA included.** They are not an Antiochian peculiarity to be
  modelled as a separate jurisdiction. This app implements none of them.
- **The book marks its own local departures.** Footnote 343 attributes the
  fast-free Paschal season to a decree of "the Holy Synod of Antioch"; the main
  text says only that fish is permitted on those days. So the typikon
  distinguishes the shared rule from Antioch's extension of it, and we can read
  which is which.
- **GOA and Antioch should not diverge much in principle**, sharing a typikon.
  The 14% figure measured below is *this app against Antiochian practice*, not
  GOA against Antioch, and much of it is more likely to be our model being
  wrong than a jurisdictional difference. Brian's scepticism on this point was
  correct.

## What that typikon says about Wednesdays and Fridays (2026-09-09)

An earlier pass concluded the Antiochian typikon "contains no rank-based fasting
rules". **That was wrong, and the miss was a search failure**: the grep looked
for rank words near food words, and the relevant section names neither. It is in
the table of contents --

    Chapter X General Directions
        Wednesdays and Fridays when exceptions to the fast are permitted…570

and reads, verbatim:

> Wednesdays and Fridays when meat is permitted. Between the feast of the
> Nativity of Christ and the feast of Epiphany, except for the Forefeast of
> Epiphany. Between the Sunday of the Pharisee and the Publican and the Sunday
> of the Prodigal Son. During Bright Week. During the week of Pentecost.
>
> On Wednesday and Friday during Cheesefare Week dairy products are permitted.
> On Wednesdays and Fridays between Thomas Sunday and Pentecost, fish is
> permitted.[343] Fish is permitted on Wednesday or Friday if it is a feast of
> the Lord even during fasting seasons, except for Holy Week. Such feasts are:
> the Annunciation, Palm Sunday, and the Transfiguration. If a feast of the
> Theotokos or one of the 12 Apostles falls on Wednesday or Friday. During the
> days following a feast of the Lord or the Theotokos until its leavetaking
> except during Great Lent and the Fast of the Theotokos.

Footnote 343: "The Holy Synod of Antioch has decreed that there will be no
fasting on Wednesday and Friday, not only during Bright week, but during the
entire Paschal season until the Feast of the Ascension."

**This is a categorical rule, not a rank one.** It keys on *what kind* of feast
-- of the Lord, of the Theotokos, of the Twelve Apostles, or an afterfeast --
where the Ch. 33 text OCA quotes keys on typikon rank. Both are in the same
book, addressing different fasts: Ch. 33 governs the Apostles' and Nativity
fasts, Chapter X the ordinary Wednesdays and Fridays of the year. They are not
rival jurisdictional readings, which is how an earlier draft of this section
described them.

### The Antiochian Paschal rule, stated exactly (corrected 2026-09-09)

The rule has two edges and no exceptions:

> **From Pascha through the Apodosis of Pascha, no fast at all, on every day of
> the week. From the Feast of the Ascension, ordinary fasting resumes.**

Verified two ways. Antioch's published *2026 Fasting Calendar* -- a colour-coded
PDF, so its text layer carries only the date numbers and it has to be read as an
image -- leaves April white from the 12th, Pascha, and May white except the
22nd, 27th and 29th, which are red. Ascension 2026 is May 21, so those three are
the Wednesdays and Fridays *after* it. Their API agrees on the same three days,
and across the whole harvest **96 of 96 days from Pascha to the Apodosis are
"no fast"**.

An earlier note here claimed their own calendar only followed the decree about
79% of the time. **That was wrong**, and the error was in the analysis rather
than the data: the Paschal season was bucketed as Pascha to Pentecost, pdist 0
to 49, when the decree ends at Ascension, pdist 39. The days that looked like
contradictions were the ones the decree explicitly excludes.

The lesson generalises past this rule: `pdist 0..49` is Pascha to Pentecost and
is the wrong window for anything scoped to Ascension, which is pdist 39.

### Implemented (2026-09-09): Chapter X is almost entirely satisfied already

Measured clause by clause against five years, counting only Wednesdays and
Fridays that currently fall below fish and that a clause would lift:

| clause | days it changes |
|---|---|
| **fish between Thomas Sunday and Pentecost** | **47 over 5 years, 9.4/yr** |
| fish on a feast of the Lord | 1 |
| fish on a feast of the Theotokos | 0 |

The second and third are already satisfied by the data. The typikon names the
three feasts of the Lord that can fall in a fasting season -- the Annunciation,
Palm Sunday and the Transfiguration -- and all three already carry
`fast_exception = 4`, fish. The single day the "feast of the Lord" clause would
have lifted is the Exaltation of the Cross, which the same typikon lists as a
fast day in its own right, so lifting it would have been wrong.

So only the Paschal clause needed implementing: `PASCHAL_WEDFRI` in
`calendarium/fasting.py`, Greek only. 47 days over five years move from wine and
oil to fish, all Wednesdays and Fridays, all inside the window.

**Not carried into Slavic practice.** OCA's guidelines make Bright Week and
Trinity Week fast-free and otherwise treat the Wednesdays and Fridays of the
year as fast days, with no Paschal fish allowance.

**Antioch's further extension is not implemented either.** Its Holy Synod
decreed no fast at all on these days through Ascension, which footnote 343 marks
as a local decree rather than the shared rule.

## Measured against goarch.org (2026-09-09) -- two changes reverted

The Chapter X work above was validated against GOA's own calendar, and **two
changes made earlier the same day were wrong and have been backed out.** The
data is in `data/goarch_fasting.json`, 276 days across nine months and three
Decembers; `tools/fasting/goarch_audit.py` reproduces the score.

| | app vs goarch.org |
|---|---|
| as shipped that morning | 239/276 (86.6%) |
| **after the two reverts** | **257/276 (93.1%)** |

**1. The Paschal fish clause was wrong for GOA.** Chapter X says "On Wednesdays
and Fridays between Thomas Sunday and Pentecost, fish is permitted", and
`PASCHAL_WEDFRI` implemented exactly that. GOA gives **wine and oil**. April
2026 is unambiguous -- the grid labels Apr 22 and Apr 24, both inside the
window, "Wine". So neither jurisdiction follows the plain text of the clause
they share: Antioch is *more* lenient than it (no fast at all, by their Synod's
decree), GOA *less* (wine and oil). The clause is removed; the app is back to
what it did before, which was right.

Fish does appear on two Paschal Wednesdays in 2026 -- Mid-Pentecost (May 6) and
the Apodosis of Pascha (May 20). Both are feasts of the Lord, so what GOA
applies there is Chapter X's *feast-of-the-Lord* clause, not its Paschal one.

**2. The Nativity boundary was wrong, twice.** See `docs/greek-fasting.md`; it
is Dec 12, `nativity - 13`, pinned by December 2027 falling across a weekend.

### Ch. 33's rank clause: measured, and it does not hold for GOA

The doxology/vigil grants in `_CH33_GRANTS` were finally testable against
practice. Enabling them makes agreement **worse, 93.1% -> 92.8%**, and the
errors run in both directions:

- GOA grants wine and oil on days our data ranks 0 or 2 -- St Barbara (Dec 4,
  level 0), St Spyridon (Dec 12, level 2)
- GOA gives strict on days our data ranks 3 and 4 -- Dec 3 2025, Jan 9 2026

**Rank does not predict GOA's grants.** Whatever drives them is per-saint, not
a threshold on `feast_level`. `apply_grants` stays `False`, and the remaining 19
differences are a *data* question -- Greek `fast_exception` rows for specific
dates -- rather than a rule waiting to be written. That is the third time a
rank-threshold hypothesis has failed against practice data on this project.

## The full-year goarch audit (2026-09-09)

The 9-month sample was extended to **37 months -- Dec 2025 plus all of 2026,
2027 and 2028, 1,127 days.** Score, as each fix landed:

| | |
|---|---|
| starting point | 1032/1127 (91.6%) |
| after a bug in the audit's own `bucket()` | 1053/1127 (93.4%) |
| `APOSTLES_GREEK` | 1071/1127 (95.0%) |
| Greek Exaltation row | **1074/1127 (95.3%)** |

**The first correction was to the measuring tool, not the app.** `bucket()`
folded `MeatFast` in with `FastFree`, so all 21 Cheesefare days scored as
differences when the app had them right. Worth recording because it is the
second time in this work that a "finding" turned out to be an artifact of how
the comparison was set up.

### Extended to ten years (2026-09-10)

The harvest was extended to **121 months -- Dec 2025 plus every month of 2026
through 2035, 3,683 days.** Ten years is the threshold that matters: a fixed
date reaches a Wednesday or Friday in roughly two years out of seven, and those
are the only days on which an ordinary-time relaxation is visible at all.

| | |
|---|---|
| three-year state | 95.3% |
| ten-year baseline (more data, more gaps) | 94.8% |
| `GREEK_WINE_OIL_DATES` (38 dates) | 97.8% |
| Wednesday/Friday fish cap + `CHEESEFARE_GREEK` | 98.5% |
| Nativity cap raised to rank 7 | 99.3% |
| `GREEK_STRICT_DATES`, scoped to festal rows | **99.4%** |

**22 differences remain across ten years -- about two a year.**

Five things came out of it, in rough order of how much they moved the number.

**The fixed-date grant list is data, not a rule.** 38 dates on which GOA relaxes
a fast to wine and oil. Their `feast_level` here runs 0, 2, 3 and 4 -- Barbara
and Ignatius are level 0 -- so no threshold picks them out, which is the same
reason Ch. 33's rank grants failed. It lives in `fasting.py` rather than the
fixture because a `greek` Day row *replaces* the `common` one outright, so
encoding it as data would mean duplicating 38 feast names that would then drift.

**The Wednesday/Friday fish cap is real, and the confound is broken.** A saint's
fish grant falls back to wine and oil on a Wednesday or Friday, however highly
ranked -- fourteen saints at levels 4, 5 and 6. Feasts of the Lord and of the
Theotokos keep fish, which `cap_exempt_rank=7` expresses, plus three
lower-ranked Lord days named explicitly. **GOA does not honour Chapter X's "or
one of the 12 Apostles" clause**: John the Theologian, Thomas, Matthew and
Andrew are all capped.

**The same cap holds inside the Nativity fast.** `NATIVITY_GREEK_EARLY` had
`cap_exempt_rank=4`, which let St Matthew, St Andrew and St Nicholas through. It
is 7 now, matching ordinary time.

**Cheesefare week needed rescuing from that cap.** Adding a Wednesday/Friday cap
to Greek ordinary time silently clamped the week before Lent -- whose whole
point is that only meat is given up -- into a fast stricter than the Lent it
precedes. It has its own season now. The characterisation caught it
immediately.

**`GREEK_STRICT_DATES` is the mirror image**: nine dates whose festal grant GOA
does not recognise, chiefly the Beheading of the Forerunner, strict on all five
weekdays across seven observations. Dropping the *festal* claim and letting the
season floor stand is what makes the weekend relief still work; a first attempt
dropped every claim and made Lenten Saturdays stricter than the Saturdays either
side of them.

### The date lists moved out of the source (2026-09-10)

Brian objected that `GREEK_WINE_OIL_DATES` and its siblings were reference data
living in source code, and he was right. They are now sparse `Day` rows.

The mechanism is his: a tradition row overrides a `common` row **field by
field**, so it carries only what differs. `feast_level`, `fast` and
`fast_exception` are nullable for this, and **NULL means "inherit" while 0 means
"explicitly zero"** -- a distinction the Exaltation depends on, its Greek
override being an explicit `fast_exception=0`. `_prefer_tradition_days` becomes
`_merge_tradition_days`.

Django's model inheritance does not do this, incidentally: abstract bases give
separate tables with no row-level fallback, and multi-table inheritance makes a
child row *be* a parent row rather than override a different one. This is a
merge, not inheritance.

Two shapes now coexist in the fixture and mean different things:

| shape | meaning |
|---|---|
| `slavic` + `greek`, no common | genuine disagreement about *what is commemorated* -- Oct 1 is the Protection for Slavs, not for Greeks |
| `common` + one tradition row | an **override**: same commemoration, kept differently |

`TestDayOverrides` guards the second: an override may not carry fields the merge
ignores (they would silently go stale when the common row is edited), and must
either change something or anchor a commemoration.

**The move paid for itself immediately.** Writing the guard exposed three
overrides that changed nothing: for Feb 24 and Mar 9 the `common` row *already*
claimed wine and oil, so those two entries in `GREEK_WINE_OIL_DATES` had always
been dead -- invisible while the list lived in code, obvious the moment it
became rows. It also found a pre-existing no-op, Nov 24's `slavic` row, which
duplicated its common row in every field.

**And deleting that one was wrong.** Two `DayCommemoration` rows hang off it, so
it is a commemoration anchor that happens to override nothing. The foreign key
caught it, not the reasoning; the guard test now allows that case explicitly.
Worth remembering next time a Day row looks redundant -- 379 of them are
foreign-key targets.

### The last two constants, and what made them necessary

Brian objected to `GREEK_WED_FRI_FISH_OK_DATES` and `_PDISTS` on the same
grounds as the first lists. The honest answer to "what makes this necessary" is
that the Wednesday/Friday cap has to distinguish *feast of the Lord* from
*saint*, and our schema encodes that only as `feast_level >= 7` -- on a scale
that follows the **Slavic** reckoning. Five days are Lord-ish to GOA and ranked
lower by us: the Synaxis of the Forerunner is level 3 and keeps its fish, while
St Matthew is level 6 and does not.

Both constants are gone, by two different routes.

**The two pdists needed no replacement.** They were the Midfeast and the
Leavetaking of Pascha, and the cap should never have reached them: it means "no
fish for a *saint*", and the Paschal cycle is not a saint. Scoping the cap to
festal claims removes them on principle rather than by name -- the same
festal/Paschal distinction the strict-date handling already needed.

**The three dates became `Day.fast_cap_exempt`.** The concept has a name now:
"this commemoration's claim outranks the season's cap."

That is what the old scale said *positionally*. Indices 3 and 4 duplicate 1 and
2 in their wording precisely because they were the cap-outranking variants --
every index-3 row is a wine-and-oil grant inside Lent, every index-4 row a fish
grant inside a fast. **Reading it off the index was tried and does not work**:
it lifts the Dormition fast's cap too, giving fish on Aug 9 and Aug 13 where
antiochian.org lists the Leavetaking of the Transfiguration as a full abstention
day, and dropping goarch agreement to 99.6%. The precedence idea is real but not
universal, so it belongs on the row rather than in the index.

`calendarium/fasting.py` now contains no jurisdiction data at all -- only
seasons and the rule.

### Chasing the last stragglers: 99.4% -> 99.9%

Working through the 22 that survived turned up one substantive bug and several
small ones.

**Four `greek` rows were forcing fast-free on days GOA fasts.** May 7, May 11,
Jul 26 and Oct 1 carried `fast_exception = 11`, set by the August 2026 pass that
corrected nine stale rows -- **from antiochian.org**, before this tradition was
settled as GOA. Index 11 short-circuits the whole rule, so those dates were
fast-free even on a Wednesday or Friday, where GOA gives wine and oil. Zeroing
them lets the Paschal row supply the fast level again, which is weekday-aware;
three of the four then also needed adding to `GREEK_WINE_OIL_DATES`. That August
table is worth re-reading in full: it is the same jurisdictional mismatch as the
Nativity boundary and the Apostles' fast, and it had been sitting in the data
for a fortnight.

**`(2, 9)` was in two lists at once**, both `GREEK_WINE_OIL_DATES` and
`GREEK_STRICT_DATES`, so the grant silently won. GOA gives strict on two of the
three Wednesday/Friday observations, so it belongs only in the latter.

**Peter and Paul and St Philip keep fish**, against the Wednesday/Friday cap --
three observations each, fish every time. Both sit on a fast boundary, which is
the likeliest reason though two feasts cannot establish it. They needed
different mechanisms: Peter and Paul already claims fish, so exempting it from
the cap suffices, while our Philip row claims only wine and oil, so there is
nothing for an exemption to protect and `GREEK_FISH_DATES` grants it outright.

### The five that remain, and why they stay

| date | | |
|---|---|---|
| 2026-02-24, 2034-02-24, 2033-03-09 | Clean Week | `fast_exception = 10`, "no overrides", caps the grant. GOA relaxes the Finding of the Forerunner's Head and the Forty Martyrs even then. Letting a fixed-date grant through a sentinel that exists precisely to stop overrides is not a change to make for three days in ten years. |
| 2029-02-09 | GOA's own inconsistency | Feb 9 is strict on two of its three Wednesday/Friday occurrences and wine and oil on this one. |
| 2031-05-21 | GOA's own inconsistency | The Leavetaking of Pascha is fish on nine of its ten Wednesdays and wine and oil on this one. |

Two of the five are goarch.org disagreeing with itself, so **99.9% is close to
the ceiling this data supports.** Chasing further would mean fitting our
calendar to their noise.

### What the earlier three-year pass had said the remaining 53 were

**36 -- per-date wine and oil grants we lack.** GOA lifts an ordinary Wednesday
or Friday to wine and oil for a large set of saints: Barbara, Spyridon,
Eleutherius, the Prophet Daniel, Mary Magdalene, the Chains of Peter, and
twenty-odd more. Their `feast_level` in our data ranges over 0, 2, 3 and 4, so
no threshold picks them out -- consistent with the rank grants failing.

These are only *visible* on Wednesday and Friday, because on any other weekday
an ordinary-time day is already fast-free. A given date lands on Wed or Fri in
roughly 2 years out of 7, so **three years of data exposes only about a third of
the list.** Fully enumerating it needs on the order of ten years of harvest.
Inside the fasting seasons the problem does not arise -- every day is a fast
day, so Dec 15 shows up in all four harvested Decembers.

**8 -- fish capped to wine and oil on ordinary Wed/Fri.** With three years the
confound noted earlier is broken: 2028-01-07 is a **Friday** that keeps fish,
and 2027-01-20, 2027-10-06 and 2028-11-08 are **Wednesdays** that are capped. So
it is not a weekday rule. Every capped day is `feast_level` 5 -- *higher* than
several days that keep fish -- so it is not a rank rule either:

| GOA keeps fish | GOA caps to wine and oil |
|---|---|
| Nativity of the Theotokos (7), Meeting (8) | Three Hierarchs (5), John the Theologian (5) |
| Midfeast, Leavetaking of Pascha (0-4) | Chrysostom (5), Euthymius (5), Thomas (5) |
| Synaxis of the Forerunner (3) | Archangel Michael (5) |

The discriminator is **what kind of feast it is** -- of the Lord or of the
Theotokos, versus a saint -- which is exactly Chapter X's wording, except that
GOA does not honour its "or one of the 12 Apostles" clause: John the Theologian
and Thomas are both capped. Our schema has no Lord/Theotokos/saint category, so
this cannot be expressed today. `feast_level >= 7` catches the two great feasts
but would wrongly cap the Midfeast, the Leavetaking of Pascha and the Synaxis of
the Forerunner -- fixing 7 days and breaking 8.

**The remaining 9** are one-offs with no pattern yet: 5 wine-and-oil-to-strict,
2 fish-to-strict, 2 fast-free-to-wine-and-oil.

### Clause 4, afterfeasts: confirmed by GOA too

**goarch.org does not apply it either**, which settles the question the earlier
Antiochian measurement left open. Inside the Theophany afterfeast, Jan 9 2026 is
`strict-fast`; inside the Exaltation's, Sep 16 and Sep 18 2026 are both
`strict-fast`; inside the Nativity of the Theotokos', Sep 11 is `strict-fast`.
Strict is what this app already gives. No code needed, and the section below
stands as originally written.

### Clause 4, afterfeasts: measured against Antioch

Chapter X's last clause reads "During the days following a feast of the Lord or
the Theotokos until its leavetaking except during Great Lent and the Fast of the
Theotokos." Taking the afterfeast spans from each feast to its leavetaking --
Theophany Jan 7-14, Meeting Feb 3-9, Dormition Aug 16-23, Nativity of the
Theotokos Sep 9-12, Exaltation Sep 15-21, Entry Nov 22-25, plus Ascension and
Pentecost -- it would lift about **ten Wednesdays and Fridays a year** to fish,
a similar size to the Paschal clause. The rule's own exclusions behave
correctly: the Transfiguration's afterfeast falls inside the Dormition fast and
the Annunciation's inside Lent, and both drop out.

**antiochian.org does not apply it.** On 56 afterfeast Wednesdays and Fridays
outside Lent and Dormition, their calendar gives **strict on 43, and fish on
2**:

| afterfeast | antiochian.org |
|---|---|
| Theophany | strict 11, wine+oil 3, fish 2 |
| Meeting | strict 10, no fast 3, wine+oil 1 |
| Entry | strict 6, wine+oil 3 |
| Exaltation | strict 6 |
| Dormition | strict 5 |
| Nativity of the Theotokos | strict 5, wine+oil 1 |

Strict is what this app already gives, so implementing the clause would move us
*away* from the only practice data available. That is the reverse of the Paschal
clause, where Antioch goes further than the typikon rather than less far, and
our wine and oil was clearly too strict.

Either the clause is monastic rather than pastoral, or it is read more narrowly
than the plain text suggests. **Held for goarch.org**: if GOA gives fish on
afterfeast Wednesdays and Fridays, implement it; if strict, we are already
right and the clause needs no code.

### The Paschal-season candidate, and who it applies to

A Paschal-season fish allowance was raised earlier and withdrawn, on the grounds
that OCA's guidelines give no such allowance. For the **Greek** tradition the
Antiochian typikon is explicit, and its own calendar bears it out:

| Wed/Fri, Thomas Sunday to Pentecost | |
|---|---|
| Antiochian typikon | fish, and per the Synod footnote no fast at all |
| antiochian.org | "no fast" on 19 of 28 harvested days |
| **this app** | wine and oil on 20 of 28 -- agreeing on **3 of 28** |

Withdrawing it was right for Slavic and wrong for Greek.

## Does the GOA publish a typikon? Not reachable, but its rules are (2026-09-09)

goarch.org is behind Cloudflare and returns 403 to any fetch. The Archdiocese's
rules are published in its annual Yearbook, and three GOA parishes reproduce
them with attribution; all three agree:

> "Nativity Lent (November 15-December 24, although fish, wine and olive oil are
> permitted, except on Wednesdays and Fridays, **until December 17**)."

**This app starts the Greek Nativity fast's stricter period on December 13**
(`pdist >= nativity - 12`). That date came from two *Antiochian* parish sources
when the Greek fasting work was done (`docs/greek-fasting.md`), before the
decision that `greek` means GOA. GOA's own rule is five days later:

| 2026 | ours | GOA |
|---|---|---|
| Dec 13-17 | strict period | still fish, wine and oil |
| Dec 18 onward | strict period | strict period |

So five days a year are stricter than GOA prescribes. **Not changed** -- the
sources are three parish reproductions of the Yearbook rather than the Yearbook
itself, and `docs/greek-fasting.md` records real Antiochian sources for the
current date. What it needs is a decision about which jurisdiction the `greek`
tradition follows for fasting, given that it follows GOA for readings.

**Answered 2026-09-09: GOA, for fasting as for readings.** Brian's call, and the
Nativity boundary is now measured from the Archdiocese's own calendar rather
than from Antiochian sources. Antioch's fast-free Paschal season is explicitly
*not* adopted -- it appears to be unique to them, and is a nice-to-have for a
possible Antiochian tradition later.

### Settled since

`Season.apply_grants` was the last open item here. It has now been measured
against goarch.org and **fails** -- see "Ch. 33's rank clause" above. It stays
`False`, and the grants stay in `_CH33_GRANTS` as a recorded reading of the
typikon that practice does not bear out, not as pending work.

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
