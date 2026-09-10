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

    def floor_for(self, weekday):
        return self.floor.get(weekday, self.default_floor)

    def cap_for(self, weekday, feast_level):
        if feast_level >= self.cap_exempt_rank:
            return D.FastFree
        return self.cap.get(weekday, self.default_cap)


# --- the seasons ------------------------------------------------------------

# Ordinary time is mostly Wednesdays and Fridays, but a few fixed feasts are
# fast days in their own right -- the Exaltation and the Beheading of the
# Forerunner -- and those take wine and oil when they fall at the weekend.
# goarch.org is unambiguous across ten years: both are strict on all five
# weekdays and wine and oil on both Saturday and Sunday, without exception.
# Ordinary Saturdays and Sundays are not fasts at all, so they never reach this
# season and the weekend floor cannot leak onto them.
ORDINARY = Season('ordinary Wed/Fri',
                  floor={SAT: D.WineAndOil, SUN: D.WineAndOil},
                  default_floor=D.Strict)

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
                  cap_exempt_rank=4, grants=_CH33_GRANTS)
NATIVITY = Season('Nativity', floor=_CH33_FLOOR, cap=_CH33_CAP,
                  cap_exempt_rank=4, grants=_CH33_GRANTS,
                  no_fish_before_nativity=True)

# Greek practice keeps a much lighter Apostles' fast than Ch. 33 prescribes, and
# than Slavic practice: fish every day except Wednesday and Friday, which stay
# strict. Measured from goarch.org across 2026 and 2028, where the fast runs
# three weeks and every day matches on both -- see data/goarch_fasting.json.
# (2027's fast is one day long, so it says nothing either way.)
#
# This is the same shape as the Nativity fast's first phase below, so the floor
# and cap are shared.
_GREEK_FISH_FLOOR = {WED: D.Strict, FRI: D.Strict}
_GREEK_FISH_CAP = {WED: D.WineAndOil, FRI: D.WineAndOil}

APOSTLES_GREEK = Season(
    "Apostles (Greek)",
    floor=_GREEK_FISH_FLOOR, default_floor=D.FishWineOil,
    cap=_GREEK_FISH_CAP, default_cap=D.FishWineOil,
    cap_exempt_rank=4)

# The Nativity fast splits in two:
# through Dec 11 everything but Wednesday and Friday is a fish day, and from
# Dec 12 it tightens further than Slavic practice does -- fish goes entirely and
# Monday, Tuesday and Thursday drop to full strictness rather than merely
# losing fish.
#
# The boundary is measured from goarch.org's own published calendar rather than
# from a summary of it, and three Decembers pin it exactly: in 2027 Dec 11 is a
# Saturday and still a fish day while Dec 12 is a Sunday and only wine and oil.
# See docs/greek-fasting.md and data/goarch_fasting.json.
NATIVITY_GREEK_EARLY = Season(
    'Nativity (Greek, to Dec 11)',
    floor=_GREEK_FISH_FLOOR, default_floor=D.FishWineOil,
    cap=_GREEK_FISH_CAP, default_cap=D.FishWineOil,
    # 7, not 4: the Wednesday/Friday no-fish cap holds inside this fast exactly
    # as it does in ordinary time, and holds against high-ranking saints.
    # St Matthew (6), St Andrew (4) and St Nicholas (5) all fall here and all
    # get wine and oil rather than fish when they land on a Wednesday or Friday.
    cap_exempt_rank=7)
NATIVITY_GREEK_STRICT = Season(
    'Nativity (Greek, from Dec 12)',
    floor={SAT: D.WineAndOil, SUN: D.WineAndOil}, default_floor=D.Strict,
    cap={SAT: D.WineAndOil, SUN: D.WineAndOil}, default_cap=D.WineAndOil,
    cap_exempt_rank=4)

_BY_LEVEL = {
    FastLevels.NoFast: NO_FAST,
    FastLevels.Fast: ORDINARY,
    FastLevels.LentenFast: LENT,
    FastLevels.DormitionFast: DORMITION,
    FastLevels.ApostlesFast: APOSTLES,
    FastLevels.NativityFast: NATIVITY,
}


