"""Audit the app's Slavic Liturgy readings against oca.org, a full year at a time.

    docker compose run --rm local python tools/oca/audit_readings.py 2026

The Slavic data has been in this app since long before the Greek tradition was
added, and until now it had never been measured against its own source the way
Greek was measured against goarch.org. This is that measurement.

Scope is the Liturgy Epistle and Gospel. The harvested pages also carry Vespers
Old Testament lessons in the Lenten months, but not consistently across the
year, so OT citations are counted and reported separately rather than audited
-- a clean report here says nothing about Vespers, Matins or the Hours.

Comparison is set-based per date and classified by book, never positional. See
harvest_readings.py for why position is unusable, and refs.slot() for the
classification. oca.org lists a date's reading sets in its own order with
free-text labels, so the only reliable question is whether the same citations
are present. A date passes when every OCA citation has a near() match among the
app's and vice versa.

Writes data/oca_readings_diff-YYYY.json with every mismatch for follow-up.
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

from tools.oca.refs import canon, near, slot         # noqa: E402


# Slot is deliberately NOT used to pair readings up. Neither side is
# self-consistent about it: oca.org labels Holy Week's Bridegroom gospels
# "(Matins)" while the app files those same readings under source "Gospel", and
# the app splits Theophany Eve across Hours, Vespers and Blessing of Waters
# where oca.org prints two rows. Matching by slot invented differences on
# precisely the hardest days -- it moved the score the wrong way and flagged
# readings both sides plainly had. Match on the citation, and report the two
# directions separately, which is what actually needs fixing:
#
#   missing -- oca.org lists it, the app has it nowhere. A real gap.
#   extra   -- the app shows it as an Epistle or Gospel, oca.org lists nothing
#              like it. Restricted to those two sources so the app's much
#              fuller Vespers/Hours data is not counted against it.


def match(ours, theirs):
    """Pair up two citation lists by near(); return what is left over."""
    unmatched_theirs, pool = [], list(ours)
    for t in theirs:
        hit = next((o for o in pool if near(o, t)), None)
        if hit is None:
            unmatched_theirs.append(t)
        else:
            pool.remove(hit)
    return pool, unmatched_theirs       # ours-only, theirs-only


async def audit(year):
    with open(f'data/oca_raw/readings-{year}.json') as f:
        oca = json.load(f)

    diffs = []
    checked = clean = ot_only = 0
    date = datetime.date(year, 1, 1)
    while date.year == year:
        rows = oca.get(date.isoformat())
        if not rows:
            date += datetime.timedelta(days=1)
            continue

        day = Day(date.year, date.month, date.day, tradition=Tradition.Slavic)
        await day.ainitialize()
        readings = await day.aget_readings()

        all_ours = [canon(r.pericope.display) for r in readings]
        liturgy_ours = [canon(r.pericope.display) for r in readings
                        if r.source in ('Epistle', 'Gospel')]
        theirs = [canon(c) for row in rows for c in row['citations']]
        theirs = [t for t in theirs if t]

        # A day whose only OCA content is Old Testament is a Lenten Vespers day
        # with no Liturgy. Out of scope rather than a mismatch.
        if theirs and all(slot(t) == 'OT' for t in theirs):
            ot_only += 1
            date += datetime.timedelta(days=1)
            continue

        _, missing = match(all_ours, theirs)
        extra, _ = match(liturgy_ours, theirs)

        checked += 1
        if missing or extra:
            diffs.append({
                'date': date.isoformat(),
                'labels': [r['label'] for r in rows if r['label']],
                'missing': missing,
                'extra': extra,
            })
        else:
            clean += 1

        date += datetime.timedelta(days=1)

    path = f'data/oca_readings_diff-{year}.json'
    with open(path, 'w') as f:
        json.dump(diffs, f, indent=1)

    pct = 100.0 * clean / checked if checked else 0.0
    print(f'{year}: {clean}/{checked} dates match ({pct:.1f}%), {len(diffs)} differ -> {path}')
    print(f'  ({ot_only} Lenten days skipped: Old Testament only, no Liturgy)')
    for d in diffs[:30]:
        bits = []
        if d['missing']:
            bits.append(f"missing={d['missing']}")
        if d['extra']:
            bits.append(f"extra={d['extra']}")
        print(f"  {d['date']}  {'  '.join(bits)}")
    if len(diffs) > 25:
        print(f'  ... and {len(diffs) - 25} more in {path}')


if __name__ == '__main__':
    for year in (sys.argv[1:] or ['2026']):
        asyncio.run(audit(int(year)))
