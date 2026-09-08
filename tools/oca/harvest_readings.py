"""Harvest a year of OCA daily Liturgy readings into data/oca_raw/.

    python tools/oca/harvest_readings.py 2026 [2025 ...]

Source: https://www.oca.org/readings/monthly/YYYY/MM -- twelve small tables a
year, each row a date with its citations and an optional free-text label:

    <td class="date">1/1</td>
      <td>Colossians 2:8-12</td>
      <td>Luke 2:20-21,40-52</td>
      <td>(Circumcision)</td>

**The columns are not positionally stable, so this stores cells, not slots.**
January and May-December give four cells a row; February, March and April give
five. The extra column is not consistently anything: on 2/1 it is empty and the
Epistle and Gospel follow it, while on 2/18 a Lenten day's two Old Testament
lessons occupy the very cells a Liturgy day uses for Epistle and Gospel.
Reading Epistle and Gospel off column numbers silently swaps them for a third
of the year -- it scored the app at 73.7% when the real figure was far higher.
Classify by book instead: tools/oca/refs.py `slot()`.

A date carries one row per reading set, so most days have one or two and a
feast can have several. The label is free text, not a controlled vocabulary --
"(Saint)", "(Saturday Before)", "(Forerunner)". Do not try to map labels onto
our `source` field; match on the citations and treat the label as a hint.

This page gives the Liturgy plus, in the Lenten months, Vespers Old Testament
lessons. Matins is not here.

Writes data/oca_raw/readings-YYYY.json:
    {"YYYY-MM-DD": [{"citations": [...], "label": "..."}, ...]}
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])

import html
import json
import re

from tools.oca.fetch import get

CELL = re.compile(r'<td[^>]*>(.*?)</td>', re.S)
DATE = re.compile(r'^(\d+)/(\d+)$')


def clean(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', s))).strip()


def harvest(year):
    out = {}
    for month in range(1, 13):
        page = get(f'https://www.oca.org/readings/monthly/{year}/{month:02d}')
        if page is None:
            print(f'  {year}-{month:02d}: no page')
            continue
        n = 0
        for row in re.findall(r'<tr>(.*?)</tr>', page, re.S):
            cells = [clean(c) for c in CELL.findall(row)]
            if not cells:
                continue
            m = DATE.match(cells[0])
            if not m or int(m.group(1)) != month:
                continue

            # Everything after the date is either a citation or the label; the
            # label is the parenthesised one, and empty cells are padding.
            label, citations = '', []
            for c in cells[1:]:
                if not c:
                    continue
                if c.startswith('(') and c.endswith(')'):
                    label = c.strip('()')
                else:
                    citations.append(c)

            key = f'{year}-{month:02d}-{int(m.group(2)):02d}'
            out.setdefault(key, []).append({'citations': citations, 'label': label})
            n += 1
        print(f'  {year}-{month:02d}: {n} rows')

    path = f'data/oca_raw/readings-{year}.json'
    with open(path, 'w') as f:
        json.dump(out, f, indent=1, sort_keys=True)
    print(f'{year}: {len(out)} dates, {sum(len(v) for v in out.values())} rows -> {path}')


if __name__ == '__main__':
    for year in (sys.argv[1:] or ['2026']):
        harvest(int(year))
