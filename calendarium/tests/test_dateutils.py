from datetime import date

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

    def test_julian_to_gregorian_error(self):
        tests = [
            date(2100, 4, 14),
            date(1900, 4, 14),
        ]

        for julian in tests:
            with self.subTest():
                with self.assertRaises(Exception):
                    datetools.julian_to_gregorian(julian)

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
        distance = 31
        expected = datetools.Weekday.Wednesday
        actual = datetools.weekday_from_pdist(distance)
        self.assertEqual(expected, actual)
