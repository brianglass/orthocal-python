"""Audit the Greek abbreviated Epistle and Gospel on Sundays against goarch.org and antiochian.org.

Only Sundays where a fixed-date proper competes with the Sunday's readings are
counted -- the question is which of the two wins (see
models.Reading.displaces_sunday). Readings are compared by book, chapter and
opening verse.

    docker compose run --rm -T -v "$PWD/data:/orthocal/data:ro" tests python tools/greek/sunday_pair_audit.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])   # data/ paths below are repo-root relative

import collections, datetime, glob, json, re
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orthocal.settings')
django.setup()
from calendarium.liturgics import Day

# Numbered books first, so that "II Corinthians" is not read as the first.
BOOKS = (
    ('2cor', r'(SECOND|\b2|\bII)\s.*COR'), ('1cor', r'(FIRST|\b1|\bI)\s.*COR'),
    ('2tim', r'(SECOND|\b2|\bII)\s.*TIM'), ('1tim', r'(FIRST|\b1|\bI)\s.*TIM'),
    ('2thess', r'(SECOND|\b2|\bII)\s.*THES'), ('1thess', r'(FIRST|\b1|\bI)\s.*THES'),
    ('2pet', r'(SECOND|\b2|\bII)\s.*PET'), ('1pet', r'(FIRST|\b1|\bI)\s.*PET'),
    ('3john', r'(THIRD|\b3|\bIII)\s.*JOHN'), ('2john', r'(SECOND|\b2|\bII)\s.*JOHN'),
    ('1john', r"(FIRST|\b1|\bI)\s.*JOHN|JOHN'S FIRST"),
    ('heb', 'HEB'), ('rom', 'ROM'), ('eph', 'EPH'), ('gal', 'GAL'), ('phlm', 'PHILEMON'),
    ('phil', 'PHIL'), ('col', 'COL'), ('titus', 'TIT'), ('jas', r'JAMES|\bJAS\b'),
    ('jude', 'JUDE'), ('acts', 'ACTS'),
    ('matt', 'MATT'), ('mark', r'MARK|\bMK\b'), ('luke', r'LUKE|\bLK\b'), ('john', r'JOHN|\bJN\b'),
)
GOSPELS = {'matt', 'mark', 'luke', 'john'}


def key(citation):
    """(book, chapter, verse) of a citation's opening, or None."""
    s = (citation or '').upper()
    verse = re.search(r'(\d+)[:.](\d+)', s)
    head = s[:verse.start()] if verse else s
    for book, pattern in BOOKS:
        if re.search(pattern, head):
            return (book, int(verse.group(1)), int(verse.group(2))) if verse else (book, 1, 1)
    return None


def goa_pairs():
    for date, entry in json.load(open('data/goarch_readings_2018_2027.json')).items():
        if date.startswith('_'):
            continue
        label, readings = entry
        cited = dict((kind, c) for kind, c in readings if kind in ('E', 'G'))
        yield date, key(cited.get('E')), key(cited.get('G'))


def antiochian_pairs():
    for path in sorted(glob.glob('data/antiochian_raw/*.json')):
        entry = json.load(open(path))
        keys = [key(entry.get(f'reading{i}Title')) for i in (1, 2, 3)]
        epistles = [k for k in keys if k and k[0] not in GOSPELS]
        gospels = [k for k in keys if k and k[0] in GOSPELS]
        yield (os.path.basename(path)[:10],
               epistles[0] if epistles else None, gospels[0] if gospels else None)


def audit(name, pairs):
    right = wrong = 0
    misses = []

    for date, epistle, gospel in pairs:
        dt = datetime.date.fromisoformat(date)
        if dt.weekday() != 6 or not epistle or not gospel:
            continue

        day = Day(dt.year, dt.month, dt.day, tradition='greek')
        full = [r for r in day.get_readings() if r.source in ('Epistle', 'Gospel')]
        if not any(r.month for r in full):
            continue

        ours = [key(r.pericope.sdisplay) for r in day.get_abbreviated_readings()]
        if ours == [epistle, gospel]:
            right += 1
        else:
            wrong += 1
            misses.append((date, day.feast_level, (day.feasts or [''])[0],
                           [r.pericope.sdisplay for r in day.get_abbreviated_readings()],
                           epistle, gospel))

    print(f'{name}: {right + wrong} Sundays with a proper, {right} right, {wrong} wrong')
    for miss in misses:
        print('  ', *miss)
    print()


audit('goarch.org', goa_pairs())
audit('antiochian.org', antiochian_pairs())