# Dates on which GOA grants wine and oil whenever they land on a fast day.
#
# Enumerated from ten years of goarch.org (2026-2035, data/goarch_fasting.json),
# taking every date where their calendar gives wine and oil and this app gives
# strict. Each was observed between one and eight times and is consistent every
# time; the ones inside the Nativity fast are seen most often, because there
# every weekday is a fast day and so every occurrence is visible, while in
# ordinary time only Wednesdays and Fridays reveal anything.
#
# **This is a list, not a rule, because no rule fits.** These are the saints GOA
# ranks highly enough to relax a fast for, and that ranking is not ours: their
# `feast_level` here runs 0, 2, 3 and 4, so no threshold selects them --
# St Barbara and St Ignatius are level 0, while plenty of level 4 days get
# nothing. That is the same reason Ch. 33's rank grants failed against this
# data; see docs/fasting-refactor-scope.md.
#
# It lives here rather than in the fixture because a `greek` Day row replaces
# the `common` one outright (`_prefer_tradition_days` keys on
# `(pdist, month, day)`), so encoding it as data would mean duplicating 38
# feast names and ranks that would then drift out of step with their originals.
#
# Incomplete by construction: a date reaches a Wednesday or Friday in roughly
# two years out of seven, so ordinary-time entries seen once or twice here are
# real but the list as a whole is a floor, not a census.
GREEK_WINE_OIL_DATES = frozenset({
    (1, 11), (1, 14), (1, 16), (1, 18), (1, 22), (1, 25), (1, 27),
    (2, 8), (2, 10), (2, 11), (2, 17), (2, 24),
    (3, 9),
    (6, 8), (6, 11), (6, 30),
    (5, 11),
    (7, 1), (7, 2), (7, 8), (7, 17), (7, 22), (7, 25), (7, 26), (7, 27),
    (8, 31),
    (9, 6), (9, 9), (9, 20),
    (10, 1), (10, 23),
    (11, 1), (11, 12),
    (12, 4), (12, 5), (12, 9), (12, 12), (12, 15), (12, 17), (12, 20),
})


# Chapter X: "Fish is permitted on Wednesday or Friday if it is a feast of the
# Lord even during fasting seasons." GOA applies that as a *cap* -- a saint's
# fish grant falls back to wine and oil when it lands on a Wednesday or Friday,
# however highly ranked the saint. Ten years of data give fourteen such saints,
# at feast levels 4, 5 and 6: Anthony the Great, Euthymius, the Three Hierarchs,
# John the Theologian (twice a year), Constantine and Helen, Elijah, Thomas,
# Demetrius, the Archangel Michael, Chrysostom, Matthew, Andrew and Nicholas.
#
# Note GOA does *not* honour Chapter X's "or one of the 12 Apostles" clause:
# John the Theologian, Thomas, Matthew and Andrew are all capped.
#
# `cap_exempt_rank=7` lets the fixed Lord and Theotokos feasts through, since
# levels 7 and 8 are exactly "Major feast Theotokos" and "Major feast Lord".
# Three Lord-feast days our data ranks lower need naming explicitly.
GREEK_WED_FRI_FISH_OK_DATES = frozenset({
    (1, 7),         # Synaxis of the Forerunner, in Theophany's afterfeast
    # Two apostles that do keep fish, against the general rule above. Both sit
    # on a fast boundary -- Peter and Paul closes the Apostles' fast, Philip is
    # the eve of the Nativity fast -- which is the likeliest reason, though two
    # feasts cannot establish it. Three Wednesday/Friday observations each,
    # fish every time.
    (6, 29),        # Holy Apostles Peter and Paul
})

# St Philip is the same case as Peter and Paul, but needs a grant rather than a
# cap exemption: our row for him claims only wine and oil, so there is no fish
# for an exemption to protect. Three Wednesday/Friday observations, fish each
# time -- he is the eve of the Nativity fast.
GREEK_FISH_DATES = frozenset({
    (11, 14),       # Holy Apostle Philip
})
GREEK_WED_FRI_FISH_OK_PDISTS = frozenset({
    24,             # Midfeast of Pentecost
    38,             # Leavetaking of Pascha / Forefeast of the Ascension
})

# Cheesefare week needs its own season purely so ORDINARY_GREEK's Wednesday and
# Friday cap does not reach it. That cap means "no fish for a saint"; the week
# before Lent is a different thing entirely -- a season-wide dispensation in
# which meat is the only thing given up -- and clamping it to wine and oil
# turned all seven days into a fast stricter than the week they precede.
# goarch.org marks the whole week `fast-day`, Wednesday and Friday included.
CHEESEFARE_GREEK = Season('Cheesefare (Greek)', default_floor=D.MeatFast)

