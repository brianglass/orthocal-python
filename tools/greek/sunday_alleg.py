import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])   # data/ paths below are repo-root relative
import asyncio, django, os, re, json, glob, datetime
os.environ.setdefault('DJANGO_SETTINGS_MODULE','orthocal.settings')
django.setup()
from calendarium.liturgics import Day

def ref(s):
    s = (s or '').upper().replace('.', ':')
    m = re.match(r'\s*(ST\.\s*)?(MATTHEW|MATT|MARK|MK|LUKE|LK|JOHN|JN)\.?\s*(.*)$', s)
    if not m: return None
    book = {'MATTHEW':'MATT','MATT':'MATT','MARK':'MARK','MK':'MARK','LUKE':'LUKE','LK':'LUKE','JOHN':'JOHN','JN':'JOHN'}[m.group(2)]
    v = re.search(r'(\d+)[:.](\d+)', s)
    return (book, int(v.group(1)), int(v.group(2))) if v else (book, 0, 0)

def hit(cands, want):
    w = ref(want)
    return any(ref(c) and ref(c)[0]==w[0] and ref(c)[1]==w[1] and abs(ref(c)[2]-w[2])<=2 for c in cands)

ant = {}
for f in sorted(glob.glob('data/antiochian_raw/*.json')):
    d = json.load(open(f))
    ant[d['originalCalendarDate']] = (d.get('feastDayTitle',''), d.get('reading2Title',''))
goa = {}
for line in open('data/goarch_winter_rows.txt'):
    dte, label, gospel = line.rstrip('\n').split('|')
    goa[dte] = (label, gospel)

async def main():
    both = sorted(set(ant) & set(goa))
    tallies = {'sunday': [0,0,0], 'weekday': [0,0,0]}   # [agrees w/ GOA, agrees w/ ANT, neither]
    notes = []
    for d in both:
        dt = datetime.date.fromisoformat(d)
        if ref(goa[d][1]) == ref(ant[d][1]):
            continue                                   # sources agree: tells us nothing
        day = Day(dt.year, dt.month, dt.day, tradition='greek'); await day.ainitialize()
        got = [r.pericope.sdisplay for r in await day.aget_readings() if r.source == 'Gospel']
        g, a = hit(got, goa[d][1]), hit(got, ant[d][1])
        kind = 'sunday' if dt.weekday() == 6 else 'weekday'
        tallies[kind][0 if g else (1 if a else 2)] += 1
        notes.append((d, dt.strftime('%a'), kind, 'GOA' if g else ('ANT' if a else 'neither'),
                      goa[d][1], ant[d][1], got))
    print('On dates where GOA and Antiochian DISAGREE, which does the app follow?\n')
    for kind in ('sunday', 'weekday'):
        g, a, n = tallies[kind]
        print(f'  {kind:<8} follows GOA: {g}   follows Antiochian: {a}   neither: {n}')
    print()
    for d, wd, kind, who, gg, aa, got in notes:
        print(f'  {d} {wd} {kind:<8} app follows {who:<7} | GOA={gg:<20} ANT={aa:<22} app={got}')

asyncio.run(main())
