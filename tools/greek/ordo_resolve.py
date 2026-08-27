"""Resolve each curated-ordo Gospel to a pdist in the existing Reading table.

If every one resolves, the overlay can reuse the sunday_gospel_override
pattern -- a (year, month, day) -> pdist table consulted by Day.gospel_pdist --
with no schema change and no new Pericope rows, and the ordinary cycle reading
is replaced rather than listed alongside.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])

import django, re, datetime, collections
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orthocal.settings')
django.setup()
from calendarium.models import Reading

def ref(s):
    s = (s or '').upper().replace('.', ':')
    m = re.match(r'\s*(ST\.\s*)?(MATTHEW|MATT|MARK|MK|LUKE|LK|JOHN|JN)\.?\s*(.*)$', s)
    if not m: return None
    b = {'MATTHEW':'MATT','MATT':'MATT','MARK':'MARK','MK':'MARK','LUKE':'LUKE','LK':'LUKE','JOHN':'JOHN','JN':'JOHN'}[m.group(2)]
    v = re.search(r'(\d+)[:.](\d+)', s)
    return (b, int(v.group(1)), int(v.group(2))) if v else None

rows = {}
for line in open('data/goarch_winter_rows.txt'):
    d, label, gospel = line.rstrip('\n').split('|')
    rows[d] = gospel

# index every Gospel row in the shared table by its opening reference
index = collections.defaultdict(list)
for r in Reading.objects.filter(source='Gospel').select_related('pericope'):
    k = ref(r.pericope.sdisplay)
    if k:
        index[k].append(r)

print(f"{'date':<12}{'ordo gospel':<22}{'-> pdist candidates':<28}resolution")
unresolved = []
table = []
for year in range(2011, 2028):
    for dd in (19, 24, 26):
        key = f'{year}-01-{dd:02d}'
        if key not in rows or datetime.date(year, 1, dd).weekday() == 6:
            continue
        want = ref(rows[key])
        cands = [r for k, rs in index.items() if k[0] == want[0] and k[1] == want[1] and abs(k[2] - want[2]) <= 2 for r in rs]
        pdists = sorted({r.pdist for r in cands if 0 <= r.pdist < 500})
        if len(pdists) == 1:
            table.append((year, 1, dd, pdists[0], rows[key]))
            note = f'pdist {pdists[0]}'
        elif not pdists:
            unresolved.append((key, rows[key], sorted({r.pdist for r in cands})))
            note = 'UNRESOLVED'
        else:
            table.append((year, 1, dd, pdists[0], rows[key]))
            note = f'ambiguous {pdists} -> using {pdists[0]}'
        print(f'  {key} {rows[key]:<22}{str(pdists):<28}{note}')

print(f'\nresolved {len(table)} of {len(table) + len(unresolved)}')
for k, g, allp in unresolved:
    print(f'  UNRESOLVED {k}  {g}   (all pdists seen: {allp})')

# --- emit the table in the form year.py wants -------------------------------
print('\n\n--- _GREEK_ORDO_GOSPEL ---')
by_year = collections.defaultdict(list)
for y, m, d, pd, cit in table:
    by_year[y].append((m, d, pd, cit))
for y in sorted(by_year):
    for m, d, pd, cit in sorted(by_year[y]):
        print(f'        ({y}, {m}, {d}): {pd},   # {cit}')
