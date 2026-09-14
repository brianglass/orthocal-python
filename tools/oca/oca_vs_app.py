"""Which oca.org commemorations does the app not show a Slavic reader?

    docker compose run --rm local python tools/oca/oca_vs_app.py [--year 2026]

The reverse of greek_vs_oca.py. That tool asked which of *our* greek-only rows
oca.org also keeps; this asks which of *oca.org's* commemorations we lack.

Each oca.org entry is compared against what the app actually shows on the
Slavic, New Calendar page for the same date -- `day.saints`, `day.feasts` and
`day.titles` -- so moveable commemorations, new-style dates and tradition
preference resolve exactly as a reader sees them, not as raw fixture rows do.
Anything unmatched is then looked for on the Greek page for that date, and
among commemorations on every other date. Each entry lands in one bucket:

    present    a strong match on the Slavic page
    probable   a partial name match on the Slavic page -- read it
    greek      we have it, but only on the Greek page (a retag candidate)
    elsewhere  we have it, but on a different date
    missing    no counterpart anywhere

Screening only. Name overlap is noisy on this project -- common forenames,
place names, and saints kept on genuinely different dates by the two
traditions -- so every bucket except `present` is a list to read, not a list
to act on. Writes the full list to data/oca_raw/oca_vs_app-YEAR.tsv.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])

import collections
import csv
import datetime
import json
import re

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orthocal.settings')
django.setup()

from calendarium.datetools import Tradition               # noqa: E402
from calendarium.liturgics import Day                      # noqa: E402
from commemorations.models import DayCommemoration         # noqa: E402
from tools.oca.greek_vs_oca import tokens                  # noqa: E402

BUCKETS = ('present', 'probable', 'greek', 'elsewhere', 'missing')

# Applied in order, to turn one name's transliterations into the same skeleton:
# Nikephoros/Nicephorus, Pansophios/Pansophius, Kalliniki/Callinica,
# Erasmus/Erazmo, Paraskevi/Parasceva, Vasily/Basil, Mikhail/Michael.
_FOLDS = (('ph', 'f'), ('kh', 'c'), ('ch', 'c'), ('k', 'c'), ('z', 's'),
          ('y', 'i'), ('v', 'b'), ('ou', 'u'), ('ae', 'e'), ('ai', 'e'), ('ei', 'i'))
_ENDING = re.compile(r'(?:ios|ius|os|us|as|es|is|[aeiou])$')
_PLACE = re.compile(r"\b(?:of|in|at|from|near)\s+(?:the\s+)?([A-Za-z’'-]+)", re.IGNORECASE)


def fold(word):
    for a, b in _FOLDS:
        word = word.replace(a, b)
    word = re.sub(r'(.)\1+', r'\1', word)
    return _ENDING.sub('', word) or word


def ident(title):
    """The title's identity words, folded to spelling skeletons."""
    return {fold(w) for w in tokens(title)}


def places(title):
    """Folded words that follow of/in/at/from/near -- a place, not a person.

    A lone shared place word says nothing about identity: "Saint Macarius,
    Patriarch of Serbia" and "The Holy New Martyrs of Serbia" share only
    "Serbia", and are not the same commemoration.
    """
    return {fold(m.lower()) for m in _PLACE.findall(title or '')}


def overlap(a, b):
    """Shared identity words over the shorter side's count, and the count.

    Over the shorter side because oca.org titles run long ("Saint Prochorus,
    Abbot in the Vranski Desert on the River Pshina in Bulgaria") and ours
    short ("Prochorus of Pshinja"); dividing by the longer would bury real
    matches. A single shared word can still be a coincidence, which is why
    `strong` below also wants two words unless one side has only one.
    """
    if not a or not b:
        return 0.0, 0
    shared = len(a & b)
    return shared / min(len(a), len(b)), shared


def named(a, b, title_a, title_b):
    """The shared words that are names rather than places."""
    return (a & b) - places(title_a) - places(title_b)


