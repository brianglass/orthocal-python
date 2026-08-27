"""app(Greek) vs goarch.org over a complete calendar year.

The counterpart to antiochian_gap.py. Together they answer how accurate each
tradition is against its own source of truth, which is the number that matters
when deciding whether a tradition is worth shipping.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])

import asyncio, django, re, collections
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orthocal.settings')
django.setup()
from calendarium.liturgics import Day
from calendarium.datetools import Tradition

BOOKS = [
    ('MATT', r'MATTHEW|MATT'), ('MARK', r'MARK'), ('LUKE', r'LUKE'), ('JOHN', r'JOHN'),
    ('ACTS', r'ACTS'), ('ROM', r'ROMANS|ROM'), ('COR', r'CORINTHIANS|COR'),
    ('GAL', r'GALATIANS|GAL'), ('EPH', r'EPHESIANS|EPH'), ('PHIL', r'PHILIPPIANS|PHIL'),
    ('COL', r'COLOSSIANS|COL'), ('THESS', r'THESSALONIANS|THESS'), ('TIM', r'TIMOTHY|TIM'),
    ('TITUS', r'TITUS'), ('PHLM', r'PHILEMON|PHLM'), ('HEB', r'HEBREWS|HEB'),
    ('JAS', r'JAMES|JAS'), ('PET', r'PETER|PET'), ('JUDE', r'JUDE'), ('REV', r'REVELATION|REV'),
]
BOOK_RE = [(t, re.compile(rf'\b(?:{p})\b')) for t, p in BOOKS]

def canon(s):
    if not s: return ''
    u = re.sub(r'[^A-Z0-9:; ,\-]', ' ', s.upper().replace('.', ':'))
    hit = min(((m.start(), t) for t, rx in BOOK_RE if (m := rx.search(u))), default=None)
    if hit is None: return ''
    pos, book = hit
    o = ''
    for w, dg in (('THIRD', '3'), ('SECOND', '2'), ('FIRST', '1')):
        if re.search(rf'\b{w}\b', u):
            o = dg; break
    if not o:
        m = re.search(r'\b(I{1,3}|[123])\s*$', u[:pos].strip() + ' ')
        if m:
            o = m.group(1) if m.group(1).isdigit() else str(len(m.group(1)))
    m = re.search(r'(\d+):(\d+)', u[pos:])
    return f'{o}{book}{m.group(1)}:{m.group(2)}' if m else ''

def near(a, b):
    if a == b: return True
    if not a or not b: return False
    pa, pb = (re.match(r'^(\d?[A-Z]+)(\d+):(\d+)$', x) for x in (a, b))
    if not (pa and pb): return False
    return (pa.group(1) == pb.group(1) and pa.group(2) == pb.group(2)
            and abs(int(pa.group(3)) - int(pb.group(3))) <= 2)

# data/goa2026.txt was written with an earlier canonicaliser that took the
# first four characters of the spelled-out book name. Translate it onto the
# tokens canon() produces now.
LEGACY = {'ROMA': 'ROM', 'CORI': 'COR', 'GALA': 'GAL', 'EPHE': 'EPH', 'COLO': 'COL',
          'THES': 'THESS', 'TIMO': 'TIM', 'TITU': 'TITUS', 'HEBR': 'HEB',
          'JAME': 'JAS', 'PETE': 'PET', 'REVE': 'REV'}

def retoken(fp):
    m = re.match(r'^(\d?)([A-Z]+)(\d+:\d+)$', fp or '')
    if not m:
        return fp
    return m.group(1) + LEGACY.get(m.group(2), m.group(2)) + m.group(3)


async def main():
    src = {}
    for tok in open('data/goa2026.txt').read().split():
        d, e, g = (tok.split(',') + ['', ''])[:3]
        src[d] = (retoken(e), retoken(g))

    stats = collections.Counter()
    misses = []
    for key in sorted(src):
        want_e, want_g = src[key]
        if not want_e and not want_g:
            stats['no readings listed'] += 1
            continue
        month, dayn = int(key[:2]), int(key[2:])
        day = Day(2026, month, dayn, tradition=Tradition.Greek)
        await day.ainitialize()
        rs = await day.aget_readings()
        got_e = [canon(r.pericope.sdisplay) for r in rs if r.source == 'Epistle']
        got_g = [canon(r.pericope.sdisplay) for r in rs if r.source == 'Gospel']
        e_ok = (not want_e) or any(near(x, want_e) for x in got_e)
        g_ok = (not want_g) or any(near(x, want_g) for x in got_g)
        stats['checked'] += 1
        stats['match' if (e_ok and g_ok) else 'differ'] += 1
        if not (e_ok and g_ok):
            misses.append((key, want_e, want_g, got_e, got_g, e_ok, g_ok))

    print(f'app(Greek) vs goarch.org, calendar 2026: {stats["checked"]} days compared')
    print(f'  match : {stats["match"]}  ({stats["match"]/stats["checked"]*100:.1f}%)')
    print(f'  differ: {stats["differ"]}\n')
    for key, we, wg, ge, gg, e_ok, g_ok in misses:
        flag = ('' if e_ok else 'E') + ('' if g_ok else 'G')
        print(f'  2026-{key[:2]}-{key[2:]} {flag:<2} want E={we:<11} G={wg:<11} got E={ge} G={gg}')

asyncio.run(main())
