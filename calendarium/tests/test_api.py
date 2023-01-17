import json

from pathlib import Path

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent


class DayAPITestCase(APITestCase):
    fixtures = ['calendarium.json', 'commemorations.json']

    def test_get_day(self):
        with open(BASE_DIR / 'data/last_bday.json') as f:
            expected = json.loads(f.read())

        url = reverse('day-get', kwargs={
            'cal': 'gregorian',
            'year': 2022,
            'month': 1,
            'day': 7,
        })
        response = self.client.get(url, format='json')
        actual = response.json()

        self.assertEqual(expected, actual)

    def test_get_day_default(self):
        url = reverse('day-get-default', kwargs={'cal': 'gregorian'})
        response = self.client.get(url, format='json')
        dt = timezone.localtime()
        actual = response.json()
        self.assertEqual(dt.year, actual['year'])
        self.assertEqual(dt.month, actual['month'])
        self.assertEqual(dt.day, actual['day'])

    def test_list_days(self):
        with open(BASE_DIR / 'data/january.json') as f:
            expected = json.loads(f.read())

        url = reverse('day-list', kwargs={
            'cal': 'gregorian',
            'year': 2022,
            'month': 1,
        })
        response = self.client.get(url, format='json')
        actual = response.json()

        self.assertEqual(expected, actual)
