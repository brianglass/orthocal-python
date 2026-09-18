"""Add exact Greek-tradition reading boundaries where goarch.org and antiochian.org agree.

The original Greek audit compared only a citation's opening chapter and verse.
That hid references which began together but ended at different verses.  These
rows preserve the complete citations on which both sources agree while leaving
the existing common rows unchanged for Slavic callers.  The two December
pointer exceptions are per-year data and live in load_ordo.py.

Each row names the reading it replaces by its slot and the citation orthocal
currently has there, so the script refuses to run against data it does not
recognise instead of overwriting whatever now occupies a row.  The evidence
column lists the years each source printed the corrected citation on a date
orthocal serves that slot; goarch.org pages before 2024 were checked by hand.
Neither source printed the old citation on any of those dates.

Run this after loading the current fixtures, then regenerate calendarium.json:

    python tools/greek/load_exact_boundaries.py
    ./manage.py dumpdata calendarium --indent=2 -o fixtures/calendarium.json
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orthocal.settings')
django.setup()

from django.db import transaction

from calendarium.models import Pericope, Reading
from ingest_antiochian import parse_reading_citation


# (source, slot, citation orthocal has, citation both sources print, evidence)
# A slot is a pdist, or (month, day) for a fixed-date reading.
BOUNDARY_ROWS = (
    ('Epistle', -62, '1 John 2.18-3.10', '1 John 2:18-29; 3:1-8',
     'goarch.org 2024, 2026; antiochian.org 2023, 2026'),
    ('Epistle', -55, '3 John 1.1-14', '3 John 1:1-15',
     'goarch.org 2024, 2026; antiochian.org 2018, 2023, 2026'),
    ('Epistle', -42, 'Heb 11.24-26, 32-12.2', 'Hebrews 11:24-26, 32-40',
     'goarch.org 2024, 2026; antiochian.org 2024, 2026'),
    ('Gospel', -2, 'Matt 27.1-38; Luke 23:39-43; Matt 27:39-54; John 19:31-37; Matt 27:55-61', 'Matthew 27:62-66',
     'goarch.org 2024, 2025, 2026; antiochian.org 2021, 2026'),
    ('Epistle', 3, 'Acts 2.22-36', 'Acts 2:22-38',
     'goarch.org 2024, 2026; antiochian.org 2026'),
    ('Epistle', (5, 7), 'Acts 26.1-5, 12-20', 'Acts 26:1, 12-20',
     'goarch.org 2025, 2026; antiochian.org 2019, 2025, 2026'),
    ('Gospel', (5, 8), 'John 19.25-27, 21.24-25', 'John 19:25-28, 21:24-25',
     'goarch.org 2024, 2025, 2026; antiochian.org 2025, 2026'),
    ('Epistle', 28, 'Acts 11.19-26, 29-30', 'Acts 11:19-30',
     'goarch.org 2024, 2025, 2026; antiochian.org 2021, 2025, 2026'),
    ('Epistle', 32, 'Acts 14.20-27', 'Acts 14:20-28; 15:1-4',
     'goarch.org 2024, 2025, 2026; antiochian.org 2019, 2025, 2026'),
    ('Epistle', 33, 'Acts 15.5-34', 'Acts 15:5-12',
     'goarch.org 2024, 2025, 2026; antiochian.org 2025, 2026'),
    ('Epistle', 36, 'Acts 17.1-15', 'Acts 17:1-9',
     'goarch.org 2024, 2025, 2026; antiochian.org 2025, 2026'),
    ('Gospel', 36, 'John 11.47-57', 'John 11:47-54',
     'goarch.org 2024, 2025, 2026; antiochian.org 2025, 2026'),
    ('Epistle', (5, 21), 'Acts 26.1-5, 12-20', 'Acts 26:1, 12-20',
     'goarch.org 2024, 2025, 2026; antiochian.org 2025, 2026'),
    ('Epistle', 47, 'Acts 27.1-44', 'Acts 27:1-44; 28:1',
     'goarch.org 2024, 2025, 2026; antiochian.org 2019, 2023, 2025, 2026'),
    ('Gospel', 48, 'John 21.15-25', 'John 21:14-25',
     'goarch.org 2024, 2025, 2026; antiochian.org 2025, 2026'),
    ('Gospel', 51, 'Matt 4.25-5.13', 'Matthew 4:23-25; 5:1-13',
     'goarch.org 2024, 2025, 2026; antiochian.org 2025, 2026'),
    ('Epistle', 54, 'Rom 2.14-29', 'Romans 2:14-28',
     'goarch.org 2024, 2025, 2026; antiochian.org 2026'),
    ('Epistle', (6, 11), 'Acts 11.19-26, 29-30', 'Acts 11:19-30',
     'goarch.org 2024, 2025, 2026; antiochian.org 2026'),
    ('Epistle', 62, 'Rom 3.19-26', 'Romans 3:19-24',
     'goarch.org 2024, 2025, 2026; antiochian.org 2025, 2026'),
    ('Epistle', 64, 'Rom 7.1-13', 'Romans 7:1-14',
     'goarch.org 2025, 2026; antiochian.org 2025, 2026'),
    ('Epistle', (6, 19), 'Jude 1-10', 'Jude 1:1-25',
     'goarch.org 2024, 2025, 2026; antiochian.org 2025, 2026'),
    ('Gospel', (6, 24), 'Luke 1.1-15, 57-68, 76, 80', 'Luke 1:1-25, 57-68, 76, 80',
     'goarch.org 2024, 2025, 2026; antiochian.org 2025, 2026'),
    ('Gospel', 85, 'Matt 13.10-23', 'Matthew 13:10-23, 43',
     'goarch.org 2024, 2025, 2026; antiochian.org 2025, 2026'),
    ('Gospel', (6, 30), 'Matt 9.36-10.8', 'Matthew 9:36, 10:1-8',
     'goarch.org 2024, 2025, 2026; antiochian.org 2019, 2021, 2023, 2025, 2026'),
    ('Epistle', 102, '1 Cor 10.28-11.7', '1 Corinthians 10:28-33; 11:1-8',
     'goarch.org 2025, 2026; antiochian.org 2025, 2026'),
    ('Epistle', 103, '1 Cor 11.8-22', '1 Corinthians 11:8-23',
     'goarch.org 2026; antiochian.org 2026'),
    ('Epistle', (7, 25), 'Gal 4.22-31', 'Galatians 4:22-27',
     'goarch.org 2024, 2025, 2026; antiochian.org 2025, 2026'),
    ('Epistle', 123, '2 Cor 4.1-6', '2 Corinthians 4:1-12',
     'goarch.org 2024, 2025, 2026; antiochian.org 2025, 2026'),
    ('Epistle', 132, '1 Cor 1.26-29', '1 Corinthians 1:26-31; 2:1-5',
     'goarch.org 2025, 2026; antiochian.org 2025, 2026'),
    ('Gospel', 136, 'Mark 3.19-27', 'Mark 3:20-27',
     'goarch.org 2025, 2026; antiochian.org 2025, 2026'),
    ('Epistle', (8, 29), 'Acts 13.25-32', 'Acts 13:25-33',
     'goarch.org 2024, 2025, 2026; antiochian.org 2025, 2026'),
    ('Epistle', 144, 'Gal 1.1-10, 20-2.5', 'Galatians 1:1-3, 20-24; 2:1-5',
     'goarch.org 2025, 2026; antiochian.org 2025, 2026'),
    ('Gospel', 147, 'Matt 22.1-14', 'Matthew 22:2-14',
     'goarch.org 2024, 2026; antiochian.org 2022, 2023, 2024, 2026'),
    ('Gospel', (9, 14), 'John 19.6-11, 13-20, 25-28, 30-35', 'John 19:6-11, 13-20, 25-28, 30',
     'goarch.org 2024, 2025, 2026; antiochian.org 2025, 2026'),
    ('Epistle', 1008, '1 Cor 1.26-29', '1 Corinthians 1:26-31; 2:1-5',
     'goarch.org 2024, 2026; antiochian.org 2026'),
    ('Epistle', (9, 23), 'Gal 4.22-31', 'Galatians 4:22-27',
     'goarch.org 2024, 2025, 2026; antiochian.org 2025, 2026'),
    ('Epistle', 183, 'Phil 2.12-16', 'Philippians 2:12-15',
     'goarch.org 2024, 2026; antiochian.org 2023, 2024, 2026'),
    ('Epistle', (10, 18), 'Col 4.5-9, 14, 18', 'Colossians 4:5-11, 14-18',
     'goarch.org 2024, 2025, 2026; antiochian.org 2025, 2026'),
    ('Epistle', 193, 'Col 1.24-29', 'Colossians 1:24-29, 2:1',
     'goarch.org 2025, 2026; antiochian.org 2022, 2025, 2026'),
    ('Epistle', 224, 'Eph 4.1-6', 'Ephesians 4:1-7',
     'goarch.org 2026; antiochian.org 2018, 2020, 2023, 2026'),
    ('Epistle', (12, 9), 'Gal 4.22-31', 'Galatians 4:22-27',
     'goarch.org 2024, 2025, 2026; antiochian.org 2018, 2020, 2021, 2022, 2023, 2024, 2025, 2026'),
    ('Epistle', 242, 'Titus 1.5-2.1', 'Titus 1:5-14',
     'goarch.org 2025, 2026; antiochian.org 2021, 2022, 2023, 2025, 2026'),
    ('Epistle', 254, 'Heb 9.8-10, 15-23', 'Hebrews 9:8-23',
     'goarch.org 2025, 2026; antiochian.org 2018, 2025, 2026'),
    ('Epistle', 260, 'Heb 11.17-23, 27-31', 'Hebrews 11:17-31',
     'goarch.org 2024, 2026; antiochian.org 2024, 2026'),
    ('Gospel', 264, 'Mark 10.23-32', 'Mark 10:24-32',
     'goarch.org 2018, 2024, 2026; antiochian.org 2018, 2021, 2022, 2023, 2024, 2026'),
    ('Epistle', 105, '1 Cor 1.10-18', '1 Corinthians 1:10-17',
     'goarch.org 2024, 2025; antiochian.org 2023, 2025'),
    ('Epistle', -61, '1 John 3.10-20', '1 John 3:9-22',
     'goarch.org 2024, 2025; antiochian.org 2020, 2023'),
    ('Epistle', -60, '1 John 3.21-4.6', '1 John 3:21-24; 4:1-11',
     'goarch.org 2024, 2025; antiochian.org 2020'),
    ('Epistle', -79, '1 Peter 1.1-2, 10-12, 2.6-10', '1 Peter 1:1-25; 2:1-10',
     'goarch.org 2024; antiochian.org 2022'),
    ('Epistle', 208, '1 Thess 2.14-19', '1 Thessalonians 2:14-20',
     'goarch.org 2024; antiochian.org 2018, 2021, 2022, 2024'),
    ('Epistle', 212, '1 Thess 3.9-13', '1 Thessalonians 3:8-13',
     'goarch.org 2024, 2025; antiochian.org 2024'),
    ('Epistle', 214, '1 Thess 5.1-8', '1 Thessalonians 4:18-5:10',
     'goarch.org 2025; antiochian.org 2020, 2021'),
    ('Epistle', 143, '2 Cor 13.3-14', '2 Corinthians 13:3-13',
     'goarch.org 2024, 2025; antiochian.org 2025'),
    ('Epistle', 13, 'Acts 5.21-33', 'Acts 5:21-32',
     'goarch.org 2024, 2025; antiochian.org 2025'),
    ('Epistle', 191, 'Col 1.1-2, 7-11', 'Colossians 1:1-3, 7-11',
     'goarch.org 2018, 2019, 2020, 2023; antiochian.org 2025'),
    ('Epistle', 170, 'Eph 5.20-26', 'Ephesians 5:20-25',
     'goarch.org 2024, 2025; antiochian.org 2025'),
    ('Epistle', 257, 'Heb 11.8, 11-16', 'Hebrews 11:8-16',
     'goarch.org 2018; antiochian.org 2018'),
    ('Gospel', 251, 'Luke 13.18-29', 'Luke 13:19-29',
     'goarch.org 2024, 2025; antiochian.org 2018, 2021, 2022, 2024, 2025'),
    ('Gospel', 225, 'Luke 14.12-15', 'Luke 14:1, 12-15',
     'goarch.org 2024, 2025; antiochian.org 2021, 2024'),
    ('Gospel', (8, 16), 'Luke 9.51-56, 10.22-24', 'Luke 9:51-57, 10:22-24, 13:22',
     'goarch.org 2024, 2025; antiochian.org 2025'),
    ('Gospel', 135, 'Mark 3.13-19', 'Mark 3:13-21',
     'goarch.org 2025; antiochian.org 2025'),
    ('Gospel', (9, 13), 'Matt 16.13-18', 'Matthew 16:13-19',
     'goarch.org 2024, 2025; antiochian.org 2025'),
)

SHORT_BOOKS = {
    'Matthew': 'Matt', 'Romans': 'Rom', '1 Corinthians': '1 Cor', '2 Corinthians': '2 Cor',
    'Galatians': 'Gal', 'Ephesians': 'Eph', 'Philippians': 'Phil',
    'Colossians': 'Col', '1 Thessalonians': '1 Thess',
    '2 Thessalonians': '2 Thess', '1 Timothy': '1 Tim', '2 Timothy': '2 Tim',
    'Hebrews': 'Heb', '1 Peter': '1 Pet',
}

def normalized_displays(title):
    reference = parse_reading_citation(title)
    match = re.match(r'(.+?)\s+(\d.*)', reference)
    book, specification = match.groups()
    specification = specification.replace(':', '.')
    display = f'{book} {specification}'
    return display, f'{SHORT_BOOKS.get(book, book)} {specification}'


def verse_codes(sdisplay):
    """Return the fixture's descriptive verse-code form for a citation."""
    match = re.match(r'(.+?)\s+(\d.*)', sdisplay)
    book, specification = match.groups()
    # The fixture spells the book as the short name without its space; 1 Peter
    # is the one exception.
    token = {'1 Pet': '1Peter'}.get(book, book.replace(' ', ''))
    chapter = None
    codes = []
    for piece in re.split(r'\s*[;,]\s*', specification):
        match = re.fullmatch(r'(?:(\d+)\.)?(\d+)(?:-(?:(\d+)\.)?(\d+))?', piece)
        if not match:
            raise ValueError(f'Cannot encode {piece!r} from {sdisplay!r}')
        start_chapter, start_verse, end_chapter, end_verse = match.groups()
        if start_chapter:
            chapter = int(start_chapter)
        if chapter is None:
            raise ValueError(f'Missing chapter in {sdisplay!r}')
        finish_chapter = int(end_chapter) if end_chapter else chapter
        finish_verse = int(end_verse) if end_verse else int(start_verse)
        codes.append(
            f'{token}_{chapter * 1000 + int(start_verse)}_'
            f'{finish_chapter * 1000 + finish_verse}'
        )
        chapter = finish_chapter
    return '|'.join(codes)


