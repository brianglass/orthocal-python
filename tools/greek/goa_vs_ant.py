import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])   # data/ paths below are repo-root relative
import django, os, re, json, glob, datetime
os.environ.setdefault('DJANGO_SETTINGS_MODULE','orthocal.settings')
django.setup()
from calendarium.liturgics import GreekYear
from calendarium import datetools

def pascha_date(y):
    j = datetime.date(y, 1, 1)
    return j + datetime.timedelta(days=datetools.compute_pascha_jdn(y) - datetools.gregorian_to_jdn(j))

def ref(s):
    s = (s or '').upper().replace('.', ':')
    m = re.match(r'\s*(ST\.\s*)?(MATTHEW|MATT|MARK|MK|LUKE|LK|JOHN|JN)\.?\s*(.*)$', s)
    if not m: return None
    book = {'MATTHEW':'MATT','MATT':'MATT','MARK':'MARK','MK':'MARK','LUKE':'LUKE','LK':'LUKE','JOHN':'JOHN','JN':'JOHN'}[m.group(2)]
    v = re.search(r'(\d+)[:.](\d+)', s)
    return (book, int(v.group(1)), int(v.group(2))) if v else (book, 0, 0)

def same(a, b):
    ra, rb = ref(a), ref(b)
    return bool(ra and rb and ra[0] == rb[0] and ra[1] == rb[1] and abs(ra[2] - rb[2]) <= 2)

ant = {}
for f in sorted(glob.glob('data/antiochian_raw/*.json')):
    d = json.load(open(f))
    ant[d['originalCalendarDate']] = (d.get('feastDayTitle',''), d.get('reading2Title',''))

goa = {}
for line in open('data/goarch_winter_rows.txt'):
    dte, label, gospel = line.rstrip('\n').split('|')
    goa[dte] = (label, gospel)

both = sorted(set(ant) & set(goa))
agree = [d for d in both if same(ant[d][1], goa[d][1])]
diff  = [d for d in both if not same(ant[d][1], goa[d][1])]
print(f'dates held by BOTH sources in the winter window: {len(both)}')
print(f'  same Gospel: {len(agree)}   different Gospel: {len(diff)}\n')
for d in diff:
    dt = datetime.date.fromisoformat(d)
    cycle = dt.year - 1
    gy = GreekYear(cycle)
    trio_mon = pascha_date(cycle) + datetime.timedelta(days=gy.triodion_start + 1)
    b = (dt - trio_mon).days // 7
    print(f'  {d} {dt.strftime("%a")} b{b:<3} jump={gy.lukan_jump:<3} trio={gy.triodion_start}')
    print(f'      GOA : {goa[d][0][:34]:<34} {goa[d][1]}')
    print(f'      ANT : {ant[d][0][:34]:<34} {ant[d][1]}')
