"""Audit the abbreviated readings -- what the Alexa skill speaks -- against oca.org.

    docker compose run --rm local python tools/oca/audit_abbreviated.py 2026

oca.org's monthly lectionary is itself an abbreviated-readings list: one
Epistle/Gospel set per row, the labelled (proper) sets first and the ordinary
daily set last. On Aug 29 it prints

    Acts 13:25-33 / Mark 6:14-30  (Forerunner)
    1 Corinthians 2:6-9 / Matthew 22:15-22

so the Forerunner's pair is what a listener should hear. That makes the first
row a ground truth for Day.aget_abbreviated_readings(), which until now had
none -- the selection was tuned by hand and never measured.

Reports three outcomes per date:

  match    our pair is oca.org's first pair
  ordered  our pair is one of oca.org's *later* pairs -- we picked a real
           reading set, but not the one it leads with. This is the Alexa
           failure mode: the ordinary weekday lesson read on a feast.
  differ   our pair is not any of oca.org's sets

Writes data/oca_abbrev_diff-YYYY.json.
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

from calendarium.datetools import Tradition          # noqa: E402
from calendarium.liturgics import Day                # noqa: E402

from tools.oca.refs import canon, near, slot         # noqa: E402


def pairs(rows):
    """oca.org's rows as (epistle, gospel) token pairs, in the order printed."""
    out = []
    for row in rows:
        e = g = None
        for citation in row['citations']:
            token = canon(citation)
            kind = slot(token)
            if kind == 'Epistle' and e is None:
                e = token
            elif kind == 'Gospel' and g is None:
                g = token
        if e or g:
            out.append((e, g, row['label']))
    return out


def same(ours, theirs):
    (oe, og), (te, tg, _) = ours, theirs
    return ((oe is None and te is None) or near(oe or '', te or '')) and \
           ((og is None and tg is None) or near(og or '', tg or ''))


async def audit(year, tradition=Tradition.Slavic):
    with open(f'data/oca_raw/readings-{year}.json') as f:
        monthly = json.load(f)

    tally = collections.Counter()
    problems = []
    date = datetime.date(year, 1, 1)
    while date.year == year:
        theirs = pairs(monthly.get(date.isoformat(), []))
        if not theirs:
            date += datetime.timedelta(days=1)
            continue

        day = Day(date.year, date.month, date.day, tradition=tradition)
        await day.ainitialize()
        abbr = await day.aget_abbreviated_readings()
        ours = (next((canon(r.pericope.display) for r in abbr if r.source == 'Epistle'), None),
                next((canon(r.pericope.display) for r in abbr if r.source == 'Gospel'), None))

        if same(ours, theirs[0]):
            tally['match'] += 1
        else:
            hit = next((i for i, t in enumerate(theirs) if same(ours, t)), None)
            kind = 'ordered' if hit is not None else 'differ'
            tally[kind] += 1
            problems.append({
                'date': date.isoformat(), 'kind': kind,
                'feast_level': day.feast_level,
                'feasts': day.feasts,
                'ours': list(ours),
                'oca_first': list(theirs[0]),
                'oca_all': [list(t) for t in theirs],
            })
        date += datetime.timedelta(days=1)

    path = f'data/oca_abbrev_diff-{year}.json'
    with open(path, 'w') as f:
        json.dump(problems, f, indent=1)

    total = sum(tally.values())
    print(f'{year}: {tally["match"]}/{total} match oca.org\'s leading pair '
          f'({100.0 * tally["match"] / total:.1f}%)')
    print(f'  ordered: {tally["ordered"]}   differ: {tally["differ"]}   -> {path}')
    for p in problems:
        if p['kind'] == 'ordered':
            print(f"  {p['date']} lvl={p['feast_level']:<2} ours={p['ours']} "
                  f"oca leads with {p['oca_first']}  {'; '.join(p['feasts'])[:38]}")


if __name__ == '__main__':
    for year in (sys.argv[1:] or ['2026']):
        asyncio.run(audit(int(year)))
