"""Multi-year confirmation for the fixed-date readings the app is missing.

three_way.py found dates in 2026 where goarch.org and antiochian.org agree and
the app differs -- shared bugs rather than jurisdictional ones. Before any of
them becomes a data row this checks the whole harvest: does antiochian.org say
the same thing on that calendar date every year? This project's standard is two
or more independent years (see docs/greek-lectionary.md).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])

import asyncio, django, re, json, glob, datetime, collections
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orthocal.settings')
django.setup()
from calendarium.liturgics import Day
from calendarium.datetools import Tradition

CANDIDATES = [(4, 25), (4, 30), (5, 7), (7, 5), (7, 13), (8, 31), (9, 24), (12, 17)]

raw = {}
for path in sorted(glob.glob('data/antiochian_raw/*.json')):
    d = json.load(open(path))
    dt = datetime.date.fromisoformat(d['originalCalendarDate'])
    raw[dt] = (d.get('feastDayTitle', ''), d.get('reading1Title', ''), d.get('reading2Title', ''))

async def main():
    for month, day in CANDIDATES:
        rows = sorted((dt, v) for dt, v in raw.items() if dt.month == month and dt.day == day)
        eps = collections.Counter(v[1] for _, v in rows)
        gos = collections.Counter(v[2] for _, v in rows)
        title = rows[0][1][0] if rows else '?'
        print(f'\n{month:02d}-{day:02d}  {title[:52]}   ({len(rows)} harvested years: '
              f'{", ".join(str(dt.year) for dt, _ in rows)})')
        for label, counter in (('Epistle', eps), ('Gospel', gos)):
            items = counter.most_common()
            verdict = 'FIXED' if len(items) == 1 else f'varies ({len(items)} values)'
            print(f'    {label:<8} {verdict}')
            for cit, n in items:
                print(f'        {n}x  {cit}')
        # what the app produces on the most recent harvested occurrence
        dt = rows[-1][0]
        pday = Day(dt.year, dt.month, dt.day, tradition=Tradition.Antiochian)
        await pday.ainitialize()
        rs = await pday.aget_readings()
        print(f'    app({dt}): ' + ', '.join(f'{r.source}={r.pericope.sdisplay}' for r in rs))

asyncio.run(main())
