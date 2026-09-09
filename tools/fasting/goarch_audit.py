"""Score the Greek fasting rules against goarch.org's published calendar.

    docker compose run --rm local python tools/fasting/goarch_audit.py

Reads data/goarch_fasting.json, which holds GOA's own daily fasting
designations, and compares them to what this app serves for
`Tradition.Greek`. Last run 2026-09-09: **257/276, 93.1%**.

Harvesting more months, when it is needed
-----------------------------------------
goarch.org sits behind Cloudflare and returns 403 to every scripted fetch, so
this cannot be automated. The route that works, and it is cheap:

  1. Open `https://www.goarch.org/chapel/calendar?month=M&year=YYYY
     &viewStyle=GridView&viewType=ViewReadings` in a real browser and let the
     user clear the interstitial once.
  2. From inside that page, `fetch()` further months same-origin -- the
     clearance cookie is inherited, so one manual step buys a whole session.

**The fasting level is not in the page text.** It is a CSS class on `div.day`,
which is why an earlier note claiming the grid's innerText carries the fasting
lines was wrong -- that is true of the readings, not of the fast:

    strict-fast   -> strict            grapes  -> wine and oil
    fasting-fish  -> fish, wine, oil   (none)  -> fast free
    fast-day      -> dairy allowed, i.e. a meat fast

`fast-day` is the trap in that list: it names the *mildest* level, not a fast
day in the ordinary sense, and it appears only in Cheesefare week. Reading it as
anything else silently mis-scores seven days a year.

The mapping is confirmed by March 2026, where Lenten weekdays come out
`strict-fast`, weekends `grapes`, and the Annunciation `fasting-fish`.

GOA's page publishes four buckets where `DietaryAllowance` has seven, so the
comparison is made at their granularity; `bucket()` below is the projection.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])

import asyncio
import collections
import datetime
import json

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orthocal.settings')
django.setup()

from calendarium.datetools import (                  # noqa: E402
    DietaryAllowance as D, FastLevels, Tradition,
    FAST_EXCEPTION_TO_DIETARY_ALLOWANCE as RUNG,
)
from calendarium.liturgics import Day                # noqa: E402

PATH = 'data/goarch_fasting.json'
CODE = {'S': 'strict', 'W': 'wine+oil', 'F': 'fish', 'D': 'meat fast',
        'N': 'no fast'}
WEEKDAYS = ('Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat')
SEASONS = {0: 'no fast', 1: 'ordinary', 2: 'Lent', 3: 'Apostles',
           4: 'Dormition', 5: 'Nativity'}


def bucket(rung):
    """Project a DietaryAllowance onto the five buckets GOA publishes.

    Only `FastFree` is "no fast": `MeatFast` is Cheesefare week's dairy
    allowance, which GOA labels separately. Collapsing the two scored all 21
    Cheesefare days in the harvest as differences when the app had them right.

    `WineOnly` -- Holy Saturday's wine without oil -- has no GOA counterpart,
    and is scored as strict because that is the nearer of the two.
    """
    if rung >= D.FastFree:
        return 'no fast'
    if rung >= D.MeatFast:
        return 'meat fast'
    if rung >= D.FishWineOil:
        return 'fish'
    if rung >= D.WineAndOil:
        return 'wine+oil'
    return 'strict'


async def main():
    with open(PATH) as f:
        goa = json.load(f)

    agree = total = 0
    differences = []
    for month, codes in sorted(goa.items()):
        if month.startswith('_'):
            continue
        year, mon = (int(x) for x in month.split('-'))
        for index, code in enumerate(codes):
            date = datetime.date(year, mon, index + 1)
            day = Day(year, mon, date.day, tradition=Tradition.Greek)
            await day.ainitialize()

            ours = ('no fast' if day.fast_level == FastLevels.NoFast
                    else bucket(RUNG[day.fast_exception]))
            total += 1
            if ours == CODE[code]:
                agree += 1
            else:
                differences.append((date, WEEKDAYS[int(day.weekday)], ours,
                                    CODE[code], day.feast_level, day.fast_level))

    print(f'\n  app (Greek) vs goarch.org: {agree}/{total} '
          f'({100 * agree / total:.1f}%)\n')
    for (ours, theirs), n in collections.Counter(
            (d[2], d[3]) for d in differences).most_common():
        print(f'    ours={ours:<9} GOA={theirs:<9} {n}')
    print()
    for season, n in collections.Counter(
            SEASONS.get(d[5], d[5]) for d in differences).most_common():
        print(f'    {season:<10} {n}')
    print('\n  differences:')
    for date, weekday, ours, theirs, feast_level, _ in differences:
        print(f'    {date} {weekday:<4} feast{feast_level} '
              f'ours={ours:<9} GOA={theirs}')


if __name__ == '__main__':
    asyncio.run(main())
