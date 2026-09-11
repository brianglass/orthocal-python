"""Pin the current fasting output, so a refactor can prove it changed nothing.

    docker compose run --rm local python tools/fasting/characterize.py --write
    docker compose run --rm local python tools/fasting/characterize.py          # analyse

Writes calendarium/tests/data/fasting-characterization.txt, one line per day per
tradition, covering YEARS below. `test_fasting_characterization.py` regenerates
the same lines and asserts they match, so any behavioural drift shows up as a
readable diff rather than as a number moving somewhere.

Why a golden file rather than assertions: the thing being characterised is a
combination rule nobody wrote down. `Day.fast_exception` is `max()` over an
integer that encodes a dietary rung, a precedence claim and a sentinel all at
once, and `_apply_fasting_adjustments` then patches whatever that gets wrong.
There is no spec to assert against -- only current behaviour, which has to be
preserved exactly through a refactor and then changed deliberately.
See docs/fasting-refactor-scope.md.

Each line carries the *inputs* as well as the outputs:

    2026-04-05 slavic w6 feast8 fast2 exc4 rows=0,4 -> meat,dairy,eggs

so a diff shows not just that a day changed but which contributing rows and
which rank produced it. `rows` is the sorted fast_exception of every Day record
the date resolved to, before combination -- the raw material the refactor is
replacing.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])

import asyncio
import collections
import datetime

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orthocal.settings')
django.setup()

from calendarium import datetools                    # noqa: E402
from calendarium.datetools import Tradition          # noqa: E402
from calendarium.liturgics import Day                # noqa: E402

# Five years spans the whole Paschal range, so fixed dates land on many
# different pdists and weekdays. Pascha: Apr 20 2025, Apr 12 2026, Mar 28 2027,
# Apr 16 2028, Apr 8 2029.
YEARS = (2025, 2026, 2027, 2028, 2029)
PATH = 'calendarium/tests/data/fasting-characterization.txt'


async def lines():
    out = []
    for tradition, name in ((Tradition.Slavic, 'slavic'), (Tradition.Greek, 'greek')):
        for year in YEARS:
            date = datetime.date(year, 1, 1)
            while date.year == year:
                day = Day(date.year, date.month, date.day, tradition=tradition)
                await day.ainitialize()
                rows = ','.join(str(e) for e in sorted(d.fast_exception for d in day.days))
                abstain = ','.join(
                    datetools.fast_abstentions_for(day.fast_level, day.fast_exception))
                out.append(
                    f'{date.isoformat()} {name} w{day.weekday} feast{day.feast_level} '
                    f'fast{day.fast_level} exc{day.fast_exception} rows={rows} '
                    f'-> {abstain or "-"}'
                )
                date += datetime.timedelta(days=1)
    return out


async def main(write):
    rendered = await lines()

    if write:
        with open(PATH, 'w') as f:
            f.write('\n'.join(rendered) + '\n')
        print(f'wrote {len(rendered)} lines -> {PATH}')

    # What the pinned data actually covers, which is the point of looking at it
    # before trusting it as a safety net.
    combos = collections.Counter()
    outcomes = collections.Counter()
    by_rows = collections.defaultdict(set)
    for line in rendered:
        head, _, tail = line.partition(' -> ')
        parts = head.split()
        rows = parts[-1].removeprefix('rows=')
        exc = parts[-2].removeprefix('exc')
        combos[rows] += 1
        outcomes[tail] += 1
        by_rows[rows].add(exc)

    print(f'\n  days pinned: {len(rendered)}  '
          f'({len(YEARS)} years x 2 traditions)')
    print(f'  distinct row-collision patterns: {len(combos)}')
    print(f'  distinct dietary outcomes: {len(outcomes)}\n')
    print('  collision patterns, by frequency:')
    for rows, n in combos.most_common():
        excs = ','.join(sorted(by_rows[rows]))
        multi = '  <-- resolves differently in different contexts' if len(by_rows[rows]) > 1 else ''
        print(f'    rows=({rows:<10}) {n:>5} days   -> exc {excs}{multi}')


if __name__ == '__main__':
    asyncio.run(main('--write' in sys.argv))
