import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])   # data/ paths below are repo-root relative
import asyncio, django, os, re, datetime, collections
os.environ.setdefault('DJANGO_SETTINGS_MODULE','orthocal.settings')
django.setup()
from calendarium.liturgics import GreekYear, Day
from calendarium import datetools

def pascha_date(y):
    jan1 = datetime.date(y, 1, 1)
    return jan1 + datetime.timedelta(days=datetools.compute_pascha_jdn(y) - datetools.gregorian_to_jdn(jan1))

LBL = re.compile(r'^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday) of the (\d+)(?:st|nd|rd|th) Week$')
ALBL = re.compile(r'^(\d+)(?:st|nd|rd|th) (Monday|Tuesday|Wednesday|Thursday|Friday|Saturday) after Pentecost$')

# (section, week, weekday) -> gospel, learned from the GOA rows we hold
slotmap = {}
for line in open('data/goarch_winter_rows.txt'):
    d, label, gospel = line.rstrip('\n').split('|')
    if m := LBL.match(label):   slotmap[('B', int(m.group(2)), m.group(1))] = gospel
    elif m := ALBL.match(label): slotmap[('A', int(m.group(1)), m.group(2))] = gospel

TOK = re.compile(r'^(\d\d)-(\d\d)([AB])(\d+)([A-Za-z]{2})$')
WD = {'Mo':'Monday','Tu':'Tuesday','We':'Wednesday','Th':'Thursday','Fr':'Friday','Sa':'Saturday'}
obs = collections.defaultdict(list)
for line in open('data/goarch_pointer_sequences.txt'):
    p = line.split(); Y = int(p[0])
    for tok in p[1:]:
        m = TOK.match(tok)
        obs[Y].append((datetime.date(Y+1,int(m.group(1)),int(m.group(2))), m.group(3), int(m.group(4)), WD[m.group(5)]))

def ref(s):
    s = s.upper().replace('.', ':')
    m = re.match(r'\s*(ST\.\s*)?(MATTHEW|MATT|MARK|MK|LUKE|LK|JOHN|JN)\.?\s*(.*)$', s)
    if not m: return None
    book = {'MATTHEW':'MATT','MATT':'MATT','MARK':'MARK','MK':'MARK','LUKE':'LUKE','LK':'LUKE','JOHN':'JOHN','JN':'JOHN'}[m.group(2)]
    v = re.search(r'(\d+)[:.](\d+)', s)
    return (book, int(v.group(1)), int(v.group(2))) if v else (book, 0, 0)

async def main():
    res = collections.Counter(); misses = []
    unresolved = 0
    for Y in sorted(obs):
        trio_mon = pascha_date(Y) + datetime.timedelta(days=GreekYear(Y).triodion_start + 1)
        for dt, sec, wk, wd in obs[Y]:
            expected = slotmap.get((sec, wk, wd))
            if not expected: unresolved += 1; continue
            b = (dt - trio_mon).days // 7
            day = Day(dt.year, dt.month, dt.day, tradition='greek'); await day.ainitialize()
            got = [r.pericope.sdisplay for r in await day.aget_readings() if r.source == 'Gospel']
            w = ref(expected)
            hit = any(ref(g) and ref(g)[0] == w[0] and ref(g)[1] == w[1] and abs(ref(g)[2]-w[2]) <= 2 for g in got)
            zone = 'b>=-3 (back-anchored)' if b >= -3 else 'b<=-4 (surplus)'
            res[(zone, hit)] += 1
            if not hit: misses.append((dt, b, f'{sec}{wk} {wd[:3]}', expected, got))
    print(f'unresolved slots (no citation known): {unresolved}')
    for zone in ('b>=-3 (back-anchored)', 'b<=-4 (surplus)'):
        ok, bad = res[(zone, True)], res[(zone, False)]
        print(f'{zone:<24} {ok+bad:>3} days  correct={ok:<3} wrong={bad}')
    print('\nmismatches:')
    for dt, b, slot, exp, got in misses:
        print(f'  {dt} b{b:<3} {slot:<9} goa={exp:<22} app={got}')

asyncio.run(main())
