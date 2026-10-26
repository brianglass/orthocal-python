"""Mark the Greek propers that are read in place of a Sunday's own readings.

The Typikon of the Great Church (Violakis; the Arman translation at
`~/Documents/Orthodox Studies/54-typikon-full.pdf`) states the rule in its
chapter "VII. The Epistle and Gospel Readings": when the feast of a great saint
falls on a Sunday, the Epistle is the saint's and the Gospel the Sunday's; the
Forerunner's feasts, Peter and Paul, the Twelve Apostles, the Evangelists and a
few others take both of theirs. Which saints are great it does not say there,
but its Menaion gives every one of them an "If the feast falls on a Sunday"
order naming the Liturgy readings, and those orders are transcribed below.
A saint with no such order keeps the Sunday's readings, and has no row here.

`greek` means the GOA, so where goarch.org departs from the typikon, goarch.org
wins, and the entry says so. Checked against goarch.org 2018-2027
(data/goarch_readings_2018_2027.json) and antiochian.org
(data/antiochian_raw/) with tools/greek/sunday_pair_audit.py.

Each entry is (month, day, desc, sources, note): the Reading rows of that date
and description get displaces_sunday=True for the sources named, 'E' for the
Epistle and 'G' for the Gospel. Where a greek row overrides a common one for
the same slot, only the greek row is marked, since it is the one read.

    python3 tools/greek/load_sunday_precedence.py

It edits fixtures/calendarium.json in place, adding the field to the marked
rows only, rather than going through the database and dumpdata, which
reorders the whole file.
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.chdir(sys.path[0])

FIXTURE = 'fixtures/calendarium.json'
FIELD = '    "displaces_sunday": true'

SOURCES = {'E': 'Epistle', 'G': 'Gospel'}

PRECEDENCE = (
    (9, 1, 'New Year', 'EG', 'the Indiction'),
    (9, 14, 'Elevation', 'EG', ''),
    (9, 23, 'Forerunner', 'E', ''),
    (9, 24, 'Myrtidiotissa Miracle', 'E', "the typikon's is St Thekla's, 2 Tim 3:10-15, which this row carries"),
    (9, 26, 'St John', 'EG', ''),
    (10, 18, 'St Luke', 'EG', 'an Evangelist'),
    (10, 23, 'St James', 'E', 'the typikon keeps the Sunday; goarch.org 2022 reads the Epistle'),
    (10, 26, 'St Demetrius', 'E', 'the typikon gives both; goarch.org and antiochian.org 2025 the Epistle only'),
    (10, 28, 'Protection of the Theotokos', 'E', 'not in the typikon; goarch.org 2018'),
    (11, 1, 'Cosmas & Damian', 'E', ''),
    (11, 8, 'Angels', 'E', ''),
    (11, 11, 'Menas, Victor & Vincent', 'E', ''),
    (11, 12, 'John the Merciful', 'E', ''),
    (11, 13, 'St John Chrysostom', 'E', 'the typikon gives both; goarch.org and antiochian.org 2022 the Epistle only'),
    (11, 14, 'St Philip', 'E', ''),
    (11, 16, 'Matthew the Apostle', 'EG', 'an Evangelist'),
    (11, 21, 'Entrance', 'EG', ''),
    (11, 25, 'Catherine', 'E', ''),
    (11, 30, 'St Andrew', 'EG', ''),
    (12, 4, 'Barbara', 'E', ''),
    (12, 5, 'St Sabbas', 'E', ''),
    (12, 6, 'St Nicholas', 'E', ''),
    (12, 9, 'St Anna', 'E', ''),
    (12, 12, 'Spyridon', 'E', 'with the Gospel of the Forefathers'),
    (12, 15, 'Eleutherios', 'E', 'with the Gospel of the Forefathers'),
    (12, 25, 'Nativity', 'EG', ''),
    (12, 27, 'St Stephen', 'E', 'with the Gospel of the Sunday after the Nativity'),
    (1, 1, 'Circumcision', 'EG', "the typikon reads St Basil's Epistle; goarch.org and antiochian.org 2023 the Circumcision's"),
    (1, 6, 'Theophany', 'EG', ''),
    (1, 7, 'Forerunner', 'EG', 'over the Sunday after Theophany'),
    (1, 11, 'Afterfeast of Theophany', 'E', "St Theodosius's Epistle, Heb 13:7-16, which goarch.org reads on Jan 11 every year; goarch.org and antiochian.org 2026"),
    (1, 17, 'St Anthony', 'E', ''),
    (1, 18, 'Athanasius & Cyril', 'E', ''),
    (1, 20, 'St. Euthymius', 'E', ''),
    (1, 25, 'St. Gregory', 'E', ''),
    (1, 27, 'St John', 'E', ''),
    (1, 30, 'Hierarchs', 'EG', 'the Gospel only before the Triodion; see GreekDay'),
    (2, 1, 'St. Trypho', 'E', 'goarch.org 2026; antiochian.org keeps the Sunday'),
    (2, 2, 'Meeting', 'EG', 'the Gospel only before the Triodion; see GreekDay'),
    (2, 6, 'St. Photius', 'E', 'not in the typikon; goarch.org 2022'),
    (2, 10, 'St. Haralambos', 'E', ''),
    (2, 24, 'Forerunner', 'E', ''),
    (3, 9, 'Martyrs', 'E', 'the typikon keeps a Sunday of Lent; goarch.org and antiochian.org 2025 read the Epistle'),
    (4, 23, 'St George', 'E', ''),
    (4, 25, 'St Mark', 'E', "the Pentecostarion's Sundays keep their Gospel"),
    (5, 2, 'Removal of Relics of Athanasius', 'E', ''),
    (5, 8, 'St John', 'E', "the Pentecostarion's Sundays keep their Gospel"),
    (5, 21, 'Saints', 'E', ''),
    (5, 25, 'Forerunner', 'E', ''),
    (6, 24, 'Forerunner', 'EG', ''),
    (6, 29, 'Apostles', 'EG', ''),
    (6, 30, 'Synaxis of the Twelve Apostles', 'EG', ''),
    (7, 1, 'Cosmas & Damian', 'E', ''),
    (7, 2, 'Deposition of the Robe', 'E', ''),
    (7, 5, 'Athanasius of Mount Athos', 'E', ''),
    (7, 7, 'Kyriake', 'E', ''),
    (7, 11, 'Euphemia (July)', 'E', ''),
    (7, 20, 'Prophet Elijah', 'E', ''),
    (7, 25, 'St Anna', 'E', ''),
    (7, 26, 'Paraskeve', 'E', ''),
    (7, 27, 'St Panteleimon', 'E', ''),
    (8, 6, 'Transfiguration', 'EG', ''),
    (8, 15, 'Dormition', 'EG', ''),
    (8, 29, 'Forerunner', 'EG', ''),
    (8, 31, 'Placing of the Sash of the Theotokos', 'E', ''),
)

# Deliberately absent, though the typikon has a Sunday order for them:
#   Aug 2, the relics of St Stephen -- the typikon reads his Epistle, but
#     goarch.org keeps the Sunday's readings (2020, 2026).
#   Sep 9, 16 and 20, and the Nativity of the Theotokos -- the Sundays before
#     and after the Elevation take precedence, and those are floats already.
#   All Saints Sunday on the Twelve Apostles -- goarch.org 2024 read All
#     Saints' Epistle with the Apostles' Gospel. One observation, and the
#     typikon gives no order for it, so the Apostles keep both here.
#   The Annunciation -- its order depends on which Sunday of Lent it falls on,
#     and its readings are not fixed-date rows in this table.


def main():
    text = open(FIXTURE).read()
    text = text.replace(',\n' + FIELD + '\n', '\n')   # start clean

    readings = [r for r in json.loads(text) if r['model'] == 'calendarium.reading']
    marked = []

    for month, day, desc, sources, note in PRECEDENCE:
        for code in sources:
            rows = [r for r in readings
                    if r['fields']['month'] == month and r['fields']['day'] == day
                    and r['fields']['desc'] == desc and r['fields']['source'] == SOURCES[code]
                    and r['fields']['tradition'] in ('common', 'greek')]
            if any(r['fields']['tradition'] == 'greek' for r in rows):
                rows = [r for r in rows if r['fields']['tradition'] == 'greek']
            if len(rows) != 1:
                raise SystemExit(f'{month}/{day} {desc!r} {SOURCES[code]}: matched {len(rows)} rows')
            marked.append(rows[0]['pk'])

    for pk in marked:
        # The row's last field is its tradition; the new one goes after it.
        pattern = re.compile(r'("model": "calendarium\.reading",\n  "pk": %d,\n  "fields": \{\n(?:    .*\n)*?    "tradition": "\w+")\n' % pk)
        text, n = pattern.subn(lambda m: m.group(1) + ',\n' + FIELD + '\n', text)
        assert n == 1, pk

    json.loads(text)
    open(FIXTURE, 'w').write(text)
    print(len(marked), 'rows marked')


main()
