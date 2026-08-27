import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])   # data/ paths below are repo-root relative
import django, os, re, datetime, collections
os.environ.setdefault('DJANGO_SETTINGS_MODULE','orthocal.settings')
django.setup()
from calendarium.liturgics import GreekYear

seqs = {}
for line in open('data/goarch_sunday_sequences.txt'):
    p = line.split()
    Y = int(p[0])
    seqs[Y] = [(datetime.date(Y+1, int(t[:2]), int(t[3:5])), t.split('=')[1]) for t in p[1:]]

buckets = collections.defaultdict(list)
for Y, rows in sorted(seqs.items()):
    gy = GreekYear(Y)
    # the interpolation window: strictly after Sunday-after-Theophany, strictly before Triodion
    inner = [(d, c) for d, c in rows if c not in ('PP',)]
    inner = inner[1:]          # drop the leading Sunday-after-Theophany
    buckets[gy.regular_extra_sundays].append((Y, gy.lukan_jump, gy.triodion_start, inner))

table = GreekYear._THEOPHANY_INTERPOLATION
for n in sorted(buckets):
    cur = table.get(n)
    cur_s = ' '.join(f'{v}{"M" if k=="matthew" else "L"}' for k, v in cur) if cur else '(none)'
    print(f'\n=== regular_extra_sundays = {n} ===   app table: {cur_s}')
    for Y, jump, trio, inner in buckets[n]:
        s = ' '.join(f'{d.strftime("%m-%d")}:{c}' for d, c in inner)
        print(f'   cycle {Y}  jump={jump:<3} trio={trio}   {s}')
