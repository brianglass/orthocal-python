import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])   # data/ paths below are repo-root relative
import asyncio, django, os, re, datetime
os.environ.setdefault('DJANGO_SETTINGS_MODULE','orthocal.settings')
django.setup()
from calendarium.liturgics import Day

def ref(s):
    s = s.upper().replace('.', ':')
    m = re.match(r'\s*(ST\.\s*)?(MATTHEW|MATT|MARK|MK|LUKE|LK|JOHN|JN)\.?\s*(.*)$', s)
    if not m: return None
    book = {'MATTHEW':'MATT','MATT':'MATT','MARK':'MARK','MK':'MARK','LUKE':'LUKE','LK':'LUKE','JOHN':'JOHN','JN':'JOHN'}[m.group(2)]
    v = re.search(r'(\d+)[:.](\d+)', s)
    return (book, int(v.group(1)), int(v.group(2))) if v else (book, 0, 0)

rows = {}
for line in open('data/goarch_winter_rows.txt'):
    d, label, gospel = line.rstrip('\n').split('|')
    rows[d] = (label, gospel)

async def main():
    curated, future = [], []
    for d in sorted(rows):
        label, gospel = rows[d]
        dt = datetime.date.fromisoformat(d)
        day = Day(dt.year, dt.month, dt.day, tradition='greek')
        await day.ainitialize()
        got = [r.pericope.sdisplay for r in await day.aget_readings() if r.source == 'Gospel']
        w = ref(gospel)
        hit = any(ref(g) and ref(g)[0] == w[0] and ref(g)[1] == w[1] and abs(ref(g)[2] - w[2]) <= 2 for g in got)
        (future if dt.year >= 2028 else curated).append((d, label, gospel, got, hit))

    for name, bucket in (('CURATED (GOA hand-supplied, 2011-2027)', curated),
                         ('UNCURATED (GOA pure algorithm, 2028+)', future)):
        bad = [r for r in bucket if not r[4]]
        print(f'\n=== {name}: {len(bucket)} days, {len(bad)} mismatched ===')
        for d, label, gospel, got, _ in bad:
            print(f'  {d} {datetime.date.fromisoformat(d).strftime("%a")}  {label[:32]:<32} goa={gospel:<22} app={got}')

asyncio.run(main())
