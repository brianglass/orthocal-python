"""A mock-up of the explicit fasting model, measured against current behaviour.

    docker compose run --rm local python tools/fasting/prototype.py

**Nothing here is wired into the app.** This exists so the shape can be looked
at, and so the claim "it reproduces what we do today" can be checked rather than
asserted. It resolves every day the characterisation test pins and compares its
answer to the live one at the *dietary rung* -- what a reader actually eats --
rather than at the legacy index.

The idea is to stop using `max()` over an integer that means three different
things, and say the rule out loud instead:

    a SEASON gives a floor per weekday, and a cap on how far a claim may lift it
    a DATA ROW either CLAIMS a rung ("this date allows wine and oil") or
        CAPS one ("this day is strict whatever else falls on it")
    a RANK RULE may grant more, where a source states one
    the answer is the most lenient claim, with every cap applied

The claim/cap split is the piece the legacy integer hides. Holy Saturday allows
wine but *not* oil -- "on this one Saturday, alone among Saturdays of the year,
olive oil is not permitted" -- so it has to beat a saint's wine-and-oil claim
rather than lose to it, which most-lenient-wins alone gets wrong.

Sources for each season's numbers are in docs/fasting-refactor-scope.md.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])

import asyncio
import collections
import datetime
from dataclasses import dataclass, field

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orthocal.settings')
django.setup()

from calendarium.datetools import (                  # noqa: E402
    DietaryAllowance as D, FastLevels, Tradition, Weekday,
    FAST_EXCEPTION_TO_DIETARY_ALLOWANCE as RUNG,
)
from calendarium.liturgics import Day                # noqa: E402

SUN, MON, TUE, WED, THU, FRI, SAT = (Weekday.Sunday, Weekday.Monday, Weekday.Tuesday,
                                     Weekday.Wednesday, Weekday.Thursday,
                                     Weekday.Friday, Weekday.Saturday)
WEEKEND = (SAT, SUN)


@dataclass(frozen=True)
class Grant:
    """A rank rule: a saint of `min_rank` on these weekdays may eat `rung`."""
    min_rank: int
    weekdays: tuple
    rung: D


@dataclass(frozen=True)
class Season:
    name: str
    # What the season allows before any commemoration is considered.
    floor: dict = field(default_factory=dict)
    default_floor: D = D.Strict
    # How far a data row's claim may lift the floor, and the rank that escapes
    # the cap. Per weekday where a season needs it.
    cap: dict = field(default_factory=dict)
    default_cap: D = D.FastFree
    cap_exempt_rank: int = 99
    grants: tuple = ()

    def floor_for(self, weekday):
        return self.floor.get(weekday, self.default_floor)

    def cap_for(self, weekday, feast_level):
        if feast_level >= self.cap_exempt_rank:
            return D.FastFree
        return self.cap.get(weekday, self.default_cap)


# --- the seasons, with their sources ---------------------------------------

ORDINARY = Season('ordinary Wed/Fri', default_floor=D.Strict)

# Ware, via OCA: weekdays strict, weekend wine and oil (which the data supplies),
# fish only on the Annunciation and Palm Sunday -- ranks 7 and 8. The cap is the
# highest rung that is still fishless, so Lazarus Saturday keeps its caviar.
LENT = Season('Great Lent', default_floor=D.Strict,
              default_cap=D.WineAndOil, cap_exempt_rank=7)

# OCA: "wine and oil are allowed only on Saturdays and Sundays (and sometimes
# on a few feast days and vigils)" -- the Transfiguration, rank 8.
DORMITION = Season('Dormition', floor={SAT: D.WineAndOil, SUN: D.WineAndOil},
                   default_floor=D.Strict,
                   default_cap=D.Strict, cap_exempt_rank=7)

# Typikon Ch. 33: Mon/Wed/Fri strict, Tue/Thu wine and oil, Sat/Sun fish.
_CH33_FLOOR = {MON: D.Strict, TUE: D.WineAndOil, WED: D.Strict,
               THU: D.WineAndOil, FRI: D.Strict,
               SAT: D.FishWineOil, SUN: D.FishWineOil}
# Ch. 33's rank clause. NOT currently implemented by the app -- switch on to see
# what it would change.
_CH33_GRANTS = (
    Grant(min_rank=3, weekdays=(MON, TUE, THU), rung=D.FishWineOil),
    Grant(min_rank=3, weekdays=(WED, FRI), rung=D.WineAndOil),
    Grant(min_rank=5, weekdays=(WED, FRI), rung=D.FishWineOil),
)
APOSTLES = Season('Apostles', floor=_CH33_FLOOR,
                  cap={WED: D.WineAndOil, FRI: D.WineAndOil,
                       SAT: D.FishWineOil, SUN: D.FishWineOil},
                  cap_exempt_rank=4)
NATIVITY = Season('Nativity', floor=_CH33_FLOOR,
                  cap={WED: D.WineAndOil, FRI: D.WineAndOil,
                       SAT: D.FishWineOil, SUN: D.FishWineOil},
                  cap_exempt_rank=4)

SEASONS = {
    FastLevels.NoFast: None,
    FastLevels.Fast: ORDINARY,
    FastLevels.LentenFast: LENT,
    FastLevels.DormitionFast: DORMITION,
    FastLevels.ApostlesFast: APOSTLES,
    FastLevels.NativityFast: NATIVITY,
}


def resolve(season, weekday, feast_level, claims, caps,
            windows=(), use_rank_grants=False):
    """The whole combination rule, in one readable pass."""
    if D.FastFree in claims:            # a fast-free row ends the question
        return D.FastFree
    if season is None:
        return D.FastFree

    allowance = season.floor_for(weekday)
    season_cap = season.cap_for(weekday, feast_level)
    for claim in claims:
        # A season cap means "no fish". Caviar is not fish -- dietarily
        # WineOilCaviar excludes exactly what WineAndOil does -- so a caviar
        # claim survives a wine-and-oil cap instead of being clamped below it.
        clamped = claim if (claim == D.WineOilCaviar and season_cap >= D.WineAndOil) \
            else min(claim, season_cap)
        allowance = max(allowance, clamped)
    if use_rank_grants:
        for grant in season.grants:
            if feast_level >= grant.min_rank and weekday in grant.weekdays:
                allowance = max(allowance, grant.rung)

    for cap in caps:                    # a row asserting strictness wins
        allowance = min(allowance, cap)

    for window in windows:              # season-specific dated rules
        allowance = window(allowance, weekday, feast_level)
    return allowance


# --- the dated windows the sources also state ------------------------------

def no_fish_before_nativity(allowance, weekday, feast_level):
    """Ch. 33: 'from the 20th of December until the 25th, even if it be
    Saturday or Sunday, we do not allow fish.'"""
    return min(allowance, D.WineAndOil)


