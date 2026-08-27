import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])   # data/ paths below are repo-root relative
import asyncio, django, os, re, datetime, collections
os.environ.setdefault('DJANGO_SETTINGS_MODULE','orthocal.settings')
django.setup()
from calendarium.liturgics import GreekYear, Day
from calendarium import datetools

def pascha_date(y):
    j = datetime.date(y,1,1)
    return j + datetime.timedelta(days=datetools.compute_pascha_jdn(y) - datetools.gregorian_to_jdn(j))

LBL = re.compile(r'^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday) of the (\d+)(?:st|nd|rd|th) Week$')
slot = {}
for line in open('data/goarch_winter_rows.txt'):
    d, label, gospel = line.rstrip('\n').split('|')
    if m := LBL.match(label):
        slot.setdefault((int(m.group(2)), m.group(1)), set()).add(gospel)

print('Greek Luke-section tail, weeks 14-16 (from GOA labels):')
for wk in (14, 15, 16):
    for wd in ('Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'):
        v = slot.get((wk, wd))
        if v: print(f'  ({wk}, {wd!r}): {sorted(v)}')

# Pick concrete sample dates in the b-1/b-2/b-3 zone, spread over jumps, and
# report the app's own sdisplay so the test can assert on stable strings.
TOK = re.compile(r'^(\d\d)-(\d\d)([AB])(\d+)([A-Za-z]{2})$')
WD = {'Mo':'Monday','Tu':'Tuesday','We':'Wednesday','Th':'Thursday','Fr':'Friday','Sa':'Saturday'}
obs = collections.defaultdict(list)
for line in open('data/goarch_pointer_sequences.txt'):
    p = line.split(); Y = int(p[0])
    for tok in p[1:]:
        m = TOK.match(tok)
        obs[Y].append((datetime.date(Y+1,int(m.group(1)),int(m.group(2))), m.group(3), int(m.group(4)), WD[m.group(5)]))

async def main():
    print('\nsample assertions (date, expected B-week/weekday, app sdisplay):')
    seen = set()
    for Y in sorted(obs):
        gy = GreekYear(Y)
        trio_mon = pascha_date(Y) + datetime.timedelta(days=gy.triodion_start + 1)
        for dt, sec, wk, wd in obs[Y]:
            b = (dt - trio_mon).days // 7
            if sec != 'B' or b < -3: continue
            key = (gy.lukan_jump, b, wd)
            if key in seen: continue
            seen.add(key)
            day = Day(dt.year, dt.month, dt.day, tradition='greek'); await day.ainitialize()
            got = [r.pericope.sdisplay for r in await day.aget_readings() if r.source == 'Gospel']
            print(f'    ({dt.year}, {dt.month}, {dt.day}, {wk}, {wd!r:<11}, {got!r}),   # jump={gy.lukan_jump} b={b}')
asyncio.run(main())
