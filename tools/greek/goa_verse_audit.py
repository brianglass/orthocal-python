"""app(Greek) vs goarch.org by verse set, over every harvested year.

Supersedes goa_gap.py, three_way.py and year_diff.py as the accuracy measure.
Those reduced each citation to its opening chapter:verse and accepted a match
within two verses, so a reading that started with goarch.org's but ended
elsewhere (`Acts 15:5-34` against `Acts 15:5-12`) counted as correct. That hid
dozens of pericope-boundary errors a year behind a 99.1% score; see
docs/greek-lectionary.md, "Accuracy, measured".

Here both sides are expanded to the full set of verses they cover, using KJV
chapter lengths (other translations number some chapters differently), and a
goarch.org Epistle or Gospel matches only if some app reading of the same kind
covers exactly the same verses. Extra app readings never count against it.

Data: data/goarch_readings_2018_2027.json, every civil date with full
citations. A result is one of
    exact     -- some app reading covers exactly goarch.org's verses
    boundary  -- an app reading overlaps it but starts or ends elsewhere
    missing   -- no app reading of that kind overlaps it at all

    docker compose run --rm local python tools/greek/goa_verse_audit.py
    docker compose run --rm local python tools/greek/goa_verse_audit.py 2026 --list
    docker compose run --rm local python tools/greek/goa_verse_audit.py --recurring

--list prints every difference; --recurring groups them by goarch.org
citation across years, which is how systematic gaps show up.
"""
import argparse
import asyncio
import collections
import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orthocal.settings')
django.setup()

from django.db.models import Max

from bible.models import Verse
from calendarium.datetools import Tradition
from calendarium.liturgics import Day

HARVEST = 'data/goarch_readings_2018_2027.json'
SOURCES = {'E': 'Epistle', 'G': 'Gospel'}

BOOKS = (
    ('MAT', r'MATT?(HEW)?'), ('MRK', r'MARK|MK'), ('LUK', r'LUKE?|LK'), ('JHN', r'JOHN|JN'),
    ('ACT', r'ACTS?'), ('ROM', r'ROM(ANS)?'), ('1CO', r'1 ?COR(INTHIANS)?'), ('2CO', r'2 ?COR(INTHIANS)?'),
    ('GAL', r'GAL(ATIANS)?'), ('EPH', r'EPH(ESIANS)?'), ('PHP', r'PHIL(IPPIANS)?|PHP'),
    ('COL', r'COL(OSSIANS)?'), ('1TH', r'1 ?THESS?(ALONIANS)?'), ('2TH', r'2 ?THESS?(ALONIANS)?'),
    ('1TI', r'1 ?TIM(OTHY)?'), ('2TI', r'2 ?TIM(OTHY)?'), ('TIT', r'TIT(US)?'),
    ('PHM', r'PHILEMON|PHLM|PHM'), ('HEB', r'HEB(REWS)?'), ('JAS', r'JA(ME)?S'),
    ('1PE', r'1 ?PET(ER)?'), ('2PE', r'2 ?PET(ER)?'), ('1JN', r'1 ?JOHN|1 ?JN'),
    ('2JN', r'2 ?JOHN|2 ?JN'), ('3JN', r'3 ?JOHN|3 ?JN'), ('JUD', r'JUDE'),
)
CHAPTERLESS = {'PHM', '2JN', '3JN', 'JUD'}
PART = re.compile(r'^\s*((?:[123]|I{1,3})?\s*[A-Za-z][A-Za-z.]*)?\s*(\d.*)$')
ITEM = re.compile(r'(\d+)(?:\.(\d+))?(?:\s*-\s*(\d+)(?:\.(\d+))?)?[a-z]?')

CHAPTERS = collections.defaultdict(dict)
for row in Verse.objects.filter(translation='kjv').values('book', 'chapter').annotate(n=Max('verse')):
    CHAPTERS[row['book']][row['chapter']] = row['n']


def book_code(name):
    n = name.upper().replace('.', '').strip()
    n = re.sub(r'^(III|II|I)\s+', lambda m: f'{len(m.group(1))} ', n)
    n = re.sub(r'\s+', ' ', n)
    return next((code for code, rx in BOOKS if re.fullmatch(rx, n)), None)


