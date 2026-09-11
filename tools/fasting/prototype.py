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

# Set False to see what the Nativity Eve fix changes.
LEGACY = '--fixed' not in sys.argv

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
    # Emulates the bug described in docs/fasting-refactor-scope.md, so the
    # refactor can be proven byte-identical before the fix is made visible.
    # The live code writes the Wednesday/Friday cap as an assignment rather
    # than a clamp, so it raises a strictness assertion instead of only
    # lowering a leniency claim.
    legacy_wed_fri_assignment: bool = False

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
                  cap_exempt_rank=4, legacy_wed_fri_assignment=LEGACY)
NATIVITY = Season('Nativity', floor=_CH33_FLOOR,
                  cap={WED: D.WineAndOil, FRI: D.WineAndOil,
                       SAT: D.FishWineOil, SUN: D.FishWineOil},
                  cap_exempt_rank=4, legacy_wed_fri_assignment=LEGACY)

# Greek practice differs only in the Nativity fast, and there it splits in two.
# See docs/greek-fasting.md: for the first four weeks everything but Wednesday
# and Friday is a fish day, and from Dec 13 the fast tightens further than
# Slavic practice does -- Monday, Tuesday and Thursday drop to full strictness
# rather than merely losing fish.
NATIVITY_GREEK_EARLY = Season(
    'Nativity (Greek, to Dec 12)',
    floor={WED: D.Strict, FRI: D.Strict},
    default_floor=D.FishWineOil,
    cap={WED: D.WineAndOil, FRI: D.WineAndOil},
    default_cap=D.FishWineOil,
    cap_exempt_rank=4, legacy_wed_fri_assignment=LEGACY)
NATIVITY_GREEK_STRICT = Season(
    'Nativity (Greek, from Dec 13)',
    floor={SAT: D.WineAndOil, SUN: D.WineAndOil},
    default_floor=D.Strict,
    # The weekend allowance is unconditional here; the weekday one is not.
    cap={SAT: D.WineAndOil, SUN: D.WineAndOil},
    default_cap=D.WineAndOil,
    cap_exempt_rank=4, legacy_wed_fri_assignment=LEGACY)

SEASONS = {
    FastLevels.NoFast: None,
    FastLevels.Fast: ORDINARY,
    FastLevels.LentenFast: LENT,
    FastLevels.DormitionFast: DORMITION,
    FastLevels.ApostlesFast: APOSTLES,
    FastLevels.NativityFast: NATIVITY,
}


def season_for(day, tradition):
    """The season table governing this day. Only Greek's Nativity fast splits."""
    if (tradition is Tradition.Greek
            and day.fast_level == FastLevels.NativityFast):
        return (NATIVITY_GREEK_STRICT if day.pdist >= day.pyear.nativity - 12
                else NATIVITY_GREEK_EARLY)
    return SEASONS.get(day.fast_level)


# The index to report when the outcome came from the season rather than from a
# particular row: one canonical legacy value per rung.
CANONICAL = {D.Strict: 0, D.WineOnly: 5, D.WineAndOil: 1, D.WineOilCaviar: 6,
             D.FishWineOil: 2, D.MeatFast: 7, D.FastFree: 11}


