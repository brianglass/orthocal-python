"""Add the Greek-tradition Menaion readings the app was missing.

These are the "shared bugs" from three_way.py: dates where goarch.org *and*
antiochian.org agree and the app differs from both, so they are Greek-tradition
gaps rather than jurisdictional ones. Each is confirmed across multiple
independent years of antiochian.org harvest and corroborated by goarch.org for
2026; see docs/greek-lectionary.md.

Rows are `greek`-tagged and additive. Where a `common` row already occupies the
slot it is left alone -- _prefer_tradition picks the greek row for the Greek
tradition and the common one for Slavic, so Slavic is unaffected.

    docker compose exec -T local python tools/greek/load_shared_menaion.py
    docker compose exec -T local ./manage.py dumpdata calendarium --indent=2 -o fixtures/calendarium.json
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orthocal.settings')
django.setup()
from calendarium.models import Pericope, Reading

# (month, day, source, pericope sdisplay, desc, evidence)
ROWS = [
    (4, 25, 'Gospel',  'Luke 10.16-21',            'St Mark',
     'Mark the Apostle; Luke 10:16-21 in 5 of 5 harvested years carrying that '
     'commemoration (the other 3 are overridden by Holy Week or Pascha)'),
    (4, 30, 'Gospel',  'Luke 9.1-6',               'St James',
     'James the Apostle; Acts 12:1-11 / Luke 9:1-6 in both harvested years '
     'carrying that commemoration. The Epistle is already correct'),
    (7, 13, 'Epistle', 'Heb 2.2-10',               'Synaxis of Archangel Gabriel',
     'Heb 2:2-10 in 4 of 5 harvested years; the exception is a Sunday, where '
     'the Sunday Epistle wins. The Gospel already has a greek row'),
    (8, 31, 'Epistle', 'Heb 9.1-7',                'Placing of the Sash of the Theotokos',
     'Heb 9:1-7 in 5 of 5 harvested years, including the year the date falls '
     'on a Sunday'),
    (8, 31, 'Gospel',  'Luke 10.38-42, 11.27-28',  'Placing of the Sash of the Theotokos',
     'Luke 10:38-42, 11:27-28 in 4 of 5 harvested years; the exception is a '
     'Sunday'),
    (12, 17, 'Epistle', 'Heb 11.33-12.2',          'Daniel and the Three Youths',
     'Heb 11:33-40; 12:1-2 in 7 of 8 harvested years; the exception is a '
     'Sunday. The Gospel already matches'),
]
ORDERING = {'Epistle': 821, 'Gospel': 921}

for month, day, source, sdisplay, desc, evidence in ROWS:
    pericope = Pericope.objects.get(sdisplay=sdisplay)
    row, created = Reading.objects.update_or_create(
        month=month, day=day, source=source, tradition='greek',
        ordering=ORDERING[source],
        defaults={'pdist': 999, 'desc': desc, 'pericope': pericope, 'flag': 0},
    )
    existing = Reading.objects.filter(
            month=month, day=day, source=source, tradition='common').first()
    note = f'(overrides common {existing.pericope.sdisplay})' if existing else '(no prior row)'
    print(f'{"+" if created else "~"} {month:02d}-{day:02d} {source:<8} greek {sdisplay:<26} {note}')
    print(f'    {evidence}')

print(f'\ngreek-tagged month/day readings now: '
      f'{Reading.objects.filter(tradition="greek", pdist=999).count()}')
