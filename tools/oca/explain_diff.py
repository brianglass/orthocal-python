"""Print the app's and oca.org's full readings side by side for given dates.

    docker compose run --rm local python tools/oca/explain_diff.py 2026-01-01 ...
    docker compose run --rm local python tools/oca/explain_diff.py --all 2026

audit_readings.py reports which citations differ; this shows the whole day on
both sides, with our `source`/`desc` and oca.org's labels, which is what it
takes to tell a real gap from a difference in how a day is decomposed.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])

import asyncio
import datetime
import json

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orthocal.settings')
django.setup()

from calendarium.datetools import Tradition          # noqa: E402
from calendarium.liturgics import Day                # noqa: E402


async def show(datestr):
    date = datetime.date.fromisoformat(datestr)
    with open(f'data/oca_raw/readings-{date.year}.json') as f:
        oca = json.load(f)

    day = Day(date.year, date.month, date.day, tradition=Tradition.Slavic)
    await day.ainitialize()
    readings = await day.aget_readings()

    print(f'\n=== {datestr} ({date:%A}) ===')
    print(f'  app titles : {"; ".join(day.titles) or "-"}')
    print(f'  app feasts : {"; ".join(day.feasts) or "-"}')
    print('  app readings:')
    for r in readings:
        desc = f' [{r.desc}]' if r.desc else ''
        print(f'      {r.source:<16} {r.pericope.display}{desc}')
    print('  oca.org:')
    for row in oca.get(datestr, []):
        label = f' ({row["label"]})' if row['label'] else ''
        print(f'      {" / ".join(row["citations"])}{label}')


async def main(args):
    if args and args[0] == '--all':
        year = int(args[1])
        with open(f'data/oca_readings_diff-{year}.json') as f:
            dates = [d['date'] for d in json.load(f)]
    else:
        dates = args
    for d in dates:
        await show(d)


if __name__ == '__main__':
    asyncio.run(main(sys.argv[1:]))
