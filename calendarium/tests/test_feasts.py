from datetime import date

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .. import liturgics
from ..datetools import Calendar, FastLevels, Tradition


class YearOfFeastsTestCase(TestCase):
    fixtures = ['calendarium.json', 'commemorations.json']

    def test_gregorian(self):
        feasts, seasons = liturgics.year_of_feasts(2027, calendar=Calendar.Gregorian, tradition=Tradition.Slavic)

        self.assertEqual([f.date for f in feasts], sorted(f.date for f in feasts))
        self.assertEqual(feasts[0].date, date(2027, 1, 1))
        self.assertEqual(feasts[0].name, 'Circumcision of Our Lord')

        # Pascha and the Twelve Great Feasts.
        self.assertEqual(len([f for f in feasts if f.is_great]), 13)
        pascha, = [f for f in feasts if f.is_pascha]
        self.assertEqual(pascha.date, date(2027, 5, 2))

        # Named for the feast, not St Mark, who shares the day in 2027.
        palm_sunday, = [f for f in feasts if f.pdist == -7]
        self.assertEqual(palm_sunday.name, 'Palm Sunday')

        self.assertEqual(
            [(s.level, s.start, s.end) for s in seasons],
            [
                (FastLevels.LentenFast, date(2027, 3, 15), date(2027, 5, 1)),
                # Pascha is late in 2027, which leaves one day before the feast.
                (FastLevels.ApostlesFast, date(2027, 6, 28), date(2027, 6, 28)),
                (FastLevels.DormitionFast, date(2027, 8, 1), date(2027, 8, 14)),
                (FastLevels.NativityFast, date(2027, 11, 15), date(2027, 12, 24)),
            ],
        )

    def test_julian_seasons_cross_new_year(self):
        """On the Julian calendar the Nativity Fast ends on civil January 6,
        so the year opens and closes inside one, and each is given whole."""

        feasts, seasons = liturgics.year_of_feasts(2027, calendar=Calendar.Julian, tradition=Tradition.Slavic)

        self.assertEqual((feasts[0].date, feasts[0].name), (date(2027, 1, 7), 'Nativity of Christ'))
        self.assertEqual((seasons[0].start, seasons[0].end), (date(2026, 11, 28), date(2027, 1, 6)))
        self.assertEqual((seasons[-1].start, seasons[-1].end), (date(2027, 11, 28), date(2028, 1, 6)))
        self.assertEqual(seasons[-1].days, 40)

    def test_greek(self):
        feasts, _ = liturgics.year_of_feasts(2027, calendar=Calendar.Gregorian, tradition=Tradition.Greek)
        names = [f.name for f in feasts]

        self.assertIn('Nativity of Christ', names)
        # The Protection is a Slavic-only great feast.
        self.assertNotIn('Protection (Pokrov) of the Most-Holy Theotokos', names)

    def test_last_supported_year(self):
        """The Nativity Fast running past the last supported year is cut off
        there instead of failing."""

        _, seasons = liturgics.year_of_feasts(4099, calendar=Calendar.Julian, tradition=Tradition.Slavic)
        self.assertEqual(seasons[-1].end, date(4099, 12, 31))


class FeastsViewTestCase(TestCase):
    fixtures = ['calendarium.json', 'commemorations.json']

    def test_default(self):
        response = self.client.get(reverse('feasts-default'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['year'], timezone.localtime().year)

    def test_year(self):
        url = reverse('feasts', kwargs={'tradition': 'slavic', 'cal': 'gregorian', 'year': 2027})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'The Resurrection of our Lord and Savior Jesus Christ')
        self.assertContains(response, 'Nativity Fast')
        pascha = reverse('readings', kwargs={'tradition': 'slavic', 'cal': 'gregorian', 'year': 2027, 'month': 5, 'day': 2})
        self.assertContains(response, f'href="{pascha}"')

    def test_julian_shows_neighboring_years(self):
        url = reverse('feasts', kwargs={'tradition': 'slavic', 'cal': 'julian', 'year': 2027})
        response = self.client.get(url)

        self.assertContains(response, 'Nov 28, 2026')
        self.assertContains(response, 'Jan 6, 2028')

    def test_remembers_calendar(self):
        url = reverse('feasts', kwargs={'tradition': 'slavic', 'cal': 'julian', 'year': 2027})
        self.client.get(f'{url}?foo')  # We send an argument to bypass caching
        response = self.client.get(reverse('feasts-default'))

        self.assertEqual(response.context['cal'], Calendar.Julian)


class FeastsAPITestCase(TestCase):
    fixtures = ['calendarium.json', 'commemorations.json']

    def test_feasts(self):
        response = self.client.get('/api/slavic/julian/feasts/2027/')
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data['year'], 2027)
        self.assertEqual(data['feasts'][0], {
            'date': '2027-01-07',
            'weekday': 4,
            'name': 'Nativity of Christ',
            'feast_level': 8,
            'great_feast': True,
            'pascha_distance': 270,
        })
        self.assertEqual(data['fasts'][0], {
            'name': 'Nativity Fast',
            'fast_level': 5,
            'start': '2026-11-28',
            'end': '2027-01-06',
            'days': 40,
        })
