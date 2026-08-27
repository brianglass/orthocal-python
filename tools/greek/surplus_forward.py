"""Test whether the surplus weeks are the forward pointer still running.

Through December the Luke-section pointer satisfies label_week = calendar_week + 1
with no exceptions (see greek_labels.py). This asks the obvious question: does
that forward pointer simply keep running through January, with the back-anchored
14/15/16 tail overriding only the last three weeks?
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

def first_sun_luke(y):
    e = datetime.date(y, 9, 14)
    return e + datetime.timedelta(days=(6 - e.weekday()) % 7 or 7) + datetime.timedelta(days=7)

TOK = re.compile(r'^(\d\d)-(\d\d)([AB])(\d+)([A-Za-z]{2})$')
obs = collections.defaultdict(dict)
for line in open('data/goarch_pointer_sequences.txt'):
    p = line.split(); Y = int(p[0])
    trio_mon = pd_to_date(Y, GreekYear(Y).triodion_start + 1)
    for t in p[1:]:
        m = TOK.match(t)
        dt = datetime.date(Y + 1, int(m.group(1)), int(m.group(2)))
        b = (dt - trio_mon).days // 7
        if b <= -4 and m.group(3) == 'B':
            obs[Y].setdefault(b, set()).add(int(m.group(4)))

print('surplus weeks: observed Luke-section week vs. the forward pointer\n')
hit = miss = 0
for Y in sorted(obs):
    wk1mon = first_sun_luke(Y) + datetime.timedelta(days=1)
    trio_mon = pd_to_date(Y, GreekYear(Y).triodion_start + 1)
    for b, weeks in sorted(obs[Y].items()):
        # any date in that b-week works; reconstruct its Monday
        monday = trio_mon + datetime.timedelta(days=7 * b)
        forward = (monday - wk1mon).days // 7 + 1 + 1      # calendar_week + 1
        for w in weeks:
            ok = (w == forward)
            hit += ok; miss += not ok
            print(f'  cycle {Y}  b{b}  observed B{w:<3} forward-pointer predicts B{forward:<3} {"MATCH" if ok else ""}')
print(f'\nforward pointer matches {hit}, misses {miss}')
