"""Per-cycle map of weeks-before-Triodion -> Luke-section week actually read.

The back-anchored tail (b-1/b-2/b-3 = 16/15/14) is settled. This lays out what
happens *before* it, in the long seasons where the Luke-section material runs
out before Triodion.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])

import django, re, datetime, collections
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orthocal.settings')
django.setup()
from calendarium.liturgics import GreekYear
from calendarium import datetools

def pd_to_date(Y, pdist):
    j = datetime.date(Y, 1, 1)
    return j + datetime.timedelta(days=datetools.compute_pascha_jdn(Y) - datetools.gregorian_to_jdn(j) + pdist)

TOK = re.compile(r'^(\d\d)-(\d\d)([AB])(\d+)([A-Za-z]{2})$')
cycles = {}
for line in open('data/goarch_pointer_sequences.txt'):
    p = line.split(); Y = int(p[0])
    rows = []
    for t in p[1:]:
        m = TOK.match(t)
        rows.append((datetime.date(Y + 1, int(m.group(1)), int(m.group(2))), m.group(3), int(m.group(4))))
    cycles[Y] = rows

print(f"{'cyc':<5}{'j':>3}{'trio':>5} {'natv':<4} " + ' '.join(f'{f"b{b}":>7}' for b in range(-6, 0)))
for Y in sorted(cycles):
    gy = GreekYear(Y)
    trio_mon = pd_to_date(Y, gy.triodion_start + 1)
    seen = collections.defaultdict(set)
    for dt, sec, wk in cycles[Y]:
        seen[(dt - trio_mon).days // 7].add(f'{sec}{wk}')
    cells = []
    for b in range(-6, 0):
        v = seen.get(b)
        cells.append(('/'.join(sorted(v)) if v else '·'))
    surplus = any(b <= -4 for b in seen)
    print(f'{Y:<5}{gy.lukan_jump:>3}{gy.triodion_start:>5} {datetime.date(Y,12,25).strftime("%a"):<4} '
          + ' '.join(f'{c:>7}' for c in cells) + ('   <- long season' if surplus else ''))
