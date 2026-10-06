import itertools
from datetime import date
from pathlib import Path

from django.test import TestCase

from bible.models import Verse
from ingest_antiochian import parse_reading_citation
from .. import liturgics
from ..datetools import Tradition

GOLDEN = Path(__file__).resolve().parent / 'data/antiochian-readings.tsv'


async def characterize(entries):
    """Classify each antiochian.org (date, title) against the Greek readings.

    One line per entry: date, title, status, and for a boundary mismatch the
    overlapping orthocal readings. Status is:

      exact      a Greek reading that day covers the identical verses
      boundary   a Greek reading overlaps but covers different verses
      different  no Greek reading overlaps (a genuinely different reading)
      unresolved the title does not parse or resolve to any verses

    Verse sets are compared rather than reference strings, so notation such
    as "5:22-26; 6:1-2" versus "5.22-6.2" cannot register as a difference.
    tools/greek/antiochian_characterize.py regenerates the golden file.
    """

    verses = {}

    async def verse_set(reference):
        if reference not in verses:
            verses[reference] = frozenset({
                (v.book, v.chapter, v.verse)
                async for v in Verse.objects.lookup_reference(reference)
            })
        return verses[reference]

    lines = []
    for day_iso, group in itertools.groupby(entries, key=lambda e: e[0]):
        day_date = date.fromisoformat(day_iso)
        day = liturgics.Day(day_date.year, day_date.month, day_date.day,
                            tradition=Tradition.Greek)
        await day.ainitialize()
        displays = [r.pericope.sdisplay for r in await day.aget_readings()]
        served = [(d, await verse_set(d)) for d in displays]

        for _, title in group:
            overlapping = '-'
            try:
                wanted = await verse_set(parse_reading_citation(title))
            except ValueError:
                wanted = frozenset()
            if not wanted:
                status = 'unresolved'
            elif any(found == wanted for _, found in served):
                status = 'exact'
            elif overlaps := [d for d, found in served if found & wanted]:
                status = 'boundary'
                overlapping = ' | '.join(overlaps)
            else:
                status = 'different'
            lines.append(f'{day_iso}\t{title}\t{status}\t{overlapping}')
    return lines


class TestAntiochianReadingCitations(TestCase):
    def test_title_case_and_jude_preamble(self):
        self.assertEqual(
            parse_reading_citation("ST. JUDE'S FIRST UNIVERSAL LETTER 1:1-25"),
            'Jude 1:1-25',
        )

    def test_colon_before_new_chapter(self):
        self.assertEqual(
            parse_reading_citation('MARK 13:31-37: 14:1-2'),
            'Mark 13:31-37; 14:1-2',
        )

    def test_bare_range_after_semicolon_continues_chapter(self):
        self.assertEqual(
            parse_reading_citation('MATTHEW 10:32-33; 37-38; 19:27-30'),
            'Matthew 10:32-33, 37-38; 19:27-30',
        )

    def test_preamble_variants(self):
        for title, expected in (
            ("ST. JAMES' UNIVERSAL LETTER 2:1-13", 'James 2:1-13'),
            ('ST. PAUL TO THE HEBREWS 11:9-10, 32-40', 'Hebrews 11:9-10, 32-40'),
            ('ST. PAUL EPISTLE TO THE HEBREWS. 7:26-8:3', 'Hebrews 7:26-8:3'),
            ("ST. PAUL'S SECOND LETTER TO ST. TIMOTHY 3:10-15", '2 Timothy 3:10-15'),
            ('ST. JOHN. 10:9-16', 'John 10:9-16'),
        ):
            with self.subTest(title=title):
                self.assertEqual(parse_reading_citation(title), expected)

    def test_preserves_discontinuous_ranges(self):
        self.assertEqual(
            parse_reading_citation(
                "ST. PAUL'S FIRST LETTER TO THE CORINTHIANS 10:28-33; 11:1-8"
            ),
            '1 Corinthians 10:28-33; 11:1-8',
        )


