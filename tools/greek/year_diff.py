import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])   # data/ paths below are repo-root relative
import re, collections

S = 'data'
goa, ant = {}, {}
for tok in open(f'{S}/goa2026.txt').read().split():
    d, e, g = (tok.split(',') + ['', ''])[:3]
    goa[d] = (e, g)
for tok in open(f'{S}/ant2026.txt').read().split(';'):
    d, e, g = (tok.split(',') + ['', ''])[:3]
    ant[d] = (e, g)

REF = re.compile(r'^(\d?[A-Z]+)(\d+):(\d+)$')
def near(a, b):
    if a == b: return True
    if not a or not b: return None            # one side blank -> not comparable
    pa, pb = REF.match(a), REF.match(b)
    if not pa or not pb: return None
    return pa.group(1) == pb.group(1) and pa.group(2) == pb.group(2) and abs(int(pa.group(3)) - int(pb.group(3))) <= 2

both = sorted(set(goa) & set(ant))
ep_diff, gs_diff, either, blank = [], [], [], 0
for d in both:
    ge, gg = goa[d]; ae, ag = ant[d]
    e_ok, g_ok = near(ge, ae), near(gg, ag)
    if e_ok is None and g_ok is None:
        blank += 1; continue
    if e_ok is False: ep_diff.append(d)
    if g_ok is False: gs_diff.append(d)
    if e_ok is False or g_ok is False: either.append(d)

print(f'Calendar year 2026 -- GOA vs Antiochian, {len(both)} days compared')
print(f'  ({blank} days excluded: one or both sources list no Epistle/Gospel, e.g. aliturgical Lenten weekdays)\n')
print(f'  Epistle differs : {len(ep_diff)} days')
print(f'  Gospel differs  : {len(gs_diff)} days')
print(f'  Either differs  : {len(either)} days   ({len(either)/(len(both)-blank)*100:.1f}% of comparable days)\n')
for d in either:
    ge, gg = goa[d]; ae, ag = ant[d]
    marks = ('G' if d in gs_diff else ' ') + ('E' if d in ep_diff else ' ')
    print(f'  2026-{d[:2]}-{d[2:]} {marks}  GOA {ge:<12} {gg:<12} | ANT {ae:<12} {ag}')

# --- classify the survivors -------------------------------------------------
# Two classes of non-difference remain, both source-formatting rather than
# liturgical:
#   * antiochian.org calls Jude "St. Jude's FIRST Universal Letter" though
#     there is only one; the citation itself is identical.
#   * on Holy Week days antiochian.org carries the Matins Gospel in reading1
#     (where the Epistle normally sits) and the Liturgy Gospel in reading2,
#     while goarch.org's grid lists a single Gospel. Same services, different
#     field layout.
ARTIFACT = set()
for d in either:
    ge, gg = goa[d]; ae, ag = ant[d]
    if ge.replace('1JUDE', 'JUDE') == ae.replace('1JUDE', 'JUDE') and near(gg, ag) is not False:
        ARTIFACT.add(d)
    elif not ge and ae and re.match(r'^(MATT|MARK|LUKE|JOHN)', ae) and near(gg, ae):
        ARTIFACT.add(d)

real = [d for d in either if d not in ARTIFACT]
print(f'\n--- after removing source-formatting artifacts ---')
print(f'  formatting artifacts : {len(ARTIFACT)} days ({", ".join(sorted(ARTIFACT))})')
print(f'  GENUINE differences  : {len(real)} days\n')
for d in real:
    ge, gg = goa[d]; ae, ag = ant[d]
    print(f'  2026-{d[:2]}-{d[2:]}  GOA {ge:<11} {gg:<12} | ANT {ae:<11} {ag}')
