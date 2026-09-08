"""How a day's dietary allowance is decided.

Two cycles contribute to any given day -- the Paschal cycle and the festal one
-- and something has to combine them. That used to be `max()` over
`Day.fast_exception`, an integer that simultaneously encoded a dietary rung, a
precedence claim and a sentinel, followed by a run of weekday and season special
cases patching whatever the comparison got wrong. See
docs/fasting-refactor-scope.md for why that could not be arithmetic.

This says the rule out loud instead:

    a SEASON gives a floor per weekday, and a cap on how far a claim may lift it
    a DATA ROW either CLAIMS a rung ("this date allows wine and oil") or CAPS
        one ("this day is strict whatever else falls on it")
    a RANK RULE may grant more, where a source states one
    the answer is the most lenient claim, with every cap applied

Each season's numbers are sourced, not fitted; the citations are on the
definitions below and collected in docs/fasting-refactor-scope.md.
"""
from dataclasses import dataclass, field

from .datetools import (
    DietaryAllowance as D, FastLevels, Weekday,
    FAST_EXCEPTION_TO_DIETARY_ALLOWANCE as RUNG,
)

SUN, MON, TUE, WED, THU, FRI, SAT = (
    Weekday.Sunday, Weekday.Monday, Weekday.Tuesday, Weekday.Wednesday,
    Weekday.Thursday, Weekday.Friday, Weekday.Saturday)

FAST_FREE = 11
# Rows that assert strictness rather than leniency. 9 and 10 are the strict eves
# and Clean/Holy Week's "no overrides"; 5 is Holy Saturday, which allows wine
# but *not* oil -- "on this one Saturday, alone among Saturdays of the year,
# olive oil is not permitted" -- so it must beat a saint's wine-and-oil claim
# rather than lose to it. 5 both claims and caps: it lifts the strict floor too.
CAP_INDICES = (5, 9, 10)
CLAIMLESS_INDICES = (0, 9, 10)

# What to report as `fast_exception` when the season decided the outcome rather
# than any particular row: one canonical legacy index per rung. The field is
# published by calendarium/api.py, which is the only reason it still exists.
CANONICAL = {
    D.Strict: 0, D.WineOnly: 5, D.WineAndOil: 1, D.WineOilCaviar: 6,
    D.FishWineOil: 2, D.MeatFast: 7, D.FastFree: 11,
}


@dataclass(frozen=True)
class Grant:
    """A rank rule: a saint of `min_rank` on these weekdays may eat `rung`."""
    min_rank: int
    weekdays: tuple
    rung: D


@dataclass(frozen=True)
class Season:
    name: str
    floor: dict = field(default_factory=dict)
    default_floor: D = D.Strict
    cap: dict = field(default_factory=dict)
    default_cap: D = D.FastFree
    cap_exempt_rank: int = 99
    grants: tuple = ()
    # Ch. 33's rank clause is stated but has never been implemented; see
    # docs/fasting-refactor-scope.md. Kept off so this refactor changes nothing.
    apply_grants: bool = False
    # Clamps fish away in the days before Nativity -- Ch. 33: "from the 20th of
    # December until the 25th, even if it be Saturday or Sunday, we do not allow
    # fish." Slavic only; Greek expresses the same tightening as a second season.
    no_fish_before_nativity: bool = False
    # Reproduces a bug in the code this module replaced, so the change could be
    # proven to alter nothing. That code wrote the Wednesday/Friday cap as an
    # assignment rather than a clamp, so it *raised* a strictness assertion
    # instead of only lowering a leniency claim, and Nativity Eve came out more
    # lenient on Wednesday and Friday than on Monday or Thursday. Removing this
    # is the fix; see docs/fasting-refactor-scope.md.
    legacy_wed_fri_assignment: bool = False

    def floor_for(self, weekday):
        return self.floor.get(weekday, self.default_floor)

    def cap_for(self, weekday, feast_level):
        if feast_level >= self.cap_exempt_rank:
            return D.FastFree
        return self.cap.get(weekday, self.default_cap)


