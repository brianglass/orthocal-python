import datetime

from urllib.parse import urljoin, urlparse

import icalendar

from django.test import TestCase
from django.urls import resolve, reverse
from django.utils import timezone

from ..datetools import Calendar, Tradition
from ..ical import generate_ical


class CalendarTest(TestCase):
    fixtures = ['calendarium.json', 'commemorations.json']

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

    def test_ical_greek(self):
        """Greek tradition ical endpoint should return 200."""
        url = reverse('ical', kwargs={'tradition': Tradition.Greek, 'cal': Calendar.Gregorian})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_ical_greek_urls(self):
        """urls should point to Greek tradition readings."""
        url = reverse('ical', kwargs={'tradition': Tradition.Greek, 'cal': Calendar.Gregorian})
        response = self.client.get(url)
        cal = icalendar.Calendar.from_ical(response.content)
        for event in cal.walk('vevent'):
            parts = urlparse(event['url'])
            match = resolve(parts.path)
            self.assertEqual(match.kwargs['tradition'], Tradition.Greek)

    def test_ical_slavic_name_unchanged(self):
        """Slavic calendar name/uid must keep their original format, since
        existing subscribers' calendar apps use the uid to track events."""
        url = reverse('ical', kwargs={'cal': Calendar.Gregorian})
        response = self.client.get(url)
        cal = icalendar.Calendar.from_ical(response.content)
        self.assertEqual(str(cal.get('name')), 'Orthodox Feasts and Fasts (Gregorian)')
        for event in cal.walk('vevent'):
            self.assertNotIn('Slavic', str(event.get('uid')))

    def test_ical_greek_name_distinguishes_tradition(self):
        url = reverse('ical', kwargs={'tradition': Tradition.Greek, 'cal': Calendar.Gregorian})
        response = self.client.get(url)
        cal = icalendar.Calendar.from_ical(response.content)
        self.assertIn('Greek', str(cal.get('name')))

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
        """ical with timestamp of Jan 7, 2022 should have Synaxis of St. John.

        Synaxis of St John the Baptist is Jan 7's sole significant
        commemoration, so its original Day.feast_name text (restored after
        the feast_name/DayCommemoration de-duplication audit briefly
        blanked it, 2026-08) drives summary_title directly rather than
        falling back to a join of that day's other commemorations."""

        def build_absolute_uri(url):
            return urljoin('http://testserver', url)

        timestamp = datetime.datetime(2022, 1, 7, tzinfo=datetime.timezone.utc)
        cal = await generate_ical(timestamp, Calendar.Gregorian, Tradition.Slavic, build_absolute_uri)
        for event in cal.walk('vevent'):
            if event['dtstart'].dt == timestamp.date():
                summary = event.decoded('summary')
                self.assertIn('Synaxis', summary)
                self.assertIn('John the Baptist', summary)
                break
        else:
            self.fail('No event for timestamp found')

    async def test_ical_content_julian(self):
        """ical with timestamp of Jan 7, 2022 should have Nativity of Christ."""

        def build_absolute_uri(url):
            return urljoin('http://testserver', url)

        timestamp = datetime.datetime(2022, 1, 7, tzinfo=datetime.timezone.utc)
        cal = await generate_ical(timestamp, Calendar.Julian, Tradition.Slavic, build_absolute_uri)
        for event in cal.walk('vevent'):
            if event['dtstart'].dt == timestamp.date():
                summary = event.decoded('summary')
                self.assertEqual(summary, 'Nativity of Christ')
                break
        else:
            self.fail('No event for timestamp found')

    def test_event_all_day(self):
        """Events should be all-day events."""

        url = reverse('ical', kwargs={'cal': Calendar.Gregorian})
        response = self.client.get(url)
        cal = icalendar.Calendar.from_ical(response.content)
        for event in cal.walk('vevent'):
            self.assertFalse(isinstance(event['dtstart'].dt, datetime.datetime))
            length = event['dtend'].dt - event['dtstart'].dt
            self.assertEqual(length, datetime.timedelta(days=1))
