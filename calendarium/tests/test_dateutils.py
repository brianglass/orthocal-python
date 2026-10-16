from datetime import date, timedelta

from django.test import TestCase

from .. import datetools


class TestDateutil(TestCase):
    def test_gregorian_date_to_jdn(self):
        tests = [
            (date(2018, 1, 15), 2458134),
            (date(2000, 5, 29), 2451694),
        ]

        for day, expected in tests:
            with self.subTest():
                actual = datetools.gregorian_to_jdn(day)
                self.assertEqual(actual, expected)

    def test_gregorian_to_julian_century_leap_day(self):
        """The Julian calendar leaps in 1700, 1900, 2100... and the Gregorian
        doesn't, so those Julian Feb 29s can't be Python dates."""

        tests = [
            ((2100, 3, 13), (2100, 2, 28)),
            ((2100, 3, 14), (2100, 2, 29)),
            ((2100, 3, 15), (2100, 3, 1)),
            ((1900, 3, 13), (1900, 2, 29)),
            ((1700, 3, 11), (1700, 2, 29)),
            ((2026, 10, 16), (2026, 10, 3)),
        ]

        for gregorian, expected in tests:
            with self.subTest(gregorian):
                actual = datetools.gregorian_to_julian(*gregorian)
                self.assertEqual(actual, datetools.JulianDate(*expected))

    def test_julian_date_arithmetic(self):
        feb28 = datetools.JulianDate(2100, 2, 28)
        self.assertEqual(feb28 + timedelta(days=1), datetools.JulianDate(2100, 2, 29))
        self.assertEqual(feb28 + timedelta(days=2), datetools.JulianDate(2100, 3, 1))
        self.assertEqual(datetools.JulianDate(2100, 3, 1) - timedelta(days=1), datetools.JulianDate(2100, 2, 29))
        self.assertEqual(datetools.JulianDate(2025, 12, 31) + timedelta(days=1), datetools.JulianDate(2026, 1, 1))

    def test_julian_date_str(self):
        self.assertEqual(str(datetools.JulianDate(2100, 2, 29)), '2100-02-29')

    def test_julian_to_jdn(self):
        expected = 2455676
        actual = datetools.julian_to_jdn(date(2011, 4, 11))
        self.assertEqual(expected, actual)

    def test_compute_pascha_jdn(self):
        data = [
            (2022, 2459694),
            (2011, 2455676),
        ]

        for year, pascha in data:
            with self.subTest(year):
                actual = datetools.compute_pascha_jdn(year)
                self.assertEqual(pascha, actual)

    def test_compute_pascha_distance(self):
        tests = [
            (date(2018, 5, 9), 31, 2018),
            (date(2018, 1, 1), 260, 2017),
        ]

        for dt, expected_distance, expected_year in tests:
            with self.subTest():
                distance, year = datetools.compute_pascha_distance(dt)
                self.assertEqual(expected_distance, distance)
                self.assertEqual(expected_year, year)

    def test_weekday_from_pdist(self):
        data = [
            (-15, datetools.Weekday.Saturday),
            (-14, datetools.Weekday.Sunday),
            (-13, datetools.Weekday.Monday),
            (-1, datetools.Weekday.Saturday),
            (0, datetools.Weekday.Sunday),
            (31, datetools.Weekday.Wednesday),
            (49, datetools.Weekday.Sunday),
        ]

        for distance, expected in data:
            with self.subTest(distance):
                actual = datetools.weekday_from_pdist(distance)
                self.assertEqual(expected, actual)

    def test_surrounding_weekends(self):
        data = [
            (37, (34, 35, 41, 42)),         # May 23, 2023
            (41, (34, 35, 48, 42)),         # May 27, 2023
            (-61, (-64, -63, -57, -56)),    # February 14, 2023
            (-63, (-64, -70, -57, -56)),    # February 12, 2023
        ]

        for pdist, expected in data:
            with self.subTest(pdist):
                actual = datetools.surrounding_weekends(pdist)
                self.assertEqual(expected, actual)
