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

1. **Characterisation test first.** Pin the current fasting output --
   `fast_level`, `fast_exception`, `fast_abstentions_desc` -- for every day of
   several years in both traditions. Refactor until it is byte-identical, then
   change behaviour deliberately and visibly.
2. The Greek path has its own `_apply_fasting_adjustments`, so both need
   covering.
3. The API exposes these fields; check `calendarium/tests/data/january.json` and
   the API schema before changing anything user-visible.

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
  The current code there only ever reduces an exception, never grants one.
