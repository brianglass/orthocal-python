import datetime

from urllib.parse import urljoin, urlparse

import icalendar

from django.test import TestCase
from django.urls import resolve, reverse
from django.utils import timezone

from ..datetools import Calendar
from ..ical import generate_ical


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

    async def test_ical_content(self):
        """ical with timestamp of Jan 7, 2022 should have Synaxis of St. John."""

        def build_absolute_uri(url):
            return urljoin('http://testserver', url)

        timestamp = datetime.datetime(2022, 1, 7, tzinfo=datetime.timezone.utc)
        cal = await generate_ical(timestamp, Calendar.Gregorian, build_absolute_uri)
        for event in cal.walk('vevent'):
            if event['dtstart'].dt.date() == timestamp.date():
                summary = event.decoded('summary')
                self.assertEqual(summary, 'Synaxis of St John the Baptist')
                break
        else:
            self.fail('No event for timestamp found')

    async def test_ical_content_julian(self):
        """ical with timestamp of Jan 7, 2022 should have Nativity of Christ."""

        def build_absolute_uri(url):
            return urljoin('http://testserver', url)

        timestamp = datetime.datetime(2022, 1, 7, tzinfo=datetime.timezone.utc)
        cal = await generate_ical(timestamp, Calendar.Julian, build_absolute_uri)
        for event in cal.walk('vevent'):
            if event['dtstart'].dt.date() == timestamp.date():
                summary = event.decoded('summary')
                self.assertEqual(summary, 'Nativity of Christ')
                break
        else:
            self.fail('No event for timestamp found')
