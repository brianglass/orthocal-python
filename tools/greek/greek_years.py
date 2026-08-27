import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])   # data/ paths below are repo-root relative
import django, os, datetime
os.environ.setdefault('DJANGO_SETTINGS_MODULE','orthocal.settings')
django.setup()
from calendarium.liturgics import GreekYear

have = {2018,2020,2021,2022,2023,2024,2025}  # cycles with some GOA data already
print(f"{'cycle':<6}{'jump':>5}{'j/7':>4}{'extraS':>7}{'regS':>5}{'trio':>6}  {'Jan19':<4}{'Jan24':<4}{'Jan26':<4}  free  interp")
for y in range(2010,2031):
    gy=GreekYear(y)
    wd=lambda d: datetime.date(y+1,1,d).strftime('%a')
    free=[d for d in (19,24,26) if datetime.date(y+1,1,d).weekday()<5]
    try: interp=gy.theophany_interpolation
    except Exception as e: interp=f'ERR'
    mark='*' if y in have else ' '
    keys=sorted(interp) if isinstance(interp,dict) else []
    summary=[interp[k] for k in keys] if keys else []
    print(f'{y}{mark:<2}{gy.lukan_jump:>5}{gy.lukan_jump//7:>4}{gy.greek_extra_sundays:>7}{gy.regular_extra_sundays:>5}{gy.triodion_start:>6}  {wd(19):<4}{wd(24):<4}{wd(26):<4}  {len(free):<4}  {summary}')
