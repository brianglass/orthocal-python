import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])   # data/ paths below are repo-root relative
import django, os, datetime, collections
os.environ.setdefault('DJANGO_SETTINGS_MODULE','orthocal.settings')
django.setup()
from calendarium.liturgics import GreekYear

seqs = {}
for line in open('data/goarch_sunday_sequences.txt'):
    p = line.split(); Y = int(p[0])
    seqs[Y] = [(datetime.date(Y+1, int(t[:2]), int(t[3:5])), t.split('=')[1]) for t in p[1:]]

print(f"{'cyc':<5}{'n':>2}{'jump':>5}{'trio':>5}  {'autumn Luke numbers used':<34}{'unused of 12-15':<17} GOA interpolation")
for Y in sorted(seqs):
    gy = GreekYear(Y)
    used = sorted({v for v in gy.lukan_sunday_numbers.values() if v})
    unused = [k for k in (12, 13, 14, 15) if k not in used]
    inner = [c for _, c in seqs[Y][1:] if c not in ('PP',)]
    print(f'{Y:<5}{gy.regular_extra_sundays:>2}{gy.lukan_jump:>5}{gy.triodion_start:>5}  '
          f'{str(used):<34}{str(unused):<17} {" ".join(inner)}')
