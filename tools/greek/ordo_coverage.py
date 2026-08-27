"""What curated-ordo data do we already hold, and what would an overlay need?"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])

import asyncio, django, re, datetime
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orthocal.settings')
django.setup()
from calendarium.liturgics import Day

rows = {}
for line in open('data/goarch_winter_rows.txt'):
    d, label, gospel = line.rstrip('\n').split('|')
    rows[d] = (label, gospel)

def ref(s):
    s = (s or '').upper().replace('.', ':')
    m = re.match(r'\s*(ST\.\s*)?(MATTHEW|MATT|MARK|MK|LUKE|LK|JOHN|JN)\.?\s*(.*)$', s)
    if not m: return None
    b = {'MATTHEW':'MATT','MATT':'MATT','MARK':'MARK','MK':'MARK','LUKE':'LUKE','LK':'LUKE','JOHN':'JOHN','JN':'JOHN'}[m.group(2)]
    v = re.search(r'(\d+)[:.](\d+)', s)
    return (b, int(v.group(1)), int(v.group(2))) if v else (b, 0, 0)

async def main():
    print(f"{'date':<12}{'GOA gospel':<22}{'app currently shows':<34} needs override?")
    need = have = 0
    for year in range(2011, 2028):
        for dd in (19, 24, 26):
            key = f'{year}-01-{dd:02d}'
            if key not in rows:
                print(f'  {key}   -- NOT HARVESTED --'); continue
            label, gospel = rows[key]
            dt = datetime.date(year, 1, dd)
            if dt.weekday() == 6:
                continue                       # Sundays are the Sunday mechanism, not the ordo
            day = Day(year, 1, dd, tradition='greek'); await day.ainitialize()
            got = [r.pericope.sdisplay for r in await day.aget_readings() if r.source == 'Gospel']
            w = ref(gospel)
            ok = any(ref(g) and ref(g)[0] == w[0] and ref(g)[1] == w[1] and abs(ref(g)[2] - w[2]) <= 2 for g in got)
            have += ok; need += not ok
            print(f'  {key} {gospel:<22}{str(got):<34}{"" if ok else "OVERRIDE"}')
    print(f'\n  weekday ordo slots checked: {have + need}   already correct: {have}   need an override: {need}')

asyncio.run(main())
