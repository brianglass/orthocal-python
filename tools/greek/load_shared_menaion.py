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
    (7, 5, 'Epistle', 'Gal 5.22-6.2',              'Athanasius of Mount Athos',
     'Gal 5:22-26; 6:1-2 in 8 of 8 harvested years, including both years the '
     'date falls on a Sunday. Slavic already carries this Epistle, tagged '
     'slavic, so Greek was falling through to the cycle'),
    (7, 5, 'Gospel',  'Matt 11.27-30',              'Athanasius of Mount Athos',
     'Matthew 11:27-30 in 6 of 8 harvested years; the two exceptions are '
     'Sundays. Slavic carries this as its Matins Gospel and reads Luke 6:17-23 '
     'at Liturgy, so the two traditions genuinely differ here'),
    (9, 24, 'Gospel', 'Luke 10.38-42, 11.27-28',    'Miracle of the Theotokos Myrtidiotissa',
     'A Greek commemoration Slavic does not keep, hence the Theotokos Gospel '
     'where the common row has Luke 21:12-19 for St Thekla. Note the source '
     'changed: antiochian.org showed Luke 5:12-16 in 2019-2021 and '
     'Luke 10:38-42, 11:27-28 in every year from 2022 through 2026, which '
     'goarch.org corroborates for 2026. Taking the later, stable value'),
    (5, 7, 'Epistle', 'Acts 26.1, 12-20',           'Appearance of the Cross over Jerusalem',
     'Acts 26:1, 12-20 on all 3 harvested years where May 7 falls on a weekday '
     '(2019 Tue, 2025 Wed, 2026 Thu); the other two are outranked by Bright '
     'Week and a Sunday. The same Epistle Ss Constantine and Helen carry on '
     'May 21, which this project already has as a common row -- the Cross '
     'appeared to Constantine, and Acts 26 is Paul recounting the light from '
     'heaven. The Gospel stays with the Paschal cycle: antiochian.org shows a '
     'different one each year, matching what the app already computes'),
    # Weekday commemorations that 2026 hid: each of these dates is a Sunday in
    # 2026, so the Sunday readings masked them in the single-year audit.
    (2, 15, 'Epistle', 'Philemon 1-25',             'St Onesimus',
     'antiochian.org 2018, 2020, 2023, 2025; goarch.org 2024, 2025. Explains '
     'the two "Philemon" years in the Prodigal Son Saturday sample in '
     'docs/greek-commons.md: those were Feb 15 falling on that Saturday'),
    (11, 22, 'Epistle', 'Philemon 1-25',            'St Philemon',
     'antiochian.org 2018, 2021, 2022, 2023, 2024; goarch.org 2024, 2025'),
    (12, 20, 'Epistle', 'Heb 10.32-38',             'St Ignatius',
     'antiochian.org 2018, 2021-2024; goarch.org 2024. 2025 is the Saturday '
     'before Nativity, which wins'),
    (12, 20, 'Gospel',  'Mark 9.33-41',             'St Ignatius',
     'antiochian.org 2018, 2021-2024; goarch.org 2024'),
    (8, 2, 'Epistle',  'Acts 6.8-7.5, 47-60',       'St Stephen',
     'Translation of the relics; goarch.org 2024, 2025; antiochian.org 2025'),
    (8, 2, 'Gospel',   'Mark 12.1-12',              'St Stephen',
     'goarch.org 2024, 2025; antiochian.org 2025'),
    (8, 9, 'Epistle',  'Acts 1.12-17, 21-26',       'St Matthias',
     'goarch.org 2024, 2025; antiochian.org 2025. The Gospel stays with the '
     'cycle in both sources'),
    (8, 16, 'Epistle', '1 Tim 3.13-4.5',            'Image',
     'goarch.org 2024, 2025; antiochian.org 2025. Same slot as the common '
     'Col 1:12-18, which Slavic keeps; the Gospel already has a greek row'),
    (9, 6, 'Epistle',  'Heb 2.2-10',                'Archangel Michael',
     'Miracle at Colossae; goarch.org 2024, 2025; antiochian.org 2025'),
    (9, 6, 'Gospel',   'Luke 10.16-21',             'Archangel Michael',
     'goarch.org 2024, 2025; antiochian.org 2025'),
    (9, 12, 'Gospel',  'John 11.47-54',             'St Autonomos',
     'goarch.org 2024, 2025; antiochian.org 2025, alongside the Leavetaking '
     'Gospel the common row carries. The Epistle differs by year'),
    (9, 20, 'Epistle', 'Eph 6.10-17',               'St Eustathius',
     'goarch.org 2024, 2025; antiochian.org 2025. 2025 is the Saturday after '
     'the Elevation, which takes the Gospel'),
    (10, 11, 'Epistle', 'Acts 8.26-39',             'St Philip the Deacon',
     'goarch.org 2024, 2025; antiochian.org 2025'),
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