def exact_pericope(base, title):
    display, sdisplay = normalized_displays(title)
    if found := Pericope.objects.filter(sdisplay=sdisplay).first():
        return found

    next_number = 309
    while Pericope.objects.filter(pericope=f'{next_number}grk', book=base.book).exists():
        next_number += 1
    return Pericope.objects.create(
        pericope=f'{next_number}grk',
        book=base.book,
        display=display,
        sdisplay=sdisplay,
        desc=base.desc,
        preverse=base.preverse,
        prefix=base.prefix,
        prefixb=base.prefixb,
        verses=verse_codes(sdisplay),
        suffix=base.suffix,
        flag=base.flag,
    )


def base_reading(source, slot, current, corrected):
    """The row a boundary replaces, found by what it says rather than its pk.

    Once applied, a greek-tagged base carries the corrected citation, so that
    is accepted too and a second run changes nothing.
    """
    if isinstance(slot, tuple):
        rows = Reading.objects.filter(source=source, pdist=999, month=slot[0], day=slot[1])
    else:
        rows = Reading.objects.filter(source=source, pdist=slot)
    rows = list(rows.exclude(tradition='slavic').select_related('pericope'))

    for found in ([r for r in rows if r.pericope.sdisplay == current],
                  [r for r in rows if r.tradition == 'greek' and r.pericope.sdisplay == corrected]):
        if len(found) > 1:
            raise LookupError(f'{source} {slot}: {len(found)} rows read {found[0].pericope.sdisplay!r}')
        if found:
            return found[0]

    raise LookupError(
        f'{source} {slot}: expected {current!r}, found '
        f'{sorted(r.pericope.sdisplay for r in rows)}'
    )


