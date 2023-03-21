from urllib.parse import urlparse

import icalendar

from django.test import TestCase
from django.urls import resolve, reverse

from ..datetools import Calendar


class CalendarTest(TestCase):
    fixtures = ['calendarium.json']

    def test_ical(self):
        """ical endpoint should return 200."""
        url = reverse('ical', kwargs={'cal': Calendar.Gregorian})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_ical_julian(self):
        """ical Julian endpoint should return 200."""
        url = reverse('ical', kwargs={'cal': Calendar.Julian})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_ical_urls(self):
        """urls should point to Gregorian readings."""
        url = reverse('ical', kwargs={'cal': Calendar.Gregorian})
        response = self.client.get(url)
        cal = icalendar.Calendar.from_ical(response.content)
        for event in cal.walk('vevent'):
            parts = urlparse(event['url'])
            match = resolve(parts.path)
            self.assertEqual(match.kwargs['cal'], Calendar.Gregorian)

    def test_ical_julian_urls(self):
        """urls should point to Julian readings."""
        url = reverse('ical', kwargs={'cal': Calendar.Julian})
        response = self.client.get(url)
        cal = icalendar.Calendar.from_ical(response.content)
        for event in cal.walk('vevent'):
            parts = urlparse(event['url'])
            match = resolve(parts.path)
            self.assertEqual(match.kwargs['cal'], Calendar.Julian)
