import json

from pathlib import Path

from dateutil.rrule import rrule, DAILY
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent


class DayAPITestCase(TestCase):
    fixtures = ['calendarium.json', 'commemorations.json']

    def test_get_day(self):
        with open(BASE_DIR / 'data/last_bday.json') as f:
            expected = json.loads(f.read())

        url = reverse('api:get_calendar_day', kwargs={
            'cal': 'gregorian',
            'year': 2022,
            'month': 1,
            'day': 7,
        })
        response = self.client.get(url, format='json')
        actual = response.json()

        self.assertEqual(expected, actual)

    def test_get_day_default(self):
        url = reverse('api:get_calendar_default', kwargs={'cal': 'gregorian'})
        response = self.client.get(url, format='json')
        dt = timezone.localtime()
        actual = response.json()
        self.assertEqual(dt.year, actual['year'])
        self.assertEqual(dt.month, actual['month'])
        self.assertEqual(dt.day, actual['day'])

    def test_list_days(self):
        with open(BASE_DIR / 'data/january.json') as f:
            expected = json.loads(f.read())

        url = reverse('api:get_calendar_month', kwargs={
            'cal': 'gregorian',
            'year': 2022,
            'month': 1,
        })
        response = self.client.get(url, format='json')
        actual = response.json()

        self.assertEqual(expected, actual)

    def test_theophany(self):
        with open(BASE_DIR / 'data/theophany.json') as f:
            expected = json.loads(f.read())

        url = reverse('api:get_calendar_day', kwargs={
            'cal': 'gregorian',
            'year': 2023,
            'month': 1,
            'day': 6,
        })
        response = self.client.get(url, format='json')
        actual = response.json()

        self.assertEqual(expected, actual)

    def test_errors(self):
        """We shouldn't have any errors in the API."""

        # This is just a brute force test to make sure we don't have any
        # errors in the API.
        start_dt = timezone.datetime(2023, 1, 1)
        end_dt = timezone.datetime(2029, 12, 31)
        for dt in rrule(DAILY, dtstart=start_dt, until=end_dt):
            with self.subTest(dt=dt):
                url = reverse('api:get_calendar_day', kwargs={
                    'cal': 'gregorian',
                    'year': dt.year,
                    'month': dt.month,
                    'day': dt.day,
                })
                response = self.client.get(url, format='json')
                self.assertEqual(response.status_code, 200)
