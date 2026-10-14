"""Pin how every harvested antiochian.org reading compares with orthocal.

    docker compose run --rm local python tools/greek/antiochian_characterize.py --write
    docker compose run --rm local python tools/greek/antiochian_characterize.py          # summary

Reads every cached day in data/antiochian_raw and writes
calendarium/tests/data/antiochian-readings.tsv, one line per reading title.
`test_antiochian_readings.py` classifies the same titles again and asserts
the lines match. Run it after re-harvesting or after changing Greek readings,
then review the diff: a line leaving `boundary` is a fix, a line leaving
`exact` is a regression.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])

import asyncio
import collections
import json
from pathlib import Path

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orthocal.settings')
django.setup()

from calendarium.tests.test_antiochian_readings import GOLDEN, characterize  # noqa: E402


def entries():
    for path in sorted(Path('data/antiochian_raw').glob('*.json')):
        day = json.loads(path.read_text())
        for n in (1, 2, 3):
            if title := ' '.join(day.get(f'reading{n}Title', '').split()):
                yield path.stem, title


async def main(write):
    lines = await characterize(list(entries()))

    if write:
        GOLDEN.write_text('\n'.join(lines) + '\n')
        print(f'wrote {len(lines)} lines -> {GOLDEN}')

    counts = collections.Counter(line.split('\t')[2] for line in lines)
    print(', '.join(f'{status} {n}' for status, n in counts.most_common()))


if __name__ == '__main__':
    asyncio.run(main('--write' in sys.argv))
