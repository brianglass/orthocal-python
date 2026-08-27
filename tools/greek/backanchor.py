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
obs = collections.defaultdict(list)
for line in open('data/goarch_pointer_sequences.txt'):
    p = line.split(); Y = int(p[0])
    for tok in p[1:]:
        m = TOK.match(tok)
        obs[Y].append((datetime.date(Y+1, int(m.group(1)), int(m.group(2))), m.group(3), int(m.group(4))))

# weeks-before-Triodion -> observed (section, week)
bucket = collections.defaultdict(collections.Counter)
for Y, rows in obs.items():
    trio_mon = pascha_date(Y) + datetime.timedelta(days=GreekYear(Y).triodion_start + 1)
    for dt, sec, wk in rows:
        bucket[(dt - trio_mon).days // 7][f'{sec}{wk}'] += 1

print('weeks before Triodion -> which lectionary week is read')
for b in sorted(bucket, reverse=True):
    items = bucket[b].most_common()
    tot = sum(c for _, c in items)
    verdict = 'CONSISTENT' if len(items) == 1 else 'varies'
    print(f'  b{b:<3} n={tot:<3} {verdict:<11} ' + ', '.join(f'{k}x{c}' for k, c in items))

print('\nsurplus region (b <= -4) detail, by cycle parameters:')
for Y in sorted(obs):
    gy = GreekYear(Y)
    trio_mon = pascha_date(Y) + datetime.timedelta(days=gy.triodion_start + 1)
    sur = [(dt, sec, wk, (dt - trio_mon).days // 7) for dt, sec, wk in obs[Y] if (dt - trio_mon).days // 7 <= -4]
    if sur:
        print(f'  cycle {Y} jump={gy.lukan_jump:<3} trio={gy.triodion_start} nativity={datetime.date(Y,12,25).strftime("%a")}: '
              + ' '.join(f'b{b}={s}{w}' for _, s, w, b in sur))