def cycle_copies(base):
    """The same weekday reading reached from the other Paschal year.

    Late-autumn and pre-Triodion weekdays are stored twice: after Pentecost
    (e.g. pdist 264) and before the next Pascha (e.g. pdist -86). Overriding
    only one leaves the old boundary on the dates that reach the other.
    Fixed-date (999) and floating (1000+) readings have no such copy.
    """
    if base.pdist >= 999:
        return [base]
    return [base, *Reading.objects.filter(
        pericope=base.pericope, source=base.source, ordering=base.ordering,
        desc=base.desc, tradition='common', pdist__lt=999,
    ).exclude(pk=base.pk)]


# One transaction, so a row that no longer matches leaves nothing half applied.
with transaction.atomic():
    for source, slot, current, corrected, evidence in BOUNDARY_ROWS:
        base = base_reading(source, slot, current, normalized_displays(corrected)[1])
        pericope = exact_pericope(base.pericope, corrected)
        for copy in cycle_copies(base):
            lookup = {
                'pdist': copy.pdist,
                'month': copy.month,
                'day': copy.day,
                'source': copy.source,
                'ordering': copy.ordering,
                'desc': copy.desc,
                'tradition': 'greek',
            }
            row, created = Reading.objects.update_or_create(
                **lookup,
                defaults={'pericope': pericope, 'flag': copy.flag},
            )
            print(f'{"+" if created else "~"} Reading {row.pk}: {pericope.sdisplay}')
