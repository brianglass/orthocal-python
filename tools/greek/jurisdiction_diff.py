import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])   # data/ paths below are repo-root relative
import django, os, re, json, glob, datetime, collections
os.environ.setdefault('DJANGO_SETTINGS_MODULE','orthocal.settings')
django.setup()
from calendarium.liturgics import GreekYear
from calendarium import datetools

def pascha_date(y):
    j = datetime.date(y, 1, 1)
    return j + datetime.timedelta(days=datetools.compute_pascha_jdn(y) - datetools.gregorian_to_jdn(j))

WD = 'MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY'
A = re.compile(rf'^(\d+)(?:ST|ND|RD|TH)\s+({WD})\s+AFTER PENTECOST$')   # Matthew section
B = re.compile(rf'^({WD})\s+OF THE\s+(\d+)(?:ST|ND|RD|TH)\s+WEEK$')      # Luke section

rows = []
for f in sorted(glob.glob('data/antiochian_raw/*.json')):
    d = json.load(open(f))
    t = d.get('feastDayTitle', '').upper().strip()
    dt = datetime.date.fromisoformat(d['originalCalendarDate'])
    if m := A.match(t):   rows.append((dt, 'A', int(m.group(1)), d.get('reading2Title','')))
    elif m := B.match(t): rows.append((dt, 'B', int(m.group(2)), d.get('reading2Title','')))

print('ANTIOCHIAN labelled days in the pre-Triodion window, by weeks-before-Triodion:')
bucket = collections.defaultdict(collections.Counter)
detail = collections.defaultdict(list)
for dt, sec, wk, cit in rows:
    # only the winter window: Jan 14 through Triodion
    if not (dt.month in (1, 2, 3)):
        continue
    cycle = dt.year - 1
    gy = GreekYear(cycle)
    trio_mon = pascha_date(cycle) + datetime.timedelta(days=gy.triodion_start + 1)
    b = (dt - trio_mon).days // 7
    if b > -1 or b < -8:
        continue
    bucket[b][f'{sec}{wk}'] += 1
    detail[b].append((dt, f'{sec}{wk}', cit, gy.lukan_jump, gy.triodion_start))

for b in sorted(bucket, reverse=True):
    items = bucket[b].most_common()
    goa = {-1: 'B16', -2: 'B15', -3: 'B14'}.get(b, '(surplus)')
    print(f'\n  b{b}  GOA rule says {goa}')
    for k, c in items:
        flag = '  <-- MATCHES GOA' if k == goa else '  <-- DIFFERS'
        print(f'      {k} x{c}{flag}')
    for dt, k, cit, jump, trio in sorted(detail[b]):
        print(f'        {dt} {dt.strftime("%a")} {k:<4} jump={jump:<3} trio={trio}  {cit}')
