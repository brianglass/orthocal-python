"""Populate models.OrdoReading from harvested ordo data, then regenerate the fixture.

Greek rows come from goarch.org (the GOA Kanonion, as published on their web
calendar); Antiochian rows from antiochian.org's feed. Both are transcriptions
of what the jurisdiction published, resolved onto pdists that already exist in
the Reading table.

    docker compose exec -T local python tools/greek/load_ordo.py
    docker compose exec -T local ./manage.py dumpdata calendarium --indent=2 -o fixtures/calendarium.json

The indent must be 2. The fixture is stored that way, and dumping it at any
other width reformats all ~62,000 lines, burying the handful that changed.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])

import django, re, json, glob, datetime, collections
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orthocal.settings')
django.setup()
from calendarium.models import OrdoReading, Reading

ORDO_DATES = (19, 24, 26)     # January; the only dates surveyed so far

def ref(s):
    s = (s or '').upper().replace('.', ':')
    m = re.match(r'\s*(ST\.\s*)?(MATTHEW|MATT|MARK|MK|LUKE|LK|JOHN|JN)\.?\s*(.*)$', s)
    if not m: return None
    b = {'MATTHEW':'MATT','MATT':'MATT','MARK':'MARK','MK':'MARK','LUKE':'LUKE','LK':'LUKE','JOHN':'JOHN','JN':'JOHN'}[m.group(2)]
    v = re.search(r'(\d+)[:.](\d+)', s)
    return (b, int(v.group(1)), int(v.group(2))) if v else None

index = collections.defaultdict(list)
for r in Reading.objects.filter(source='Gospel').select_related('pericope'):
    k = ref(r.pericope.sdisplay)
    if k:
        index[k].append(r)

def resolve(citation):
    """The single ordinary pdist carrying this citation, or None.

    The opening chapter:verse must match within one -- the traditions differ by
    a verse at a few pericope boundaries (this repo has `Matt 22.1-14` where
    both jurisdictions print `22:2-14`, for instance). The *closing* reference
    has to match within two as well. Without that second check a loose start
    match picks up entirely different pericopes: `Mark 5:24-34` (the woman with
    the issue of blood) and `Mark 5.22-24, 35-6.1` (Jairus' daughter) open two
    verses apart and are not the same reading.
    """
    want, want_end = ref(citation), last_ref(citation)
    if not want:
        return None
    pdists = sorted({
        r.pdist for k, rs in index.items()
        if k[0] == want[0] and k[1] == want[1] and abs(k[2] - want[2]) <= 1
        for r in rs
        if 0 <= r.pdist < 500
        and _end_matches(want_end, last_ref(r.pericope.sdisplay))
    })
    return pdists[0] if pdists else None


def last_ref(s):
    """The final chapter:verse (or bare verse) mentioned in a citation."""
    s = (s or '').upper().replace('.', ':')
    nums = re.findall(r'(\d+):(\d+)|(\d+)', s)
    tail = [n for n in nums if any(n)]
    if not tail:
        return None
    ch, v, bare = tail[-1]
    return int(v) if v else int(bare)


def _end_matches(a, b):
    return a is None or b is None or abs(a - b) <= 2

def goarch_rows():
    src = {}
    for line in open('data/goarch_winter_rows.txt'):
        d, label, gospel = line.rstrip('\n').split('|')
        src[d] = gospel
    for year in range(2011, 2028):
        for dd in ORDO_DATES:
            key = f'{year}-01-{dd:02d}'
            if key not in src or datetime.date(year, 1, dd).weekday() == 6:
                continue
            pdist = resolve(src[key])
            if pdist is None:
                print(f'  skip greek {key}: {src[key]!r} does not resolve to an ordinary pdist')
                continue
            yield ('greek', year, 1, dd, 'Gospel', pdist, f'goarch.org: {src[key]}')

def antiochian_rows():
    for path in sorted(glob.glob('data/antiochian_raw/*.json')):
        d = json.load(open(path))
        dt = datetime.date.fromisoformat(d['originalCalendarDate'])
        if dt.month != 1 or dt.day not in ORDO_DATES or dt.weekday() == 6:
            continue
        citation = d.get('reading2Title', '')
        pdist = resolve(citation)
        if pdist is None:
            print(f'  skip antiochian {dt}: {citation!r} does not resolve to an ordinary pdist')
            continue
        yield ('antiochian', dt.year, 1, dt.day, 'Gospel', pdist, f'antiochian.org: {citation}')

made = collections.Counter()
seen = set()
for jur, y, m, dd, source, pdist, note in list(goarch_rows()) + list(antiochian_rows()):
    OrdoReading.objects.update_or_create(
        jurisdiction=jur, year=y, month=m, day=dd, source=source,
        defaults={'pdist': pdist, 'note': note},
    )
    made[jur] += 1
    seen.add((jur, y, m, dd, source))

# Prune what the sources no longer produce, rather than emptying the table up
# front and rebuilding it. Rebuilding renumbered every pk on every run, so
# harvesting one new date rewrote all ~120 rows in the fixture diff and hid the
# one line that actually changed. update_or_create keeps a surviving row's pk.
stale = [
    o.pk for o in OrdoReading.objects.all()
    if (o.jurisdiction, o.year, o.month, o.day, o.source) not in seen
]
if stale:
    OrdoReading.objects.filter(pk__in=stale).delete()
    print(f'pruned {len(stale)} row(s) the sources no longer produce')

for jur, n in sorted(made.items()):
    yrs = OrdoReading.objects.filter(jurisdiction=jur).order_by('year')
    print(f'{jur:<12} {n:>3} rows, {yrs.first().year}-{yrs.last().year}')
print(f'total {OrdoReading.objects.count()}')
