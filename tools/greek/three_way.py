"""app vs goarch.org vs antiochian.org on the same dates, for calendar 2026.

Splits the app's errors into two piles that need very different fixes:
  * both sources agree and the app differs -> a shared bug; fixing it helps
    the Greek tradition too, and the row belongs to `greek` (or `common`).
  * the sources disagree -> genuinely jurisdictional; needs an
    `antiochian`-tagged row.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])

import asyncio, django, re, json, glob, datetime, collections
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orthocal.settings')
django.setup()
from calendarium.liturgics import Day
from calendarium.datetools import Tradition

BOOKS = [('MATT', r'MATTHEW|MATT'), ('MARK', r'MARK'), ('LUKE', r'LUKE'), ('JOHN', r'JOHN'),
         ('ACTS', r'ACTS'), ('ROM', r'ROMANS|ROM'), ('COR', r'CORINTHIANS|COR'),
         ('GAL', r'GALATIANS|GAL'), ('EPH', r'EPHESIANS|EPH'), ('PHIL', r'PHILIPPIANS|PHIL'),
         ('COL', r'COLOSSIANS|COL'), ('THESS', r'THESSALONIANS|THESS'), ('TIM', r'TIMOTHY|TIM'),
         ('TITUS', r'TITUS'), ('PHLM', r'PHILEMON|PHLM'), ('HEB', r'HEBREWS|HEB'),
         ('JAS', r'JAMES|JAS'), ('PET', r'PETER|PET'), ('JUDE', r'JUDE'), ('REV', r'REVELATION|REV')]
BOOK_RE = [(t, re.compile(rf'\b(?:{p})\b')) for t, p in BOOKS]
LEGACY = {'ROMA':'ROM','CORI':'COR','GALA':'GAL','EPHE':'EPH','COLO':'COL','THES':'THESS',
          'TIMO':'TIM','TITU':'TITUS','HEBR':'HEB','JAME':'JAS','PETE':'PET','REVE':'REV'}

def canon(s):
    if not s: return ''
    u = re.sub(r'[^A-Z0-9:; ,\-]', ' ', s.upper().replace('.', ':'))
    hit = min(((m.start(), t) for t, rx in BOOK_RE if (m := rx.search(u))), default=None)
    if hit is None: return ''
    pos, book = hit
    o = ''
    for w, dg in (('THIRD','3'), ('SECOND','2'), ('FIRST','1')):
        if re.search(rf'\b{w}\b', u): o = dg; break
    if not o:
        m = re.search(r'\b(I{1,3}|[123])\s*$', u[:pos].strip() + ' ')
        if m: o = m.group(1) if m.group(1).isdigit() else str(len(m.group(1)))
    if book in ('JUDE', 'PHLM'): o = ''
    tail = u[pos:]
    m = re.search(r'(\d+):(\d+)', tail)
    if m: return f'{o}{book}{m.group(1)}:{m.group(2)}'
    if book in ('JUDE', 'PHLM'):
        m = re.search(r'(\d+)', tail)
        if m: return f'{o}{book}1:{m.group(1)}'
    return ''

def retoken(fp):
    m = re.match(r'^(\d?)([A-Z]+)(\d+:\d+)$', fp or '')
    return m.group(1) + LEGACY.get(m.group(2), m.group(2)) + m.group(3) if m else fp

def near(a, b):
    if a == b: return True
    if not a or not b: return False
    pa, pb = (re.match(r'^(\d?[A-Z]+)(\d+):(\d+)$', x) for x in (a, b))
    if not (pa and pb): return False
    return pa.group(1) == pb.group(1) and pa.group(2) == pb.group(2) and abs(int(pa.group(3)) - int(pb.group(3))) <= 2

async def main():
    goa = {}
    for tok in open('data/goa2026.txt').read().split():
        d, e, g = (tok.split(',') + ['', ''])[:3]
        goa[d] = (retoken(e), retoken(g))

    ant = {}
    for path in sorted(glob.glob('data/antiochian_raw/2026-*.json')):
        d = json.load(open(path))
        dt = datetime.date.fromisoformat(d['originalCalendarDate'])
        ant[f'{dt.month:02d}{dt.day:02d}'] = (canon(d.get('reading1Title','')), canon(d.get('reading2Title','')))

    shared, juris = [], []
    for key in sorted(set(goa) & set(ant)):
        ge, gg = goa[key]; ae, ag = ant[key]
        if not (ae or ag) or not (ge or gg):
            continue
        month, dayn = int(key[:2]), int(key[2:])
        day = Day(2026, month, dayn, tradition=Tradition.Antiochian)
        await day.ainitialize()
        rs = await day.aget_readings()
        got_e = [canon(r.pericope.sdisplay) for r in rs if r.source == 'Epistle']
        got_g = [canon(r.pericope.sdisplay) for r in rs if r.source == 'Gospel']
        app_ok = ((not ae or any(near(x, ae) for x in got_e))
                  and (not ag or any(near(x, ag) for x in got_g)))
        if app_ok:
            continue
        sources_agree = near(ge, ae) and near(gg, ag)
        (shared if sources_agree else juris).append(
            (key, ae, ag, ge, gg, got_e, got_g))

    print(f'2026, dates where the app differs from antiochian.org: {len(shared) + len(juris)}\n')
    print(f'  SHARED BUG -- goarch.org agrees with antiochian.org, app differs: {len(shared)}')
    for key, ae, ag, ge, gg, got_e, got_g in shared:
        print(f'    2026-{key[:2]}-{key[2:]}  both sources E={ae:<11} G={ag:<11} app E={got_e} G={got_g}')
    print(f'\n  JURISDICTIONAL -- the two sources disagree: {len(juris)}')
    for key, ae, ag, ge, gg, got_e, got_g in juris:
        print(f'    2026-{key[:2]}-{key[2:]}  ant E={ae:<11} G={ag:<11} | goa E={ge:<11} G={gg:<11} | app E={got_e} G={got_g}')

asyncio.run(main())
