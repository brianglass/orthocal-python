"""Audit every app reading against oca.org, across all services.

    docker compose run --rm local python tools/oca/audit_daily.py 2026

The counterpart to audit_readings.py, which compares only the Liturgy Epistle
and Gospel -- 894 of 1,446 readings a year, leaving 38% unmeasured. This uses
data/oca_raw/daily-YYYY.json (see harvest_daily.py), where both sides carry the
whole day, so the comparison is symmetric: no restriction is needed on the
"extra" direction the way audit_readings.py needs one.

That symmetry is the point. The open question in docs/oca-audit.md -- whether
the ordinary daily reading coexists with a proper one -- lives on feast days
thick with Vespers, Matins and Hours, and the Liturgy-only audit is blind
there. Theophany Eve renders 32 readings in the app and 34 on oca.org, of which
the older audit compared two.

Matching is on citations, never on service labels: neither side names the
service consistently (Holy Week's Bridegroom gospels are "(Matins)" to oca.org
and source "Gospel" here). See docs/oca-audit.md.

Writes data/oca_daily_diff-YYYY.json.
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

from tools.oca.refs import canon, near               # noqa: E402


def match(ours, theirs):
    """Pair two citation lists by near(); return what is left over on each side."""
    leftover_theirs, pool = [], list(ours)
    for t in theirs:
        hit = next((o for o in pool if near(o, t)), None)
        if hit is None:
            leftover_theirs.append(t)
        else:
            pool.remove(hit)
    return pool, leftover_theirs


async def audit(year, tradition=Tradition.Slavic):
    with open(f'data/oca_raw/daily-{year}.json') as f:
        oca = json.load(f)

    diffs, clean, checked = [], 0, 0
    counts = collections.Counter()
    date = datetime.date(year, 1, 1)
    while date.year == year:
        theirs = [c for c in (canon(x) for x in oca.get(date.isoformat(), [])) if c]
        if not theirs:
            date += datetime.timedelta(days=1)
            continue

        day = Day(date.year, date.month, date.day, tradition=tradition)
        await day.ainitialize()
        readings = await day.aget_readings()
        ours = [c for c in (canon(r.pericope.display) for r in readings) if c]

        extra, missing = match(ours, theirs)
        checked += 1
        counts['app'] += len(ours)
        counts['oca'] += len(theirs)
        if extra or missing:
            diffs.append({'date': date.isoformat(), 'missing': missing, 'extra': extra})
        else:
            clean += 1
        date += datetime.timedelta(days=1)

    path = f'data/oca_daily_diff-{year}.json'
    with open(path, 'w') as f:
        json.dump(diffs, f, indent=1)

    pct = 100.0 * clean / checked if checked else 0.0
    print(f'{year}: {clean}/{checked} dates fully match ({pct:.1f}%), '
          f'{len(diffs)} differ -> {path}')
    print(f'  readings compared: app {counts["app"]}, oca.org {counts["oca"]}')
    worst = sorted(diffs, key=lambda d: -(len(d['missing']) + len(d['extra'])))
    for d in worst[:20]:
        print(f"  {d['date']}  missing={len(d['missing']):<3} extra={len(d['extra']):<3}"
              f"  {(d['missing'] + d['extra'])[:5]}")


if __name__ == '__main__':
    for year in (sys.argv[1:] or ['2026']):
        asyncio.run(audit(int(year)))
