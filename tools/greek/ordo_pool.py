"""Do the curated Jan 19/24/26 Gospels drain a computable pool?

The standing hypothesis (finding #7 in the doc) is that they are Matthew
Sundays the Lukan jump skipped, recovered later as weekdays. This tests it
against goarch.org's curated years with the Sunday-side accounting now
understood: which Matthew Sundays did the autumn actually read, and which did
the Theophany interpolation consume?
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])

import django, re, datetime
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orthocal.settings')
django.setup()
from calendarium.liturgics import GreekYear

MT = {2:'Matthew 4:18-23', 3:'Matthew 6:22-33', 4:'Matthew 8:5-13', 5:'Matthew 8:28-34; 9:1',
      6:'Matthew 9:1-8', 7:'Matthew 9:27-35', 8:'Matthew 14:14-22', 9:'Matthew 14:22-34',
      10:'Matthew 17:14-23', 11:'Matthew 18:23-35', 12:'Matthew 19:16-26', 13:'Matthew 21:33-42',
      14:'Matthew 22:2-14', 15:'Matthew 22:35-46', 16:'Matthew 25:14-30', 17:'Matthew 15:21-28'}
INV = {v: k for k, v in MT.items()}

goa = {}
for line in open('data/goarch_winter_rows.txt'):
    d, label, gospel = line.rstrip('\n').split('|')
    goa[d] = gospel

print(f"{'cyc':<5}{'jump':>5}{'last Mt read':>13}{'interp uses':>13}   {'pool':<18} Jan19 / Jan24 / Jan26")
for Y in range(2010, 2027):
    gy = GreekYear(Y)
    last_mt = (gy.first_sun_luke - 56) // 7            # last Matthew Sunday read in the autumn
    interp_mt = {n for book, n in gy.interpolation_sequence if book == 'matthew'}
    pool = [n for n in range(last_mt + 1, 17) if n not in interp_mt]
    obs = []
    for dd in (19, 24, 26):
        g = goa.get(f'{Y+1}-01-{dd:02d}')
        if g is None:
            obs.append('--')
        elif g in INV:
            obs.append(f'{INV[g]}M')
        else:
            obs.append('ord')
    print(f'{Y:<5}{gy.lukan_jump:>5}{last_mt:>13}{str(sorted(interp_mt)):>13}   {str(pool):<18} ' + ' / '.join(f'{o:>4}' for o in obs))
