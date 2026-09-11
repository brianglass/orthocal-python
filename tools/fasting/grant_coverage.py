"""How much of the Greek fixed-date grant list the harvest can actually see.

    docker compose run --rm local python tools/fasting/grant_coverage.py

The grant list in the fixture -- sparse `greek` `Day` rows overriding
`fast_exception` -- was derived from goarch.org, and a date can only enter it if
the harvest ever caught it relaxed. So the obvious worry is that the list is
incomplete: a grant on a date that never surfaced would be invisible and
untestable.

This measures that worry instead of assuming it. **Last run 2026-09-11: the
list is complete with respect to the ten years harvested.**

The measurement has to be made against the *season*, not against the app's
output. Asking "where does the app say strict?" is circular -- a granted date no
longer says strict, so every grant would look like a gap. A grant leaves a trace
only where the season's own floor is strict *and* its cap would let a claim
reach wine and oil; anywhere else the answer is the same with or without it.
Those occurrences are the probes below.

Two structural blind spots fall out, and neither is a real gap:

  * **Dec 25 - Jan 4 and Jan 6** are fast-free, so no grant can exist there.
  * **Aug 1-14**, the Dormition fast, caps claims below rank 7 to strict, so a
    grant there would be invisible. Checked directly against goarch.org rather
    than left as an unknown: across ten years its Dormition weekdays are strict
    93 times and fish 7, and all seven are Aug 6, the Transfiguration, which the
    shared data already grants.

What would extend the list is more years, which buys more probes for the dates
currently probed once or twice. `tools/fasting/goarch_audit.py` documents the
harvest route.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])

import calendar
import collections
import datetime
import json

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orthocal.settings')
django.setup()

from calendarium import fasting                      # noqa: E402
from calendarium.datetools import (                  # noqa: E402
    DietaryAllowance as D, FastLevels, Tradition,
)
from calendarium.liturgics import Day                # noqa: E402

GOARCH = 'data/goarch_fasting.json'
CODES = {'S': 'strict', 'W': 'wine+oil', 'F': 'fish', 'D': 'meat fast',
         'N': 'fast free'}


def years(goa):
    return sorted({int(k[:4]) for k in goa if not k.startswith('_')})


def main():
    with open(GOARCH) as f:
        goa = json.load(f)
    span = [y for y in years(goa) if all(f'{y}-{m:02d}' in goa for m in range(1, 13))]

    probes = collections.Counter()
    for year in span:
        date = datetime.date(year, 1, 1)
        while date.year == year:
            day = Day(year, date.month, date.day, tradition=Tradition.Greek)
            day.initialize()
            season = fasting.greek_season(day)
            if season is not None and day.fast_level != FastLevels.NoFast:
                floor = season.floor_for(day.weekday)
                cap = season.cap_for(day.weekday, day.feast_level)
                if floor <= D.Strict and cap >= D.WineAndOil:
                    probes[(date.month, date.day)] += 1
            date += datetime.timedelta(days=1)

    all_dates = [(m, d) for m in range(1, 13)
                 for d in range(1, calendar.monthrange(2028, m)[1] + 1)]
    never = [md for md in all_dates if probes[md] == 0]
    thin = [md for md in all_dates if probes[md] == 1]

    print(f'\n  {len(span)} full years harvested: {span[0]}-{span[-1]}\n')
    print(f'    dates probed 2+ times : {len(all_dates) - len(never) - len(thin)}')
    print(f'    probed once           : {len(thin)}')
    print(f'    never probed          : {len(never)}')

    print('\n  never probed (a grant here would leave no trace):')
    for md in never:
        print(f'    {md[0]:02d}-{md[1]:02d}')

    # The Dormition blind spot, checked rather than assumed.
    tally = collections.Counter()
    for year in span:
        codes = goa.get(f'{year}-08')
        for day_of_month in range(1, 15):
            date = datetime.date(year, 8, day_of_month)
            if date.weekday() > 4:          # weekends already take wine and oil
                continue
            tally[CODES[codes[day_of_month - 1]]] += 1
    print(f'\n  goarch.org on Dormition weekdays across {len(span)} years: {dict(tally)}')


if __name__ == '__main__':
    main()
