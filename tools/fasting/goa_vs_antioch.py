"""Compare the two Greek-tradition jurisdictions to each other, not to us.

    docker compose run --rm local python tools/fasting/goa_vs_antioch.py

Every earlier comparison in this project measured *this app* against
antiochian.org, which conflates our errors with their divergence and made the
two jurisdictions look much further apart than they are. This puts their own
published calendars side by side.

Last run 2026-09-10: **374/396, 94.4%**, on the days both sources cover.

Sources: `data/goarch_fasting.json` (harvested; see tools/fasting/goarch_audit.py)
and `data/antiochian_raw/*.json`, whose `fastDesignation` is free text and is
mapped below. Antioch publishes a "wine but not oil" level that GOA's five
colours have no category for, so a handful of Holy Week days differ in
granularity rather than in substance.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])

import collections
import glob
import json

GOARCH = 'data/goarch_fasting.json'
ANTIOCHIAN = 'data/antiochian_raw/*.json'

GOA_CODES = {'S': 'strict', 'W': 'wine+oil', 'F': 'fish',
             'D': 'meat fast', 'N': 'no fast'}

ANTIOCHIAN_DESIGNATIONS = {
    'ABSTAIN FROM MEAT, FISH, DAIRY, EGGS, WINE, OLIVE OIL': 'strict',
    'ABSTAIN FROM MEAT, FISH, DAIRY, EGGS, OLIVE OIL': 'wine only',
    'ABSTAIN FROM MEAT, FISH, DAIRY, EGGS': 'wine+oil',
    'ABSTAIN FROM MEAT, DAIRY, EGGS': 'fish',
    'ABSTAIN FROM MEAT': 'meat fast',
    'NO FAST': 'no fast',
}


def antiochian():
    out = {}
    for path in glob.glob(ANTIOCHIAN):
        with open(path) as f:
            row = json.load(f)
        date = (row.get('originalCalendarDate') or '')[:10]
        level = ANTIOCHIAN_DESIGNATIONS.get(
            (row.get('fastDesignation') or '').strip().upper())
        if date and level:
            out[date] = level
    return out


def main():
    with open(GOARCH) as f:
        goa = json.load(f)
    ant = antiochian()

    agree = 0
    differences = []
    for date, theirs in sorted(ant.items()):
        year, month, day = date.split('-')
        month_key = f'{year}-{month}'
        if month_key not in goa:
            continue
        ours = GOA_CODES[goa[month_key][int(day) - 1]]
        if ours == theirs:
            agree += 1
        else:
            differences.append((date, ours, theirs))

    total = agree + len(differences)
    print(f'\n  GOA vs Antioch on {total} shared days: '
          f'{agree} agree ({100 * agree / total:.1f}%), {len(differences)} differ\n')
    for (goa_level, ant_level), n in collections.Counter(
            (d[1], d[2]) for d in differences).most_common():
        print(f'    GOA={goa_level:<10} Antioch={ant_level:<10} {n}')
    print('\n  differences:')
    for date, goa_level, ant_level in differences:
        print(f'    {date}  GOA={goa_level:<10} Antioch={ant_level}')


if __name__ == '__main__':
    main()
