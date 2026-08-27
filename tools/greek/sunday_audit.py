import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])   # data/ paths below are repo-root relative
import asyncio, django, os, re, datetime
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

SUN = re.compile(r'^(\d+)(?:st|nd|rd|th) Sunday of (Matthew|Luke)$')
rows = []
for line in open('data/goarch_winter_rows.txt'):
    d, label, gospel = line.rstrip('\n').split('|')
    if SUN.match(label) or 'Canaanite' in label or 'Publican' in label:
        rows.append((d, label, gospel))

async def main():
    ok = bad = 0; misses = []
    for d, label, gospel in sorted(rows):
        dt = datetime.date.fromisoformat(d)
        day = Day(dt.year, dt.month, dt.day, tradition='greek'); await day.ainitialize()
        got = [r.pericope.sdisplay for r in await day.aget_readings() if r.source == 'Gospel']
        if hit(got, gospel): ok += 1
        else: bad += 1; misses.append((d, label, gospel, got))
    print(f'GOA Sundays in the Theophany->Triodion window: {ok+bad} checked, {ok} match, {bad} differ\n')
    for d, label, gospel, got in misses:
        print(f'  {d}  GOA={label:<26} {gospel:<22} app={got}')
asyncio.run(main())