class TestExactGreekReadingBoundaries(TestCase):
    fixtures = ['calendarium.json', 'commemorations.json']

    # Every field reported in the 2026 Antiochian/GOA comparison.
    CASES = (
        (2, 9, 'Epistle', '1 John 2.18-29; 3.1-8'),
        (2, 16, 'Epistle', '3 John 1.1-15'),
        (3, 1, 'Epistle', 'Heb 11.24-26, 32-40'),
        (4, 10, 'Gospel', 'Matt 27.62-66'),
        (4, 15, 'Epistle', 'Acts 2.22-38'),
        (5, 7, 'Epistle', 'Acts 26.1, 12-20'),
        (5, 8, 'Gospel', 'John 19.25-28, 21.24-25'),
        (5, 10, 'Epistle', 'Acts 11.19-30'),
        (5, 14, 'Epistle', 'Acts 14.20-28; 15.1-4'),
        (5, 15, 'Epistle', 'Acts 15.5-12'),
        (5, 18, 'Epistle', 'Acts 17.1-9'),
        (5, 18, 'Gospel', 'John 11.47-54'),
        (5, 21, 'Epistle', 'Acts 26.1, 12-20'),
        (5, 29, 'Epistle', 'Acts 27.1-44; 28.1'),
        (5, 30, 'Gospel', 'John 21.14-25'),
        (6, 2, 'Gospel', 'Matt 4.23-25; 5.1-13'),
        (6, 5, 'Epistle', 'Rom 2.14-28'),
        (6, 11, 'Epistle', 'Acts 11.19-30'),
        (6, 13, 'Epistle', 'Rom 3.19-24'),
        (6, 15, 'Epistle', 'Rom 7.1-14'),
        (6, 19, 'Epistle', 'Jude 1.1-25'),
        (6, 24, 'Gospel', 'Luke 1.1-25, 57-68, 76, 80'),
        (7, 6, 'Gospel', 'Matt 13.10-23, 43'),
        (7, 23, 'Epistle', '1 Cor 10.28-33; 11.1-8'),
        (7, 24, 'Epistle', '1 Cor 11.8-23'),
        (7, 25, 'Epistle', 'Gal 4.22-27'),
        (8, 13, 'Epistle', '2 Cor 4.1-12'),
        (8, 22, 'Epistle', '1 Cor 1.26-31; 2.1-5'),
        (8, 26, 'Gospel', 'Mark 3.20-27'),
        (8, 29, 'Epistle', 'Acts 13.25-33'),
        (9, 3, 'Epistle', 'Gal 1.1-3, 20-24; 2.1-5'),
        (9, 6, 'Gospel', 'Matt 22.2-14'),
        (9, 14, 'Gospel', 'John 19.6-11, 13-20, 25-28, 30'),
        (9, 19, 'Epistle', '1 Cor 1.26-31; 2.1-5'),
        (9, 23, 'Epistle', 'Gal 4.22-27'),
        (10, 12, 'Epistle', 'Phil 2.12-15'),
        (10, 18, 'Epistle', 'Col 4.5-11, 14-18'),
        (10, 22, 'Epistle', 'Col 1.24-29, 2.1'),
        (11, 22, 'Epistle', 'Eph 4.1-7'),
        (12, 9, 'Epistle', 'Gal 4.22-27'),
        (12, 10, 'Epistle', 'Titus 1.5-14'),
        (12, 22, 'Epistle', 'Heb 9.8-23'),
        (12, 28, 'Epistle', 'Heb 11.17-31'),
        (12, 30, 'Gospel', 'Mark 10.17-27'),
        (12, 31, 'Gospel', 'Mark 10.24-32'),
    )

    async def test_all_reported_fields_are_exact(self):
        for month, day, source, expected in self.CASES:
            with self.subTest(date=date(2026, month, day), source=source):
                pday = liturgics.Day(
                    2026, month, day, tradition=Tradition.Greek
                )
                await pday.ainitialize()
                readings = await pday.aget_readings()
                actual = {
                    reading.pericope.sdisplay
                    for reading in readings
                    if reading.source == source
                }
                self.assertIn(expected, actual)


class TestAntiochianReadingCharacterization(TestCase):
    """Pins how every harvested antiochian.org reading compares with orthocal.

    The hand-written cases above encode the reported 2026 defect. This covers
    every year in data/antiochian_raw instead, so a change that fixes one year
    while breaking another shows up as a readable diff naming the date. Lines
    marked `boundary` are known, unresolved differences, not accepted ones.

    data/ is excluded from the Docker image, so the titles are carried in the
    golden file itself. Regenerate deliberately, never to make a red test green:

        docker compose run --rm local python tools/greek/antiochian_characterize.py --write
    """

    fixtures = ['calendarium.json', 'commemorations.json']

    async def test_antiochian_comparison_is_unchanged(self):
        expected = GOLDEN.read_text().splitlines()
        entries = [line.split('\t')[:2] for line in expected]
        actual = await characterize(entries)

        differences = [(e, a) for e, a in zip(expected, actual) if e != a]
        if differences:
            report = '\n'.join(
                f'  expected: {e}\n  actual:   {a}' for e, a in differences[:10])
            self.fail(
                f'{len(differences)} of {len(expected)} readings changed. '
                f'First few:\n{report}'
            )
