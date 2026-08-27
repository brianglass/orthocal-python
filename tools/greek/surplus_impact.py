"""How many days per year actually fall in the surplus region?

The audit can only *observe* Jan 24/26 (every other date in the span carries a
fixed commemoration, so goarch.org prints the saint's name instead of a week
label). But the app still shows a continuous-cycle reading alongside the
saint's on those days, so the user-visible cost is the whole span, not just
the observable part.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])

import django, datetime
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orthocal.settings')
django.setup()
from calendarium.liturgics import GreekYear
from calendarium import datetools

def pd_to_date(Y, pdist):
    j = datetime.date(Y, 1, 1)
    return j + datetime.timedelta(days=datetools.compute_pascha_jdn(Y) - datetools.gregorian_to_jdn(j) + pdist)

START, END = 2010, 2060
total_days = long_cycles = 0
rows = []
for Y in range(START, END):
    gy = GreekYear(Y)
    trio = pd_to_date(Y, gy.triodion_start)
    trio_mon = trio + datetime.timedelta(days=1)
    leavetaking = pd_to_date(Y, gy.theophany + 8)
    # weekdays (Mon-Sat) strictly after Leavetaking and before Triodion that sit
    # at b <= -4, i.e. outside the proven back-anchored tail
    n = 0
    d = leavetaking + datetime.timedelta(days=1)
    while d < trio:
        if d.weekday() != 6 and (d - trio_mon).days // 7 <= -4:
            n += 1
        d += datetime.timedelta(days=1)
    if n:
        long_cycles += 1
        rows.append((Y, gy.lukan_jump, gy.triodion_start, n))
    total_days += n

print(f'Surplus-region weekdays, cycles {START}-{END - 1} ({END - START} cycles):\n')
for Y, j, t, n in rows:
    print(f'  cycle {Y}  jump={j:<3} trio={t}  {n} weekdays affected')
print(f'\n  {long_cycles} of {END - START} cycles are affected ({long_cycles/(END - START)*100:.0f}%)')
print(f'  {total_days} affected weekdays over {END - START} years'
      f' = {total_days/(END - START):.2f} per year on average')
print(f'  when a cycle is affected: {total_days/long_cycles:.1f} days that year')