def eve_on_weekend(allowance, weekday, feast_level):
    """The eves of Nativity and Theophany are wine-and-oil days on a weekend."""
    return max(allowance, D.WineAndOil) if weekday in WEEKEND else allowance


async def main():
    matches = collections.Counter()
    mismatches = collections.Counter()
    examples = collections.defaultdict(list)

    for tradition, tname in ((Tradition.Slavic, 'slavic'),):
        for year in (2025, 2026, 2027, 2028, 2029):
            date = datetime.date(year, 1, 1)
            while date.year == year:
                day = Day(date.year, date.month, date.day, tradition=tradition)
                await day.ainitialize()

                raw = [d.fast_exception for d in day.days]
                # 0 makes no claim. 5, 9 and 10 assert strictness rather than
                # leniency -- Holy Saturday's wine-without-oil, the strict eves,
                # and Clean Week's "no overrides" -- so they cap rather than
                # claim.
                # 0 makes no claim. 9 and 10 assert strictness only. 5 --
                # Holy Saturday's wine-without-oil -- asserts an *exact* rung:
                # it lifts the strict floor and also forbids the oil a saint's
                # claim would allow, so it is both a claim and a cap.
                claims = [RUNG[e] for e in raw if e not in (0, 9, 10)]
                caps = [RUNG[e] for e in raw if e in (5, 9, 10)]

                season = SEASONS.get(day.fast_level)
                windows = []
                if day.fast_level in (FastLevels.ApostlesFast, FastLevels.NativityFast):
                    if day.pyear.nativity - 6 < day.pdist < day.pyear.nativity - 1:
                        windows.append(no_fish_before_nativity)
                if day.pdist in (day.pyear.nativity - 1, day.pyear.theophany - 1):
                    windows.append(eve_on_weekend)

                got = resolve(season, day.weekday, day.feast_level, claims,
                              caps, windows)
                want = D.FastFree if day.fast_level == FastLevels.NoFast \
                    else RUNG[day.fast_exception]

                key = season.name if season else 'no fast'
                if got == want:
                    matches[key] += 1
                else:
                    mismatches[(key, want.name, got.name)] += 1
                    examples[(key, want.name, got.name)].append(
                        f'{date} {tname} w{day.weekday} feast{day.feast_level} rows={raw}')
                date += datetime.timedelta(days=1)

    total = sum(matches.values()) + sum(mismatches.values())
    print(f'\n  prototype vs current behaviour, slavic, 5 years: '
          f'{sum(matches.values())}/{total} '
          f'({100 * sum(matches.values()) / total:.1f}%)\n')
    print('  by season:')
    for name in ('no fast', 'ordinary Wed/Fri', 'Great Lent', 'Dormition',
                 'Apostles', 'Nativity'):
        ok = matches[name]
        bad = sum(v for k, v in mismatches.items() if k[0] == name)
        if ok or bad:
            print(f'    {name:<18} {ok:>5} match  {bad:>4} differ')
    if mismatches:
        print('\n  differences:')
        for (name, want, got), n in mismatches.most_common():
            print(f'    {name:<18} current={want:<13} prototype={got:<13} ({n})')
            print(f'        e.g. {examples[(name, want, got)][0]}')


if __name__ == '__main__':
    asyncio.run(main())
