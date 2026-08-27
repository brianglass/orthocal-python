import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])   # data/ paths below are repo-root relative
import django, os, datetime
os.environ.setdefault('DJANGO_SETTINGS_MODULE','orthocal.settings')
django.setup()
from calendarium.liturgics import GreekYear
from calendarium import datetools

def pd_to_date(Y, pdist):
    j = datetime.date(Y, 1, 1)
    return j + datetime.timedelta(days=datetools.compute_pascha_jdn(Y) - datetools.gregorian_to_jdn(j) + pdist)

bad = []
for line in open('data/goarch_sunday_sequences.txt'):
    p = line.split(); Y = int(p[0])
    gy = GreekYear(Y)
    trio = pd_to_date(Y, gy.triodion_start)
    pps = [datetime.date(Y+1, int(t[:2]), int(t[3:5])) for t in p[1:] if t.endswith('=PP')]
    status = 'OK' if pps and pps[-1] == trio and len(pps) == 1 else 'MISMATCH'
    if status == 'MISMATCH':
        bad.append((Y, trio, pps))
print(f'GOA "Triodion Begins Today" vs this project\'s Paschalion, 30 cycles:')
print(f'  aligned: {30 - len(bad)}   mismatched: {len(bad)}\n')
for Y, trio, pps in bad:
    print(f'  cycle {Y}: app Triodion = {trio}, GOA marks PP on {[str(d) for d in pps]}')
