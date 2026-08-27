"""Classify the shared bugs: fixed-Menaion reading, or moveable-cycle difference?

three_way.py lists dates where goarch.org and antiochian.org agree and the app
differs from both. They need different fixes, and grouping by calendar date
alone conflates them -- a date can carry a fixed saint one year and a moveable
feast the next. This groups by what actually falls on the date each year.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])

import asyncio, django, re, json, glob, datetime, collections
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orthocal.settings')
django.setup()
from calendarium.liturgics import Day
from calendarium.datetools import Tradition

SHARED = [(4, 10), (4, 25), (4, 30), (5, 7), (7, 5), (7, 13), (8, 31), (9, 24), (12, 17)]

raw = {}
for path in sorted(glob.glob('data/antiochian_raw/*.json')):
    d = json.load(open(path))
    dt = datetime.date.fromisoformat(d['originalCalendarDate'])
    raw[dt] = (d.get('feastDayTitle', ''), d.get('reading1Title', ''), d.get('reading2Title', ''))

def short(c, n=30):
    return (c or '')[:n]

async def main():
    for month, day in SHARED:
        rows = sorted((dt, v) for dt, v in raw.items() if dt.month == month and dt.day == day)
        titles = collections.Counter(v[0] for _, v in rows)
        fixed = len(titles) == 1
        print(f'\n=== {month:02d}-{day:02d} === {"FIXED commemoration" if fixed else "title VARIES by year"}')
        for t, n in titles.most_common():
            print(f'    {n}x {t[:64]}')
        # readings, but only for the years carrying the dominant title
        dominant = titles.most_common(1)[0][0]
        same = [(dt, v) for dt, v in rows if v[0] == dominant]
        eps = collections.Counter(v[1] for _, v in same)
        gos = collections.Counter(v[2] for _, v in same)
        for label, counter in (('Epistle', eps), ('Gospel', gos)):
            items = counter.most_common()
            print(f'    {label:<8} {"CONSISTENT" if len(items) == 1 else f"varies ({len(items)})"}'
                  f'  across {len(same)} years with that title')
            for cit, n in items:
                print(f'        {n}x {short(cit, 58)}')
        dt = same[-1][0]
        pday = Day(dt.year, dt.month, dt.day, tradition=Tradition.Greek)
        await pday.ainitialize()
        rs = await pday.aget_readings()
        got = ', '.join(f'{r.source}={r.pericope.sdisplay}' for r in rs
                        if r.source in ('Epistle', 'Gospel'))
        print(f'    app({dt}): {got}')

asyncio.run(main())
