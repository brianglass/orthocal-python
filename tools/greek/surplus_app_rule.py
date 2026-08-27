"""Does the app's surplus-region output follow the back-anchor extended backward?

The tail b-1/b-2/b-3 = weeks 16/15/14 is proven. The natural extension is
b-4 = 13, b-5 = 12. This checks whether that is in fact what the app already
computes there -- i.e. whether the app is applying a coherent rule that GOA
simply departs from, rather than producing noise.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])

import asyncio, django, re, datetime, collections
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orthocal.settings')
django.setup()
from calendarium.liturgics import GreekYear, Day
from calendarium import datetools

def pd_to_date(Y, pdist):
    j = datetime.date(Y, 1, 1)
    return j + datetime.timedelta(days=datetools.compute_pascha_jdn(Y) - datetools.gregorian_to_jdn(j) + pdist)

# Luke-section table, weeks 12-16, from the GOA labels (see greek_labels.py)
TAIL = {
    12: {0:'Luke 20.27-44', 1:'Luke 21.12-19', 2:'Luke 21.5-8, 10-11, 20-24', 3:'Luke 21.28-33', 4:'Luke 21.37-22.8', 5:'Luke 13.18-29'},
    13: {0:'Mark 8.11-21', 1:'Mark 8.22-26', 2:'Mark 8.30-34', 3:'Mark 9.10-15', 4:'Mark 9.33-41', 5:'Luke 14.1-11'},
    14: {0:'Mark 9.42-10.1', 1:'Mark 10.2-12', 2:'Mark 10.11-16', 3:'Mark 10.17-27', 4:'Mark 10.23-32', 5:'Luke 16.10-15'},
    15: {0:'Mark 10.46-52', 1:'Mark 11.11-23', 2:'Mark 11.22-26', 3:'Mark 11.27-33', 4:'Mark 12.1-12', 5:'Luke 17.3-10'},
    16: {0:'Mark 12.13-17', 1:'Mark 12.18-27', 2:'Mark 12.28-37', 3:'Mark 12.38-44', 4:'Mark 13.1-8', 5:'Luke 18.2-8'},
}

async def main():
    tally = collections.Counter()
    for Y in range(2027, 2100):
        gy = GreekYear(Y)
        if gy.triodion_start < 308:
            continue
        trio = pd_to_date(Y, gy.triodion_start)
        trio_mon = trio + datetime.timedelta(days=1)
        lv = pd_to_date(Y, gy.theophany + 8)
        d = lv + datetime.timedelta(days=1)
        while d < trio:
            b = (d - trio_mon).days // 7
            if d.weekday() != 6 and b <= -4:
                expected_week = 17 + b               # b-4 -> 13, b-5 -> 12
                want = TAIL.get(expected_week, {}).get(d.weekday())
                if want:
                    day = Day(d.year, d.month, d.day, tradition='greek')
                    await day.ainitialize()
                    got = [r.pericope.sdisplay for r in await day.aget_readings() if r.source == 'Gospel']
                    tally['match' if want in got else 'differ'] += 1
                else:
                    tally['week out of table range'] += 1
            d += datetime.timedelta(days=1)
    total = tally['match'] + tally['differ']
    print('Does the app extend the back-anchor backward (b-4 = wk13, b-5 = wk12)?\n')
    for k, v in tally.most_common():
        print(f'  {k:<26} {v}')
    if total:
        print(f'\n  -> {tally["match"]}/{total} = {tally["match"]/total*100:.0f}% of surplus days follow the extended rule')

asyncio.run(main())
