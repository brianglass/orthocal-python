from datetime import date

from django.test import TestCase

from .. import datetools, liturgics


class TestYear(TestCase):
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

    def test_lucan_jump(self):
        # TODO: Confirm this is actually working
        year = liturgics.Year(2018, False)
        self.assertEqual(year.lucan_jump, 7)

    def test_daily_readings(self):
        year = liturgics.Year(2018, False)

        expected = 266, 280, 268, 272, 273, 252, 259, 260, 261, 262, 266
        for day in expected:
            with self.subTest():
                self.assertFalse(year.has_daily_readings(day))

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
    fixtures = ['calendarium.json']

    def test_commemorations(self):
        day = liturgics.Day(2023, 2, 26)

        print(day.titles)
        print(day.saints)
        print(day.feasts)
        print(day.feast_level)
        print(day.fast_level)
        print(day.fast_exception)

        print(day.readings)

        for r in day.readings:
            print(r.passage)

    def test_paremias(self):
        day = liturgics.Day(2023, 3, 30)

        print(day.titles)
        print(day.saints)
        print(day.feasts)
        print(day.feast_level)
        print(day.fast_level)
        print(day.fast_exception)

        print(day.readings)

        for r in day.readings:
            print(r.passage)

    def test_tone(self):
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
            with self.subTest(tone):
                day = liturgics.Day(year, month, day)
                self.assertEqual(tone, day.tone)