# --- the seasons ------------------------------------------------------------

ORDINARY = Season('ordinary Wed/Fri', default_floor=D.Strict)

# Not a fasting season, but a day still carries an allowance label: a feast row
# on a free day says "Fish, Wine and Oil are Allowed" and that is what gets
# shown. `fast_abstentions_for` short-circuits on NoFast, so the rung is unused.
NO_FAST = Season('no fast', default_floor=D.Strict)

# Ware, *The Lenten Triodion*, via OCA: weekdays strict, weekend wine and oil
# (supplied by the Paschal-cycle rows), fish only on the Annunciation and Palm
# Sunday, which are ranks 7 and 8.
LENT = Season('Great Lent', default_floor=D.Strict,
              default_cap=D.WineAndOil, cap_exempt_rank=7)

# OCA: "wine and oil are allowed only on Saturdays and Sundays (and sometimes on
# a few feast days and vigils)" -- in practice the Transfiguration, rank 8.
DORMITION = Season('Dormition', floor={SAT: D.WineAndOil, SUN: D.WineAndOil},
                   default_floor=D.Strict,
                   default_cap=D.Strict, cap_exempt_rank=7)

# Typikon Ch. 33: "on Tuesday and Thursday we do not eat fish, but only oil or
# wine. On Monday, Wednesday and Friday, we eat neither oil nor wine.... On
# Saturday and Sunday we eat fish."
_CH33_FLOOR = {MON: D.Strict, TUE: D.WineAndOil, WED: D.Strict,
               THU: D.WineAndOil, FRI: D.Strict,
               SAT: D.FishWineOil, SUN: D.FishWineOil}
_CH33_CAP = {WED: D.WineAndOil, FRI: D.WineAndOil,
             SAT: D.FishWineOil, SUN: D.FishWineOil}
# The rest of Ch. 33, which the app has never applied: "If there occur on
# Tuesday or Thursday a Saint who has a [Great] Doxology, we eat fish; if on
# Monday, the same; but if on Wednesday or Friday, we allow only oil and wine....
# If it be a Saint who has a Vigil on Wednesday or Friday ... we allow oil and
# wine and fish." Doxology is feast level 3, Vigil is 5.
_CH33_GRANTS = (
    Grant(min_rank=3, weekdays=(MON, TUE, THU), rung=D.FishWineOil),
    Grant(min_rank=3, weekdays=(WED, FRI), rung=D.WineAndOil),
    Grant(min_rank=5, weekdays=(WED, FRI), rung=D.FishWineOil),
)

APOSTLES = Season('Apostles', floor=_CH33_FLOOR, cap=_CH33_CAP,
                  cap_exempt_rank=4, grants=_CH33_GRANTS,
                  legacy_wed_fri_assignment=True)
NATIVITY = Season('Nativity', floor=_CH33_FLOOR, cap=_CH33_CAP,
                  cap_exempt_rank=4, grants=_CH33_GRANTS,
                  no_fish_before_nativity=True,
                  legacy_wed_fri_assignment=True)

# Greek practice differs only in the Nativity fast, and there it splits in two:
# for the first four weeks everything but Wednesday and Friday is a fish day,
# and from Dec 13 it tightens further than Slavic practice does -- Monday,
# Tuesday and Thursday drop to full strictness rather than merely losing fish.
# See docs/greek-fasting.md.
NATIVITY_GREEK_EARLY = Season(
    'Nativity (Greek, to Dec 12)',
    floor={WED: D.Strict, FRI: D.Strict}, default_floor=D.FishWineOil,
    cap={WED: D.WineAndOil, FRI: D.WineAndOil}, default_cap=D.FishWineOil,
    cap_exempt_rank=4, legacy_wed_fri_assignment=True)
NATIVITY_GREEK_STRICT = Season(
    'Nativity (Greek, from Dec 13)',
    floor={SAT: D.WineAndOil, SUN: D.WineAndOil}, default_floor=D.Strict,
    cap={SAT: D.WineAndOil, SUN: D.WineAndOil}, default_cap=D.WineAndOil,
    cap_exempt_rank=4, legacy_wed_fri_assignment=True)

