"""Lay out one Composite's oca.org text beside every candidate verse, to read.

    docker compose run --rm local python tools/oca/show_composite.py 8

Deliberately does no matching. Neither Ephrem nor oca.org records which verses
a composite covers, so the selection has to be read out of the text -- and a
similarity threshold here would be a number nobody can check. Composite 18's
error (an extra 7:51, a missing 8:3) was found by reading, not scoring.

Prints oca.org's parts in order, then every verse of the chapters the loose
reference names, so the two can be compared by eye.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])

import html
import json
import re

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orthocal.settings')
django.setup()

from bible.models import Verse                       # noqa: E402
from calendarium.models import Pericope              # noqa: E402


def clean(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', s or ''))).strip()


def chapters(sdisplay):
    out, book = [], ''
    for passage in re.split(r'\s*;\s*', sdisplay):
        m = re.match(r'(?:([\w\s\[\]]+?)\s+)?(\d.*)', passage.strip())
        if not m:
            continue
        if m.group(1):
            book = m.group(1).strip()
        for chunk in re.split(r',\s*', m.group(2)):
            ch = re.match(r'(\d+)', chunk.strip())
            if ch and (book, int(ch.group(1))) not in out:
                out.append((book, int(ch.group(1))))
    return out


def main(num, translation='lxx2012-web', width=0):
    oca = json.load(open('data/oca_raw/composites.json'))[str(num)]
    p = Pericope.objects.filter(display__contains=f'Composite {num} -').first()

    print(f'=== Composite {num} — {oca["title"]} ===')
    print(f'    our sdisplay: {p.sdisplay if p else "?"}\n')
    print('--- oca.org text ---')
    for i, part in enumerate(oca['parts'], 1):
        print(f'[{i}] {clean(part)}\n')

    print(f'--- candidate verses ({translation}) ---')
    for book, chapter in chapters(p.sdisplay if p else ''):
        for v in Verse.objects.lookup_reference(f'{book} {chapter}', translation=translation):
            text = v.content if not width else v.content[:width]
            print(f'  {v.chapter}:{v.verse:<3} {text}')
        print()


if __name__ == '__main__':
    main(int(sys.argv[1]),
         *(sys.argv[2:3] or ['lxx2012-web']),
         width=int(sys.argv[3]) if len(sys.argv) > 3 else 0)
