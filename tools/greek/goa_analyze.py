import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])   # data/ paths below are repo-root relative
import django, os, re, datetime, collections
os.environ.setdefault('DJANGO_SETTINGS_MODULE','orthocal.settings')
django.setup()
from calendarium.liturgics import GreekYear

MT = {2:'Matthew 4:18-23',3:'Matthew 6:22-33',4:'Matthew 8:5-13',5:'Matthew 8:28-34; 9:1',
      6:'Matthew 9:1-8',7:'Matthew 9:27-35',8:'Matthew 14:14-22',9:'Matthew 14:22-34',
      10:'Matthew 17:14-23',11:'Matthew 18:23-35',12:'Matthew 19:16-26',13:'Matthew 21:33-42',
      14:'Matthew 22:2-14',15:'Matthew 22:35-46',16:'Matthew 25:14-30',17:'Matthew 15:21-28'}
MT_INV = {v:k for k,v in MT.items()}
LK_INV = {'Luke 17:12-19':12,'Luke 18:18-27':13,'Luke 18:35-43':14,'Luke 19:1-10':15}

SLOT = re.compile(r'^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday) of the (\d+)(?:st|nd|rd|th) Week$')

rows = {}
for line in open('data/goarch_winter_rows.txt'):
    d, label, gospel = line.rstrip('\n').split('|')
    rows[d] = (label, gospel)

def first_sun_luke(y):
    e = datetime.date(y,9,14)
    return e + datetime.timedelta(days=(6-e.weekday()) % 7 or 7) + datetime.timedelta(days=7)

print('=== Jan 19 / 24 / 26: what content appears, vs cycle parameters ===')
print(f"{'cyc':<5}{'jump':>5}{'j/7':>4}{'regS':>5}{'trio':>6}  " + '  '.join(f'{d:<22}' for d in ('Jan19','Jan24','Jan26')))
for cy in range(2010, 2031):
    gy = GreekYear(cy)
    cells = []
    for dd in (19, 24, 26):
        key = f'{cy+1}-01-{dd:02d}'
        if key not in rows:
            cells.append('(no data)'); continue
        label, gospel = rows[key]
        wd = datetime.date(cy+1,1,dd).strftime('%a')
        if gospel in MT_INV:  tag = f'Mt#{MT_INV[gospel]}'
        elif gospel in LK_INV: tag = f'Lk#{LK_INV[gospel]}'
        else: tag = 'ordinary'
        m = SLOT.match(label)
        slot = f'B{m.group(2)}' if m else ('SUN' if 'Sunday' in label else '--')
        cells.append(f'{wd} {slot:<4} {tag}')
    print(f'{cy:<5}{gy.lukan_jump:>5}{gy.lukan_jump//7:>4}{gy.regular_extra_sundays:>5}{gy.triodion_start:>6}  ' + '  '.join(f'{c:<22}' for c in cells))

print()
print('=== February Format-B pointer: label week vs calendar week since the jump ===')
for cy in range(2010, 2031):
    wk1mon = first_sun_luke(cy) + datetime.timedelta(days=1)
    lags = []
    for d, (label, gospel) in sorted(rows.items()):
        dt = datetime.date.fromisoformat(d)
        if not (datetime.date(cy+1,1,14) <= dt <= datetime.date(cy+1,3,15)): continue
        m = SLOT.match(label)
        if not m: continue
        calwk = (dt - wk1mon).days // 7 + 1
        lags.append((d, int(m.group(2)), calwk, calwk - int(m.group(2))))
    if lags:
        gy = GreekYear(cy)
        print(f'  cycle {cy} jump={gy.lukan_jump:<3} lags={sorted({l[3] for l in lags})}  '
              f'({len(lags)} slot days, first {lags[0][0]} B{lags[0][1]})')
