from datetime import date

from django.test import TestCase

from .. import datetools, liturgics


class TestYear(TestCase):
    fixtures = ['calendarium.json', 'commemorations.json']

    def test_pascha(self):
        year = liturgics.Year(2018, False)
        pascha = datetools.gregorian_to_jdn(date(2018, 4, 8))
        self.assertEqual(year.pascha, pascha)

    def test_pdists(self):
        year = liturgics.Year(2018, False)
        pascha = datetools.gregorian_to_jdn(date(2018, 4, 8))

        data = [
                (date(2019, 1, 6), 'theophany'),
                (date(2018, 2, 24), 'finding'),
                (date(2018, 3, 25), 'annunciation'),
                (date(2018, 6, 29), 'peter_and_paul'),
                (date(2018, 7, 15), 'fathers_six'),
                (date(2018, 8, 29), 'beheading'),
                (date(2018, 9, 8), 'nativity_theotokos'),
                (date(2018, 9, 14), 'elevation'),
                (date(2018, 10, 14), 'fathers_seven'),
                (date(2018, 10, 20), 'demetrius_saturday'),
                (date(2018, 12, 16), 'forefathers'),
                (date(2018, 12, 25), 'nativity'),
        ]

        for dt, feast in data:
            with self.subTest(feast):
                actual = getattr(year, feast)
                expected = datetools.gregorian_to_jdn(dt) - pascha
                self.assertEqual(actual, expected)

    def test_lukan_jump(self):
        # TODO: Confirm this is actually working
        year = liturgics.Year(2018, False)
        self.assertEqual(year.lukan_jump, 7) 

    def test_daily_readings(self):
        data = [
            (2018, {266, 280, 268, 272, 273, 252, 259, 260, 261, 262, 266}),
            (2023, {259, 266, 260, 264, 265, 245, 252, 252, 253, 254, 259, -22}),
        ]

        for year, days in data:
            year = liturgics.Year(year)
            with self.subTest(year):
                self.assertSetEqual(year.no_daily, days)

    def test_reserves(self):
        year = liturgics.Year(2018, False)

        self.assertEqual(year.extra_sundays, 3)
        expected = 266, 161, 168
        self.assertSequenceEqual(year.reserves, expected)

    def test_has_no_paremias(self):
        year = liturgics.Year(2018, False)
        noparemias = -43, -40, -30, -8
        for pdist in noparemias:
            with self.subTest(pdist):
                self.assertTrue(year.has_no_paremias(pdist))

    def test_has_paremias(self):
        year = liturgics.Year(2018, False)
        paremias = -44, -41, -31, -9
        for pdist in paremias:
            with self.subTest(pdist):
                self.assertTrue(year.has_moved_paremias(pdist))


