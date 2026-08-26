"""Verify the GOA Theophany-interpolation rule against goarch.org.

Rule under test: build the candidate pool in this inclusion priority,
dropping any Lukan number the autumn already consumed --

        12L, 15L, 14L, 16M, 15M

take the first `regular_extra_sundays - 2`, and read out ascending (Lukan
numbers first, then Matthean). The final Sunday before Triodion is the
Canaanite Woman / Zacchaeus boundary and is governed separately by
`canaanite_woman_applies`.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])   # data/ paths below are repo-root relative
import django, os, datetime
os.environ.setdefault('DJANGO_SETTINGS_MODULE','orthocal.settings')
django.setup()
from calendarium.liturgics import GreekYear
from calendarium import datetools

PRIORITY = [('luke', 12), ('luke', 15), ('luke', 14), ('matthew', 16), ('matthew', 15)]

def pd_to_date(Y, pdist):
    j = datetime.date(Y, 1, 1)
    return j + datetime.timedelta(days=datetools.compute_pascha_jdn(Y) - datetools.gregorian_to_jdn(j) + pdist)

def predict(gy):
    used = {v for v in gy.lukan_sunday_numbers.values() if v}
    pool = [p for p in PRIORITY if p[0] == 'matthew' or p[1] not in used]
    chosen = pool[:max(gy.regular_extra_sundays - 2, 0)]
    return ' '.join(f'{n}{"M" if k == "matthew" else "L"}'
                    for k, n in sorted(chosen, key=lambda p: (p[0] == 'matthew', p[1])))

ok = bad = skipped = corrupt = 0
for line in open('data/goarch_sunday_sequences.txt'):
    p = line.split(); Y = int(p[0])
    gy = GreekYear(Y)
    trio = pd_to_date(Y, gy.triodion_start)
    rows = [(datetime.date(Y+1, int(t[:2]), int(t[3:5])), t.split('=')[1]) for t in p[1:]]

    pps = [d for d, c in rows if c == 'PP']
    if len(pps) != 1 or pps[0] != trio:
        corrupt += 1
        print(f'  {Y}  EXCLUDED - GOA Triodion disagrees with the Paschalion (app {trio}, GOA {[str(x) for x in pps]})')
        continue

    rows = rows[1:]                                   # drop Sunday-after-Theophany
    if rows and rows[0][1] == 'LV':                   # Leavetaking on Sunday: already netted out of n
        rows = rows[1:]
    inner = [c for d, c in rows if d < trio][:-1]     # drop the Canaanite/Zacchaeus boundary
    if 'X' in inner:
        skipped += 1
        continue
    pred, actual = predict(gy), ' '.join(inner)
    if pred == actual:
        ok += 1
    else:
        bad += 1
        print(f'  {Y}  n={gy.regular_extra_sundays} jump={gy.lukan_jump:<3} MISMATCH  predicted={pred!r}  actual={actual!r}')

print(f'\nmatches {ok}   fails {bad}   skipped {skipped} (a fixed feast claims a slot)   excluded {corrupt} (GOA data error)')