def strong(a, b, title_a, title_b):
    score, shared = overlap(a, b)
    if score < 0.75:
        return False
    if shared >= 2:
        return True
    # A single shared word only counts when it is a name, and one side has
    # nothing else to go on ("Elizabeth the Wonderworker").
    return min(len(a), len(b)) == 1 and bool(named(a, b, title_a, title_b))


def best(theirs, their_title, candidates):
    """(score, shared, title) of the best candidate, ranked by named overlap."""
    top = (0.0, 0, '')
    for title in candidates:
        ours = ident(title)
        if not named(theirs, ours, their_title, title):
            continue
        score, shared = overlap(theirs, ours)
        if (score, shared) > top[:2]:
            top = (score, shared, title)
    return top


def page_titles(date, tradition):
    day = Day(date.year, date.month, date.day, tradition=tradition)
    day.initialize()
    return list(dict.fromkeys([*day.saints, *day.feasts, *day.titles]))


def other_dates_index():
    """Every Slavic-visible fixed-date commemoration, with its saints' names."""
    index = []
    rows = (DayCommemoration.objects
            .filter(tradition__in=('common', 'slavic'), day__pdist=999)
            .select_related('day').prefetch_related('saints'))
    for dc in rows:
        names = [dc.title] + [n for s in dc.saints.all() for n in (s.name, s.full_name) if n]
        index.append((f'{dc.day.month:02d}-{dc.day.day:02d}', dc.title,
                      set().union(*(ident(n) for n in names))))
    return index


def main(year):
    with open(f'data/oca_raw/saints-{year}.json') as f:
        oca = json.load(f)
    index = other_dates_index()

    results = []
    for iso in sorted(oca):
        date = datetime.date.fromisoformat(iso)
        slavic = page_titles(date, Tradition.Slavic)
        greek = None
        for entry in oca[iso]:
            theirs = ident(entry['title'])
            score, shared, ours = best(theirs, entry['title'], slavic)
            if ours and strong(theirs, ident(ours), entry['title'], ours):
                bucket = 'present'
            elif ours:
                bucket = 'probable'
            else:
                if greek is None:
                    greek = [t for t in page_titles(date, Tradition.Greek) if t not in slavic]
                score, shared, ours = best(theirs, entry['title'], greek)
                if ours and strong(theirs, ident(ours), entry['title'], ours):
                    bucket = 'greek'
                else:
                    top = (0.0, 0, '', '')
                    for md, title, toks in index:
                        if md == iso[5:] or not named(theirs, toks, entry['title'], title):
                            continue
                        s_, n = overlap(theirs, toks)
                        if n >= 2 and (s_, n) > top[:2]:
                            top = (s_, n, title, md)
                    if top[1] >= 2 and top[0] >= 0.75:
                        bucket, score, shared, ours = 'elsewhere', top[0], top[1], f'{top[3]}  {top[2]}'
                    else:
                        bucket, score, shared, ours = 'missing', 0.0, 0, ''
            results.append((bucket, iso[5:], entry['title'], ours, round(score, 2)))

    path = f'data/oca_raw/oca_vs_app-{year}.tsv'
    with open(path, 'w', newline='') as f:
        writer = csv.writer(f, delimiter='\t')
        writer.writerow(('bucket', 'date', 'oca_title', 'best_ours', 'score'))
        writer.writerows(results)

    counts = collections.Counter(r[0] for r in results)
    print(f'\n  {len(results)} oca.org commemorations for {year}, against the Slavic page:\n')
    for b in BUCKETS:
        print(f'    {b:<10} {counts[b]:>5}')
    icons = sum(1 for r in results if r[0] == 'missing' and 'icon' in r[2].lower())
    print(f'\n    of the missing, {icons} are icons of the Mother of God or similar')
    print(f'\n  full list -> {path}')


if __name__ == '__main__':
    y = 2026
    if '--year' in sys.argv:
        y = int(sys.argv[sys.argv.index('--year') + 1])
    main(y)