class TestDay(TestCase):
    fixtures = ['calendarium.json', 'commemorations.json']

    async def test_no_memorial(self):
        """Memorial Saturday with no memorial readings should not have John 5.24-30."""

        day = liturgics.Day(2022, 3, 26)
        await day.ainitialize()
        readings = await day.aget_readings()
        short_displays = [r.pericope.sdisplay for r in readings]
        self.assertNotIn('John 5.24-30', short_displays)

    async def test_scriptures(self):
        # Cheesefare Sunday
        day = liturgics.Day(2018, 2, 18)
        await day.ainitialize()
        readings = await day.aget_readings()

        self.assertEqual(len(readings), 3)

        count = await readings[0].pericope.get_passage().acount()
        self.assertEqual(count, 12)
        count = await readings[1].pericope.get_passage().acount()
        self.assertEqual(count, 8)
        count = await readings[2].pericope.get_passage().acount()
        self.assertEqual(count, 8)

    async def test_scriptures_pascha(self):
        day = liturgics.Day(2023, 4, 16)
        await day.ainitialize()
        readings = await day.aget_readings()

        self.assertEqual(len(readings), 2)

        self.assertEqual('Acts 1.1-8', readings[0].pericope.display)
        self.assertEqual('John 1.1-17', readings[1].pericope.display)

        # TODO: This is the Paschal Vespers. There are some missing records in
        # the fixtures that we need to update from
        # https://github.com/paulkachur/orthodox_calendar

        #self.assertEqual('John 20.19-25', readings[2].pericope.display)

    async def test_annunciation(self):
        """Test a sample feast day."""

        day = liturgics.Day(2018, 3, 25)
        await day.ainitialize()

        self.assertIn('Annunciation Most Holy Theotokos', day.feasts)
        self.assertIn('St Mary of Egypt', day.feasts)

        self.assertEqual(day.feast_level, 7)
        self.assertEqual(day.fast_level, 2)
        self.assertEqual(day.fast_exception, 4)
        readings = await day.aget_readings()
        self.assertEqual(len(readings), 12)

    async def test_paremias(self):
        """Paremias should be moved from the subsequent day."""

        day = liturgics.Day(2018, 3, 8)
        await day.ainitialize()
        readings = await day.aget_readings()
        self.assertEqual(len(readings), 6)

    async def test_sebaste(self):
        """Paremias should be moved to the previous day."""

        day = liturgics.Day(2018, 3, 9)
        await day.ainitialize()
        readings = await day.aget_readings()

        self.assertEqual(len(readings), 6)
        self.assertEqual(readings[0].source, 'Matins Gospel')

        short_displays = [r.pericope.sdisplay for r in readings]
        self.assertEqual(len(short_displays), len(set(short_displays)))

    async def test_tone(self):
        data = [
			(2023, 1, 1, 4),   # 29th Sunday after Pentecost
			(2023, 4, 8, 0),   # Lazarus Saturday
			(2023, 4, 17, 2),  # Bright Friday
			(2023, 4, 21, 6),  # Bright Friday
			(2023, 4, 22, 8),  # Bright Saturday
			(2023, 4, 23, 1),  # Thomas Sunday
			(2023, 6, 11, 8),  # 1st Sunday after Pentecost; All Saints
            (2023, 6, 18, 1),  # 2nd Sunday after Pentecost
        ]

        for year, month, day, tone in data:
            day = liturgics.Day(year, month, day)
            await day.ainitialize()
            with self.subTest(tone):
                self.assertEqual(tone, day.tone)

    async def test_fasting_levels(self):
        # Use Apostles Fast as a test case
        data = [
			(2018, 6, 3, 0, 0),
			(2018, 6, 4, 3, 0),
			(2018, 6, 12, 3, 1),
			(2018, 6, 14, 3, 1),
			(2018, 6, 16, 3, 2),
			(2018, 6, 17, 3, 2),
			(2018, 6, 28, 3, 1),
			(2018, 6, 29, 1, 2),
			(2018, 6, 30, 0, 0),
        ]

        for year, month, day, fast, exception in data:
            day = liturgics.Day(year, month, day)
            await day.ainitialize()
            with self.subTest():
                self.assertEqual(day.fast_level, fast)
                self.assertEqual(day.fast_exception, exception)

    async def test_fast_free(self):
        """Test fast free days."""

        data = [
			(2018, 12, 26, 0, "No Fast"),
			(2018, 12, 28, 0, "No Fast"),
			(2019, 1, 2, 0, "No Fast"),
			(2019, 1, 4, 0, "No Fast"),
        ]

        for year, month, day, fast, description in data:
            day = liturgics.Day(year, month, day)
            await day.ainitialize()
            with self.subTest():
                self.assertEqual(day.fast_level, fast)
                self.assertEqual(day.fast_level_desc, description)

    async def test_eothinon(self):
        data = [
            (2018, 3, 11, 7),
            (2023, 1, 1, 7),
            (2023, 1, 8, 8),
        ]

        for year, month, day, gospel in data:
            day = liturgics.Day(year, month, day)
            await day.ainitialize()
            with self.subTest(gospel):
                self.assertEqual(day.eothinon_gospel, gospel)

    async def test_composites(self):
        """Test for composite scripture readings."""

        # The lengths are slightly different than the Go version because they
        # are unicode rather than utf-8.
        data = [
			(2019, 2, 27, 0, 1378), # 2
			(2019, 2, 24, 0, 1486), # 3
			(2019, 2, 24, 1, 1357), # 8
			(2019, 2, 24, 2, 1306), # 9
        ]

        for year, month, day, reading, length in data:
            day = liturgics.Day(year, month, day)
            await day.ainitialize()
            readings = await day.aget_readings()
            with self.subTest(f'{day}: {reading}'):
                passage = readings[reading].pericope.get_passage()
                verse = await passage.afirst()
                self.assertEqual(len(verse.content), length)

    async def test_abbreviated_readings(self):
        data = [
			(2023, 2, 5, 2),    # Sunday of the Publican and Pharisee; 2 NT readings
			(2023, 2, 27, 3),   # first day of Lent + St. Raphael of Brooklyn; 3 OT readings
			(2023, 2, 28, 3),   # second day of Lent; 3 OT readings
			(2023, 3, 9, 2),    # Holy 40 Martyrs of Sebaste during Lent; should be 2 NT readings
			(2023, 3, 24, 3),   # Forefeast of Annunciation; should be 3 OT readings
			(2023, 3, 25, 2),   # Annunciation; should be 2 NT readings
			(2023, 4, 14, 2),   # Holy Thursday; should NOT include passion gospels
        ]

        for year, month, day, length in data:
            day = liturgics.Day(year, month, day)
            await day.ainitialize()
            readings = await day.aget_abbreviated_readings()
            with self.subTest(f'{day}'):
                self.assertEqual(length, len(readings))

    async def test_new_martyrs_russia(self):
        data = [
            (2023, 1, 22),
            (2022, 1, 23),
        ]
        for y, m, d in data:
            day = liturgics.Day(y, m, d)
            await day.ainitialize()
            with self.subTest(y):
                self.assertIn('New Martyrs and Confessors of Russia', day.feasts)

    async def test_gospel_pdist(self):
        data = [
            (2022, 12, 4, 252),  # 25th Sunday after Pentecost -> with jump, 28th, swapped to 29th
        ]

        for y, m, d, pdist in data:
            day = liturgics.Day(y, m, d)
            await day.ainitialize()
            with self.subTest(day.gregorian_date):
                self.assertEqual(day.gospel_pdist, pdist)
