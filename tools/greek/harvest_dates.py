"""Harvest specific calendar dates from antiochian.org across years.

The standing harvest is winter-weighted, so a few fixed dates elsewhere in the
year have too few samples to confirm a Menaion reading. This fills those in.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])

import datetime
from ingest_antiochian import Antiochian, CACHE_DIR

# Edit these for whatever dates need filling in. Already-cached dates are
# skipped, so re-running is cheap and safe.
TARGETS = [(1, 19), (1, 24), (1, 26)]
YEARS = [2020, 2027]

client = Antiochian(delay=2.0)
client.authenticate()
for month, day in TARGETS:
    for year in YEARS:
        dt = datetime.date(year, month, day)
        if (CACHE_DIR / f'{dt.isoformat()}.json').exists():
            print(f'  cached  {dt}')
            continue
        try:
            client.get_liturgical_day(dt)
            print(f'  fetched {dt}')
        except Exception as exc:
            print(f'  FAILED  {dt}: {type(exc).__name__}: {exc}')
