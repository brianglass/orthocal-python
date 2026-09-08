"""Harvest a year of OCA readings across *every* service, into data/oca_raw/.

    python tools/oca/harvest_daily.py 2026

Source: https://www.oca.org/readings/daily/YYYY/MM/DD -- the daily index, which
lists every reading for the day, not just the Liturgy. Theophany Eve returns 34
readings here (four sets of Hours, thirteen Vespers lessons, the Liturgy pair,
and the Blessing of Waters) where the monthly lectionary gives two.

That is the whole point of this harvest. harvest_readings.py covers the Liturgy
Epistle and Gospel, which is 894 of 1,446 readings a year -- 38% of what the
app renders was unmeasured, and the gap fell on exactly the feast days where
the open reading-selection question lives. See docs/oca-audit.md.

One request per day rather than one per reading: the index carries the
citations, and the audit matches on citations rather than on service labels
(neither side names the service consistently -- again see docs/oca-audit.md).

**365 requests at oca.org's requested Crawl-delay of 10 seconds -- about an
hour a year.** Cached by tools/oca/fetch.py, so re-runs are instant. Run it in
the background.

Writes data/oca_raw/daily-YYYY.json: {"YYYY-MM-DD": ["Isaiah 35:1-10", ...]}
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])

import datetime
import html
import json
import re

from tools.oca.fetch import get

SECTION = re.compile(r'<section>\s*<ul>(.*?)</ul>', re.S)
LINK = re.compile(r'<a href="/readings/daily/[^"]+">(.*?)</a>', re.S)


def clean(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', s))).strip()


def harvest(year):
    path = f'data/oca_raw/daily-{year}.json'
    out = json.load(open(path)) if os.path.exists(path) else {}

    date = datetime.date(year, 1, 1)
    while date.year == year:
        key = date.isoformat()
        if key in out:
            date += datetime.timedelta(days=1)
            continue

        page = get(f'https://www.oca.org/readings/daily/'
                   f'{date.year}/{date.month:02d}/{date.day:02d}')
        section = SECTION.search(page or '')
        out[key] = [clean(c) for c in LINK.findall(section.group(1))] if section else []

        # Checkpoint; an hour-long harvest should survive a stray ^C.
        json.dump(out, open(path, 'w'), indent=1, sort_keys=True)
        print(f'  {key}: {len(out[key])}', flush=True)
        date += datetime.timedelta(days=1)

    print(f'{year}: {len(out)} dates, {sum(len(v) for v in out.values())} readings -> {path}')


if __name__ == '__main__':
    for year in (sys.argv[1:] or ['2026']):
        harvest(int(year))
