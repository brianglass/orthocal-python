"""Harvest a year of OCA commemorations into data/oca_raw/saints-YYYY.json.

    python tools/oca/harvest_saints.py 2026

Source: https://www.oca.org/saints/lives/YYYY/MM/DD -- one page a day, each
listing the day's commemorations as <article class="saint"> blocks with a
heading and a permalink carrying a stable numeric id:

    /saints/lives/2026/01/15/100196-venerable-paul-of-thebes

The id is the useful part. Titles are prose and vary in wording between
sources, but the id is oca.org's own identity for that saint, so it is what to
match on when the same figure appears on two dates.

**This is 365 requests at oca.org's requested Crawl-delay of 10 seconds --
about an hour.** Everything is cached on disk by tools/oca/fetch.py, so it is a
one-time cost; re-runs are instant. Run it in the background.

Saints are overwhelmingly fixed-date, so one year covers nearly all of them.
The exceptions are the movable commemorations tied to Pascha, which land on
different calendar dates each year -- do not treat a single year's harvest as a
complete census of those.
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

ARTICLE = re.compile(r'<article class="saint.*?</article>', re.S)
LINK = re.compile(r'href="/saints/lives/\d{4}/\d{2}/\d{2}/(\d+)-([^"]+)"')
HEADING = re.compile(r'<h[1-6][^>]*>(.*?)</h[1-6]>', re.S)


def clean(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', s))).strip()


def harvest(year):
    path = f'data/oca_raw/saints-{year}.json'
    out = {}
    if os.path.exists(path):
        with open(path) as f:
            out = json.load(f)

    date = datetime.date(year, 1, 1)
    while date.year == year:
        key = date.isoformat()
        if key in out:
            date += datetime.timedelta(days=1)
            continue

        page = get(f'https://www.oca.org/saints/lives/'
                   f'{date.year}/{date.month:02d}/{date.day:02d}')
        saints = []
        for block in ARTICLE.findall(page or ''):
            link = LINK.search(block)
            heading = HEADING.search(block)
            if not link:
                continue
            saints.append({
                'id': int(link.group(1)),
                'slug': link.group(2),
                'title': clean(heading.group(1)) if heading else '',
            })
        out[key] = saints

        # Checkpoint as we go; an hour-long harvest should survive a stray ^C.
        with open(path, 'w') as f:
            json.dump(out, f, indent=1, sort_keys=True)
        print(f'  {key}: {len(saints)}', flush=True)
        date += datetime.timedelta(days=1)

    total = sum(len(v) for v in out.values())
    print(f'{year}: {len(out)} dates, {total} commemorations -> {path}')


if __name__ == '__main__':
    for year in (sys.argv[1:] or ['2026']):
        harvest(int(year))
