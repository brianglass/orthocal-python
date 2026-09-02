"""Which `greek`-tagged commemorations does oca.org also keep, on the same date?

    python tools/oca/greek_vs_oca.py [--min 0.5]

A commemoration tagged `greek` asserts that the Slavic tradition does not keep
it. oca.org is the source the Slavic data was compiled from, so a `greek` row
whose saint appears on oca.org for the same date is a candidate for `common`.

Screening only. It ranks candidates by name overlap for a human to read -- the
standing lesson on this project is that raw name matches are mostly noise
(common forenames, place names, and saints the two traditions keep on genuinely
different dates, e.g. Catherine of Alexandria on Nov 24 Slavic and Nov 25
Greek, which is a real distinction and must not be collapsed).

A match here is a question, not an answer.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])

import json
import re
import unicodedata

# Words that carry no identity: ranks, honorifics, and grammar.
NOISE = {
    'saint', 'saints', 'st', 'sts', 'holy', 'the', 'of', 'and', 'his', 'her',
    'our', 'father', 'fathers', 'mother', 'venerable', 'righteous', 'blessed',
    'martyr', 'martyrs', 'hieromartyr', 'hieromartyrs', 'greatmartyr',
    'great', 'new', 'monk', 'nun', 'bishop', 'archbishop', 'patriarch',
    'apostle', 'apostles', 'prophet', 'confessor', 'wonderworker', 'abbot',
    'equal', 'apostles', 'among', 'who', 'with', 'in', 'at', 'a', 'ca',
    'commemoration', 'synaxis', 'translation', 'relics', 'repose', 'finding',
    'uncovering', 'deaconess', 'servants', 'those', 'she', 'he',
}


def tokens(name):
    name = unicodedata.normalize('NFKD', name or '')
    name = ''.join(c for c in name if not unicodedata.combining(c))
    words = re.findall(r"[a-z]+", name.lower())
    return {w for w in words if w not in NOISE and len(w) > 2}


def main(threshold):
    oca = json.load(open('data/oca_raw/saints-2026.json'))
    comm = json.load(open('fixtures/commemorations.json'))
    cal = json.load(open('fixtures/calendarium.json'))
    day = {r['pk']: r['fields'] for r in cal if r['model'] == 'calendarium.day'}

    by_date = {}
    for iso, saints in oca.items():
        by_date[iso[5:]] = [(s['title'], tokens(s['title'])) for s in saints]

    hits = []
    for row in comm:
        if row['model'] != 'commemorations.daycommemoration':
            continue
        f = row['fields']
        if f['tradition'] != 'greek':
            continue
        d = day.get(f['day'], {})
        if not d.get('month'):
            continue                    # movable; oca harvest is keyed by date
        md = f"{d['month']:02d}-{d['day']:02d}"
        ours = tokens(f['title'])
        if not ours:
            continue
        best = (0.0, '')
        for title, theirs in by_date.get(md, []):
            if not theirs:
                continue
            score = len(ours & theirs) / len(ours)
            if score > best[0]:
                best = (score, title)
        if best[0] >= threshold:
            hits.append((best[0], md, f['title'], best[1]))

    hits.sort(reverse=True)
    print(f'{len(hits)} greek-tagged commemorations with a same-date oca.org match '
          f'at >= {threshold:.0%} token overlap\n')
    for score, md, ours, theirs in hits:
        print(f'  {score:>4.0%}  {md}  {ours[:52]:<52} | {theirs[:52]}')


if __name__ == '__main__':
    t = 0.5
    if '--min' in sys.argv:
        t = float(sys.argv[sys.argv.index('--min') + 1])
    main(t)