def resolve(season, weekday, feast_level, rows, windows=(), use_rank_grants=False):
    """The whole combination rule, in one readable pass.

    Returns (rung, legacy_index). The rung is the answer; the index is kept
    only because `fast_exception` is published by the API, and is the winning
    row's own value when a row decided it, or the canonical value for the rung
    when the season did.
    """
    claims = [(i, RUNG[i]) for i in rows if i not in (0, 9, 10)]
    caps = [(i, RUNG[i]) for i in rows if i in (5, 9, 10)]

    for i, rung in claims:
        if rung is D.FastFree:          # a fast-free row ends the question
            return D.FastFree, i
    if season is None:
        return D.FastFree, CANONICAL[D.FastFree]

    allowance = season.floor_for(weekday)
    winner = None                       # the row that set the current answer
    season_cap = season.cap_for(weekday, feast_level)
    for i, claim in claims:
        # A season cap means "no fish". Caviar is not fish -- dietarily
        # WineOilCaviar excludes exactly what WineAndOil does -- so a caviar
        # claim survives a wine-and-oil cap instead of being clamped below it.
        clamped = claim if (claim == D.WineOilCaviar and season_cap >= D.WineAndOil) \
            else min(claim, season_cap)
        if clamped > allowance:
            allowance = clamped
            # A clamped claim no longer speaks for itself; the season does.
            winner = i if clamped == claim else None
    if use_rank_grants:
        for grant in season.grants:
            if feast_level >= grant.min_rank and weekday in grant.weekdays:
                if grant.rung > allowance:
                    allowance, winner = grant.rung, None

    for i, cap in caps:                 # a row asserting strictness wins
        if cap < allowance:
            allowance, winner = cap, i
        elif cap == allowance and winner is None:
            winner = i                  # it agrees, and it has the better label

    index = winner if winner is not None else CANONICAL[allowance]

    if (season.legacy_wed_fri_assignment and weekday in (WED, FRI)
            and feast_level < season.cap_exempt_rank and index > 1):
        allowance, index = D.WineAndOil, 1

    for window in windows:              # season-specific dated rules
        moved = window(allowance, weekday, feast_level)
        if moved != allowance:
            allowance, index = moved, CANONICAL[moved]

    return allowance, index


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
    index_diffs = collections.Counter()
    index_examples = collections.defaultdict(list)

    for tradition, tname in ((Tradition.Slavic, 'slavic'), (Tradition.Greek, 'greek')):
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

                season = season_for(day, tradition)
                windows = []
                if (tradition is Tradition.Slavic
                        and day.fast_level in (FastLevels.ApostlesFast,
                                               FastLevels.NativityFast)
                        and day.pyear.nativity - 6 < day.pdist < day.pyear.nativity - 1):
                    windows.append(no_fish_before_nativity)
                if day.pdist in (day.pyear.nativity - 1, day.pyear.theophany - 1):
                    windows.append(eve_on_weekend)

                got, got_index = resolve(season, day.weekday, day.feast_level,
                                         raw, windows)
                want = D.FastFree if day.fast_level == FastLevels.NoFast \
                    else RUNG[day.fast_exception]
                if day.fast_level != FastLevels.NoFast and got_index != day.fast_exception:
                    index_diffs[(day.fast_exception, got_index)] += 1
                    index_examples[(day.fast_exception, got_index)].append(
                        f'{date} {tname} rows={raw} feast{day.feast_level}')

                key = f'{tname} {season.name}' if season else f'{tname} no fast'
                if got == want:
                    matches[key] += 1
                else:
                    mismatches[(key, want.name, got.name)] += 1
                    examples[(key, want.name, got.name)].append(
                        f'{date} {tname} w{day.weekday} feast{day.feast_level} rows={raw}')
                date += datetime.timedelta(days=1)

    total = sum(matches.values()) + sum(mismatches.values())
    print(f'\n  prototype vs current behaviour, both traditions, 5 years: '
          f'{sum(matches.values())}/{total} '
          f'({100 * sum(matches.values()) / total:.1f}%)\n')
    print('  by season:')
    for name in sorted(set(matches) | {k[0] for k in mismatches}):
        ok = matches[name]
        bad = sum(v for k, v in mismatches.items() if k[0] == name)
        flag = '' if not bad else '   <--'
        print(f'    {name:<34} {ok:>5} match  {bad:>4} differ{flag}')
    print(f"\n  legacy fast_exception index reproduced exactly: "
          f"{'yes' if not index_diffs else 'NO'}")
    for (want_i, got_i), n in index_diffs.most_common(10):
        print(f'    current exc={want_i} -> prototype exc={got_i}  ({n} days)'
              f'  e.g. {index_examples[(want_i, got_i)][0]}')
    if mismatches:
        print('\n  differences:')
        for (name, want, got), n in mismatches.most_common():
            print(f'    {name:<34} current={want:<13} prototype={got:<13} ({n})')
            print(f'        e.g. {examples[(name, want, got)][0]}')


if __name__ == '__main__':
    asyncio.run(main())