# The mirror of GREEK_WINE_OIL_DATES: dates whose festal wine-and-oil grant GOA
# does not recognise, so the season's own floor should stand instead. Chiefly
# the Beheading of the Forerunner, which our data relaxes to wine and oil but
# which goarch.org keeps strict on all five weekdays -- seven observations,
# never once relaxed. The claim is dropped rather than capped, so the weekend
# floor still applies and the Beheading is wine and oil on a Saturday or Sunday,
# which is exactly what GOA does.
GREEK_STRICT_DATES = frozenset({
    (2, 9), (4, 7), (4, 23), (8, 16), (8, 29),
    (9, 12), (9, 24), (9, 28), (10, 9),
})

ORDINARY_GREEK = Season('ordinary Wed/Fri (Greek)',
                        floor={SAT: D.WineAndOil, SUN: D.WineAndOil},
                        default_floor=D.Strict,
                        cap={WED: D.WineAndOil, FRI: D.WineAndOil},
                        cap_exempt_rank=7)


def slavic_season(day):
    return _BY_LEVEL.get(day.fast_level)


def greek_season(day):
    if day.fast_level == FastLevels.Fast:
        # Cheesefare week: Clean Monday is pdist -48, so the week runs -55..-49.
        if -55 <= day.pdist <= -49:
            return CHEESEFARE_GREEK
        return ORDINARY_GREEK
    if day.fast_level == FastLevels.ApostlesFast:
        return APOSTLES_GREEK
    if day.fast_level == FastLevels.NativityFast:
        # Dec 12 is `nativity - 13`; see NATIVITY_GREEK_EARLY for the citation.
        return (NATIVITY_GREEK_STRICT if day.pdist >= day.pyear.nativity - 13
                else NATIVITY_GREEK_EARLY)
    return _BY_LEVEL.get(day.fast_level)


# --- the rule ---------------------------------------------------------------

def resolve(season, weekday, feast_level, rows, no_fish=False,
            eve_on_weekend=False, cap_exempt=False):
    """Combine a day's contributing rows into (rung, legacy fast_exception)."""
    claims = [(i, RUNG[i]) for i in rows if i not in CLAIMLESS_INDICES]
    caps = [(i, RUNG[i]) for i in rows if i in CAP_INDICES]

    for index, rung in claims:
        if rung is D.FastFree:              # a fast-free row ends the question
            return D.FastFree, index

    allowance = season.floor_for(weekday)
    winner = None                           # the row that set the current answer
    season_cap = (D.FastFree if cap_exempt
                  else season.cap_for(weekday, feast_level))

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

    if no_fish:
        allowance = min(allowance, D.WineAndOil)
        winner = None
    if eve_on_weekend and weekday in (SAT, SUN) and allowance < D.WineAndOil:
        allowance, winner = D.WineAndOil, None

    return allowance, (winner if winner is not None else CANONICAL[allowance])


def apply(day, season_for, wine_oil_dates=frozenset(), fish_dates=frozenset(),
          fish_ok_dates=frozenset(), fish_ok_pdists=frozenset(),
          strict_dates=frozenset()):
    """Set `day.fast_level` and `day.fast_exception` for one day."""
    if (day.month, day.day) in strict_dates:
        # Where the jurisdiction recognises no relaxation, the *festal* claim is
        # dropped and the season's floor stands. Only festal rows are touched:
        # the Paschal cycle's own weekend allowance has to survive, or a Lenten
        # Saturday on one of these dates would come out stricter than the
        # Saturdays either side of it. Caps are kept -- a row asserting
        # strictness still has its say.
        rows = [d.fast_exception
                if not d.month or d.fast_exception in CAP_INDICES else 0
                for d in day.days]
    else:
        rows = [d.fast_exception for d in day.days]

    # A jurisdiction's own fixed-date relaxations enter as an ordinary claim, so
    # the season's cap still applies -- they lift a fast, they do not escape one.
    if (day.month, day.day) in wine_oil_dates:
        rows.append(1)
    if (day.month, day.day) in fish_dates:
        rows.append(2)

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

    cap_exempt = ((day.month, day.day) in fish_ok_dates
                  or (day.month, day.day) in fish_dates
                  or day.pdist in fish_ok_pdists)

    _, day.fast_exception = resolve(
        season, day.weekday, day.feast_level, rows,
        no_fish=no_fish, eve_on_weekend=eve, cap_exempt=cap_exempt)