def verse_set(citation):
    """The (book, chapter, verse) triples a New Testament citation covers.

    Reads both this repo's style (`Heb 11.24-26, 32-12.2`, `Jude 1-10`) and
    goarch.org's (`I John 2:18-29; 3:1-8`, `Acts 26:1,12-20`). Returns None
    for anything it cannot read, so an unparsed citation is never a match.
    """
    # goarch.org occasionally types ':' for ';' ("Mark 13:31-37: 14:1-2").
    citation = re.sub(r':\s+(?=\d+:)', '; ', citation.strip())
    verses, book, chapter = set(), None, None
    for part in re.split(r'\s*;\s*', citation):
        m = PART.match(part)
        if not m:
            return None
        if m.group(1):
            book, chapter = book_code(m.group(1)), None
        if not book:
            return None
        for item in re.split(r'\s*,\s*', m.group(2)):
            im = ITEM.fullmatch(item.strip().replace(':', '.'))
            if not im:
                return None
            a, b, c, d = im.groups()
            if book in CHAPTERLESS:
                # "Jude 1-10" is verses 1-10; "Jude 1:1-10" is chapter 1.
                first, last = (int(b), int(d or c or b)) if b else (int(a), int(c or a))
                verses.update((book, 1, v) for v in range(first, last + 1))
                chapter = 1
                continue
            if b is not None:
                start = (int(a), int(b))
            elif chapter is not None:
                start = (chapter, int(a))
            else:
                return None
            if c is None:
                end = start
            elif d is not None:
                end = (int(c), int(d))
            else:
                end = (start[0], int(c))
            ch, v = start
            while (ch, v) <= end and v <= CHAPTERS[book].get(ch, 0):
                verses.add((book, ch, v))
                v += 1
                if v > CHAPTERS[book].get(ch, 0):
                    ch, v = ch + 1, 1
            chapter = end[0]
    return frozenset(verses)


async def app_readings(date):
    day = Day(date.year, date.month, date.day, tradition=Tradition.Greek)
    await day.ainitialize()
    return [(r.source, r.pericope.sdisplay) for r in await day.aget_readings()]


async def audit(years):
    harvest = json.load(open(HARVEST))
    results = []
    for key, value in sorted(harvest.items()):
        if key.startswith('_') or int(key[:4]) not in years:
            continue
        label, readings = value
        date = datetime.date.fromisoformat(key)
        ours = await app_readings(date)
        for kind, citation in readings:
            if kind not in SOURCES:
                continue
            want = verse_set(citation)
            candidates = [s for source, s in ours if source == SOURCES[kind]]
            got = [verse_set(s) for s in candidates]
            if want is None:
                result = 'unparsed'
            elif want in got:
                result = 'exact'
            elif any(g and g & want for g in got):
                result = 'boundary'
            else:
                result = 'missing'
            results.append((key, label, SOURCES[kind], citation, result, candidates))
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('years', nargs='*', type=int, default=list(range(2018, 2028)))
    parser.add_argument('--list', action='store_true', help='print every difference')
    parser.add_argument('--recurring', action='store_true', help='group differences by citation')
    args = parser.parse_args()

    results = asyncio.run(audit(set(args.years)))
    by_year = collections.defaultdict(collections.Counter)
    for key, *_, result, _ in results:
        by_year[key[:4]][result] += 1

    total = collections.Counter()
    print('app(Greek) vs goarch.org, Epistle and Gospel fields, by verse set')
    for year, counts in sorted(by_year.items()):
        total.update(counts)
        n = sum(counts.values())
        print(f'  {year}: {counts["exact"]:4} of {n} exact ({100 * counts["exact"] / n:.1f}%)'
              f'  boundary {counts["boundary"]}, missing {counts["missing"]}, unparsed {counts["unparsed"]}')
    n = sum(total.values())
    print(f'  all : {total["exact"]:4} of {n} exact ({100 * total["exact"] / n:.1f}%)')

    misses = [r for r in results if r[4] != 'exact']
    if args.list:
        print()
        for key, label, source, citation, result, candidates in misses:
            print(f'{key} {source:<7} {result:<8} goarch {citation!r}  app {candidates}  ({label})')
    if args.recurring:
        print()
        groups = collections.defaultdict(list)
        for miss in misses:
            groups[miss[2], miss[3]].append(miss)
        for (source, citation), rows in sorted(groups.items(), key=lambda g: -len(g[1])):
            apps = collections.Counter(' | '.join(r[5]) for r in rows).most_common(1)[0][0]
            print(f'{len(rows):3}x {source:<7} {citation:<34} {rows[0][4]:<8} app: {apps}')
            print(f'      {", ".join(r[0] for r in rows)}')


main()
