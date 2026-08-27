"""How far is the Antiochian tradition from antiochian.org, across the whole harvest?

Answers the question the two-day figure does not: the two-day number came from
comparing GOA against Antiochian. This compares *the app's Antiochian output*
against antiochian.org directly, over every harvested day, so we can see the
real size of the gap and what kinds of day it consists of.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])

import asyncio, django, re, json, glob, datetime, collections
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orthocal.settings')
django.setup()
from calendarium.liturgics import Day
from calendarium.datetools import Tradition

# Both sides name books differently: antiochian.org spells them out ("St. Paul's
# Letter to the Ephesians"), the Reading table abbreviates ("Eph 4.7-13"). Map
# both onto one token, keeping the ordinal for the numbered epistles.
BOOKS = [
    ('MATT',  r'MATTHEW|MATT'),        ('MARK', r'MARK'),
    ('LUKE',  r'LUKE'),                ('JOHN', r'JOHN'),
    ('ACTS',  r'ACTS'),                ('ROM',  r'ROMANS|ROM'),
    ('COR',   r'CORINTHIANS|COR'),     ('GAL',  r'GALATIANS|GAL'),
    ('EPH',   r'EPHESIANS|EPH'),       ('PHIL', r'PHILIPPIANS|PHIL'),
    ('COL',   r'COLOSSIANS|COL'),      ('THESS', r'THESSALONIANS|THESS'),
    ('TIM',   r'TIMOTHY|TIM'),         ('TITUS', r'TITUS'),
    ('PHLM',  r'PHILEMON|PHLM'),       ('HEB',  r'HEBREWS|HEB'),
    ('JAS',   r'JAMES|JAS'),           ('PET',  r'PETER|PET'),
    ('JUDE',  r'JUDE'),                ('REV',  r'REVELATION|REV'),
    ('GEN',   r'GENESIS|GEN'),         ('ISA',  r'ISAIAH|ISA'),
    ('PROV',  r'PROVERBS|PROV'),       ('EXOD', r'EXODUS|EXOD'),
    ('JOEL',  r'JOEL'),                ('ZECH', r'ZECHARIAH|ZECH'),
    ('MAL',   r'MALACHI|MAL'),         ('JOB',  r'JOB'),
    ('JONAH', r'JONAH'),               ('DAN',  r'DANIEL|DAN'),
    ('WIS',   r'WISDOM|WIS'),          ('JER',  r'JEREMIAH|JER'),
    ('EZEK',  r'EZEKIEL|EZEK'),        ('MIC',  r'MICAH|MIC'),
    ('KGS',   r'KINGS|KGS'),           ('SAM',  r'SAMUEL|SAM'),
    ('ZEPH',  r'ZEPHANIAH|ZEPH'),      ('HAB',  r'HABAKKUK|HAB'),
]
# JOHN must lose to the epistles of John only via the ordinal, and MATT before
# MARK is irrelevant, but PETER/PET must be tried before PROV etc. -- order the
# alternation longest-first within each pattern instead of relying on list order.
BOOK_RE = [(tok, re.compile(rf'\b(?:{pat})\b')) for tok, pat in BOOKS]

def canon(s):
    if not s: return ''
    u = re.sub(r'[^A-Z0-9:; ,\-]', ' ', s.upper().replace('.', ':'))
    hit = min(
        ((m.start(), tok) for tok, rx in BOOK_RE if (m := rx.search(u))),
        default=None,
    )
    if hit is None: return ''
    pos, book = hit
    o = ''
    head = u[:pos]
    for w, dg in (('THIRD', '3'), ('SECOND', '2'), ('FIRST', '1')):
        if re.search(rf'\b{w}\b', u):
            o = dg; break
    if not o:
        m = re.search(r'\b(I{1,3}|[123])\s*$', head.strip() + ' ') or re.match(r'\s*(I{1,3})\b', u)
        if m:
            tok = m.group(1)
            o = tok if tok.isdigit() else str(len(tok))
    if book in ('JUDE', 'PHLM'):
        o = ''       # antiochian.org writes "St. Jude's FIRST Universal Letter"
    tail = u[pos:]
    m = re.search(r'(\d+):(\d+)', tail)
    if m:
        return f'{o}{book}{m.group(1)}:{m.group(2)}'
    # Jude and Philemon have a single chapter, and this repo cites them without
    # one ("Jude 11-25") where antiochian.org writes "JUDE 1:11-25".
    if book in ('JUDE', 'PHLM'):
        m = re.search(r'(\d+)', tail)
        if m:
            return f'{o}{book}1:{m.group(1)}'
    return ''

def near(a, b):
    if a == b: return True
    if not a or not b: return False
    pa, pb = re.match(r'^(\d?[A-Z]+)(\d+):(\d+)$', a), re.match(r'^(\d?[A-Z]+)(\d+):(\d+)$', b)
    if not (pa and pb): return False
    return pa.group(1) == pb.group(1) and pa.group(2) == pb.group(2) and abs(int(pa.group(3)) - int(pb.group(3))) <= 2

async def main():
    days = []
    for path in sorted(glob.glob('data/antiochian_raw/*.json')):
        d = json.load(open(path))
        days.append((datetime.date.fromisoformat(d['originalCalendarDate']),
                     d.get('reading1Title', ''), d.get('reading2Title', ''), d.get('feastDayTitle', '')))

    stats = collections.Counter()
    misses = []
    for dt, ep_src, gs_src, title in days:
        want_e, want_g = canon(ep_src), canon(gs_src)
        if not want_e and not want_g:
            stats['no readings listed'] += 1
            continue

        # antiochian.org reuses reading1/reading2 for whatever the day has, so
        # two shapes are not Epistle/Gospel at all and must not be compared as
        # though they were:
        #   * aliturgical Lenten weekdays, where the pair is the Vespers Old
        #     Testament readings (Genesis/Isaiah/Proverbs). The app carries
        #     those as source='Vespers'; there is no Epistle or Gospel.
        #   * Holy Week and a few feasts, where reading1 holds the *Matins*
        #     Gospel rather than an Epistle.
        OT = ('GEN', 'ISA', 'PROV', 'EXOD', 'JOEL', 'ZECH', 'MAL', 'JOB',
              'JONAH', 'DAN', 'WIS', 'JER', 'EZEK', 'MIC', 'KGS', 'SAM', 'ZEPH', 'HAB')
        GOSPELS = ('MATT', 'MARK', 'LUKE', 'JOHN')
        book = lambda c: re.sub(r'^\d', '', c or '').rstrip('0123456789:')
        if any(book(x).startswith(OT) for x in (want_e, want_g)):
            stats['vespers-only (aliturgical Lenten weekday)'] += 1
            continue
        if book(want_e) in GOSPELS:
            stats['reading1 is a Matins Gospel, not an Epistle'] += 1
            want_e = ''
        day = Day(dt.year, dt.month, dt.day, tradition=Tradition.Antiochian)
        await day.ainitialize()
        rs = await day.aget_readings()
        got_e = [canon(r.pericope.sdisplay) for r in rs if r.source == 'Epistle']
        got_g = [canon(r.pericope.sdisplay) for r in rs if r.source == 'Gospel']
        e_ok = (not want_e) or any(near(x, want_e) for x in got_e)
        g_ok = (not want_g) or any(near(x, want_g) for x in got_g)
        stats['checked'] += 1
        if e_ok and g_ok:
            stats['match'] += 1
        else:
            stats['differ'] += 1
            misses.append((dt, title, want_e, want_g, got_e, got_g, e_ok, g_ok))

    print(f'app(Antiochian) vs antiochian.org, {stats["checked"]} harvested days with readings')
    print(f'  match : {stats["match"]}  ({stats["match"]/stats["checked"]*100:.1f}%)')
    print(f'  differ: {stats["differ"]}  ({stats["differ"]/stats["checked"]*100:.1f}%)')
    for label in ('no readings listed', 'vespers-only (aliturgical Lenten weekday)',
                  'reading1 is a Matins Gospel, not an Epistle'):
        if stats[label]:
            print(f'  excluded/adjusted: {stats[label]:>4}  {label}')
    print()

    per_year = collections.Counter(dt.year for dt, *_ in misses)
    checked_per_year = collections.Counter()
    for dt, *_ in days:
        checked_per_year[dt.year] += 1
    print('  by calendar year (harvest coverage varies -- 2026 is the only complete one):')
    for y in sorted(checked_per_year):
        print(f'    {y}: {per_year[y]:>3} differ of {checked_per_year[y]:>3} harvested')
    print()

    by_month = collections.Counter(dt.strftime('%m') for dt, *_ in misses)
    print('  differing days by month: ' + ' '.join(f'{m}:{n}' for m, n in sorted(by_month.items())))
    ep_only = sum(1 for *_, e_ok, g_ok in misses if g_ok and not e_ok)
    gs_only = sum(1 for *_, e_ok, g_ok in misses if e_ok and not g_ok)
    print(f'  Epistle only: {ep_only}   Gospel only: {gs_only}   both: {len(misses) - ep_only - gs_only}')
    # Group by (month, day): a difference that recurs on the same calendar date
    # across years is a fixed-Menaion difference and can be carried as an
    # antiochian-tagged row. One that appears in a single year is either a
    # moveable-cycle effect or noise.
    by_date = collections.defaultdict(list)
    for dt, title, we, wg, ge, gg, e_ok, g_ok in misses:
        by_date[(dt.month, dt.day)].append((dt.year, title, we, wg, ge, gg, e_ok, g_ok))

    recurring = {k: v for k, v in by_date.items() if len(v) > 1}
    oneoff = {k: v for k, v in by_date.items() if len(v) == 1}
    print(f'\n  distinct calendar dates involved: {len(by_date)}'
          f'  ({len(recurring)} recur across years, {len(oneoff)} appear once)\n')
    print('  RECURRING -- candidates for antiochian-tagged fixed rows:')
    for (m, d), rows in sorted(recurring.items()):
        yrs = ','.join(str(r[0]) for r in rows)
        _, title, we, wg, ge, gg, e_ok, g_ok = rows[0]
        flag = ('' if e_ok else 'E') + ('' if g_ok else 'G')
        consistent = len({(r[2], r[3]) for r in rows}) == 1
        print(f'    {m:02d}-{d:02d} {flag:<2} x{len(rows)} [{yrs}] {"consistent" if consistent else "VARIES"}'
              f'  {title[:26]:<26} want E={we:<11} G={wg:<11} got E={ge} G={gg}')

asyncio.run(main())
