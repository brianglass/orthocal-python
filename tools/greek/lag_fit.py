import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])   # data/ paths below are repo-root relative
import django, os, re, datetime, collections
os.environ.setdefault('DJANGO_SETTINGS_MODULE','orthocal.settings')
django.setup()
from calendarium.liturgics import GreekYear
from calendarium import datetools

def pascha_date(y):
    jan1 = datetime.date(y, 1, 1)
    return jan1 + datetime.timedelta(days=datetools.compute_pascha_jdn(y) - datetools.gregorian_to_jdn(jan1))

TOK = re.compile(r'^(\d\d)-(\d\d)([AB])(\d+)([A-Za-z]{2})$')

def first_sun_luke(y):
    e = datetime.date(y, 9, 14)
    return e + datetime.timedelta(days=(6 - e.weekday()) % 7 or 7) + datetime.timedelta(days=7)

cycles = {}
for line in open('data/goarch_pointer_sequences.txt'):
    parts = line.split()
    Y = int(parts[0]); obs = []
    for tok in parts[1:]:
        m = TOK.match(tok)
        obs.append((datetime.date(Y + 1, int(m.group(1)), int(m.group(2))), m.group(3), int(m.group(4))))
    cycles[Y] = obs

print(f"{'cyc':<5}{'jump':>5}{'trio':>6}{'triodate':>12}{'natv':>5}  observations (date -> week), with week counted BACK from Triodion")
for Y, obs in sorted(cycles.items()):
    gy = GreekYear(Y)
    # triodion_start is a pdist relative to this GreekYear's pascha
    trio = pascha_date(Y) + datetime.timedelta(days=gy.triodion_start)
    natv = datetime.date(Y, 12, 25).strftime('%a')
    cells = []
    for dt, sec, wk in obs:
        trio_mon = trio + datetime.timedelta(days=1)
        back = (dt - trio_mon).days // 7          # 0 = week starting the Monday after Triodion Sunday
        calwk = (dt - (first_sun_luke(Y) + datetime.timedelta(days=1))).days // 7 + 1
        cells.append(f'{dt.strftime("%m-%d")}={sec}{wk}[c{calwk} b{back}]')
    print(f'{Y:<5}{gy.lukan_jump:>5}{gy.triodion_start:>6}{str(trio):>12}{natv:>5}  ' + ' '.join(cells))