_BY_LEVEL = {
    FastLevels.NoFast: NO_FAST,
    FastLevels.Fast: ORDINARY,
    FastLevels.LentenFast: LENT,
    FastLevels.DormitionFast: DORMITION,
    FastLevels.ApostlesFast: APOSTLES,
    FastLevels.NativityFast: NATIVITY,
}


def slavic_season(day):
    return _BY_LEVEL.get(day.fast_level)


def greek_season(day):
    if day.fast_level == FastLevels.NativityFast:
        return (NATIVITY_GREEK_STRICT if day.pdist >= day.pyear.nativity - 12
                else NATIVITY_GREEK_EARLY)
    return _BY_LEVEL.get(day.fast_level)


# --- the rule ---------------------------------------------------------------

def resolve(season, weekday, feast_level, rows, no_fish=False, eve_on_weekend=False):
    """Combine a day's contributing rows into (rung, legacy fast_exception)."""
    claims = [(i, RUNG[i]) for i in rows if i not in CLAIMLESS_INDICES]
    caps = [(i, RUNG[i]) for i in rows if i in CAP_INDICES]

    for index, rung in claims:
        if rung is D.FastFree:              # a fast-free row ends the question
            return D.FastFree, index

    allowance = season.floor_for(weekday)
    winner = None                           # the row that set the current answer
    season_cap = season.cap_for(weekday, feast_level)

    for index, claim in claims:
        # A season cap means "no fish", and caviar is not fish -- dietarily
        # WineOilCaviar excludes exactly what WineAndOil does -- so a caviar
        # claim survives the cap rather than being clamped below it.
        clamped = (claim if claim is D.WineOilCaviar and season_cap >= D.WineAndOil
                   else min(claim, season_cap))
        if clamped > allowance:
            # A clamped claim no longer speaks for itself; the season does.
            allowance, winner = clamped, (index if clamped == claim else None)

    if season.apply_grants:
        for grant in season.grants:
            if feast_level >= grant.min_rank and weekday in grant.weekdays:
                if grant.rung > allowance:
                    allowance, winner = grant.rung, None

    for index, cap in caps:
        if cap < allowance:
            allowance, winner = cap, index
        elif cap == allowance and winner is None:
            winner = index                  # it agrees, and has the better label

    index = winner if winner is not None else CANONICAL[allowance]

    if (season.legacy_wed_fri_assignment and weekday in (WED, FRI)
            and feast_level < season.cap_exempt_rank and index > 1):
        allowance, index, winner = D.WineAndOil, 1, None

    if no_fish:
        allowance = min(allowance, D.WineAndOil)
        winner = None
    if eve_on_weekend and weekday in (SAT, SUN) and allowance < D.WineAndOil:
        allowance, winner = D.WineAndOil, None

    return allowance, (winner if winner is not None else CANONICAL[allowance])


def apply(day, season_for):
    """Set `day.fast_level` and `day.fast_exception` for one day."""
    rows = [d.fast_exception for d in day.days]

    if FAST_FREE in rows:
        day.fast_level = FastLevels.NoFast
        day.fast_exception = FAST_FREE
        return

    # The Apostles' fast cannot be read off the database: the feast of Sts Peter
    # and Paul belongs to the festal cycle while the fast's start is Paschal.
    if 56 < day.pdist < day.pyear.peter_and_paul:
        day.fast_level = FastLevels.ApostlesFast
        if day.pdist == 57:
            day.service_notes.append("Beginning of Apostles' Fast")

    season = season_for(day)
    no_fish = bool(season and season.no_fish_before_nativity
                   and day.pyear.nativity - 6 < day.pdist < day.pyear.nativity - 1)
    eve = day.pdist in (day.pyear.nativity - 1, day.pyear.theophany - 1)

    _, day.fast_exception = resolve(
        season, day.weekday, day.feast_level, rows,
        no_fish=no_fish, eve_on_weekend=eve)
