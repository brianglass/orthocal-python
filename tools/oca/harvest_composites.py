"""Harvest oca.org's text for every Composite reading into data/oca_raw/.

    python tools/oca/harvest_composites.py

oca.org publishes the same composite corpus, under the same numbering, as
orthodox_calendar -- verified identical word for word on Composites 17 and 18.
It is NOT Archimandrite Ephrem's translation, which is what our Composite table
stores, so it is useful here as *evidence of which verses a composite covers*
rather than as replacement text.

oca.org does not publish the verse selection either: a composite's title is
chapter-only ("Composite 17 - Exodus 40") and the <dt> markers in its body are
part numbers (1, 2, 3), not verse numbers, where an ordinary reading's <dt>
markers are true verses. So the text is the only handle on what a composite
actually contains, which is why this exists.

Writes data/oca_raw/composites.json: {"17": {"title": ..., "date": ..., "parts": [...]}}
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])

import html
import json
import re

from tools.oca.fetch import get

# Where each composite is used, as a 2026 date. Fixed dates come straight from
# the Reading rows; Composites 19-20 are Mid-Pentecost (pdist 24) and 21-22
# Ascension (pdist 39), which fall on May 6 and May 21 in 2026.
DATES = ['01-01', '01-25', '01-27', '02-02', '02-24', '05-06', '05-21',
         '06-24', '07-20', '08-06', '09-01', '10-26', '11-21']
YEAR = 2026


def clean(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', s))).strip()


def main():
    path = 'data/oca_raw/composites.json'
    out = json.load(open(path)) if os.path.exists(path) else {}

    for md in DATES:
        month, day = md.split('-')
        index = get(f'https://www.oca.org/readings/daily/{YEAR}/{month}/{day}')
        if not index:
            print(f'  {md}: no page')
            continue

        for href, title in re.findall(
                r'<li><a href="(/readings/daily/[^"]+)"[^>]*>(.*?)</a></li>', index):
            title = clean(title)
            m = re.match(r'Composite (\d+)', title)
            if not m or m.group(1) in out:
                continue

            page = get(f'https://www.oca.org{href}')
            body = re.search(r'<dl class="reading">(.*?)</dl>', page or '', re.S)
            if not body:
                print(f'  {md}: {title} -- no reading body')
                continue
            parts = [clean(p) for p in re.findall(r'<dd>(.*?)</dd>', body.group(1), re.S)]
            out[m.group(1)] = {'title': title, 'date': f'{YEAR}-{md}', 'parts': parts}
            json.dump(out, open(path, 'w'), indent=1, sort_keys=True)
            print(f'  {md}: {title} -- {len(parts)} parts, '
                  f'{sum(len(p.split()) for p in parts)} words', flush=True)

    print(f'{len(out)} composites -> {path}')


if __name__ == '__main__':
    main()
