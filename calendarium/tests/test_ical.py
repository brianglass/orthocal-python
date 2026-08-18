import datetime

from urllib.parse import urljoin, urlparse

import icalendar

from django.test import TestCase
from django.urls import resolve, reverse
from django.utils import timezone

from ..datetools import Calendar, Tradition
from ..ical import generate_ical

# The four Great Fasts' multi-day events don't carry a url or a fixed
# one-day length the way the daily commemoration events do -- tests that
# check those fields on every event need to skip them.
_FAST_UID_PREFIXES = ('great_lent-', 'apostles_fast-', 'dormition_fast-', 'nativity_fast-')


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
            if str(event.get('uid')).startswith(_FAST_UID_PREFIXES):
                continue
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
            if str(event.get('uid')).startswith(_FAST_UID_PREFIXES):
                continue
            parts = urlparse(event['url'])
            match = resolve(parts.path)
            self.assertEqual(match.kwargs['cal'], Calendar.Gregorian)

    def test_ical_julian_urls(self):
        """urls should point to Julian readings."""

        url = reverse('ical', kwargs={'cal': Calendar.Julian})
        response = self.client.get(url)
        cal = icalendar.Calendar.from_ical(response.content)
        for event in cal.walk('vevent'):
            if str(event.get('uid')).startswith(_FAST_UID_PREFIXES):
                continue
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
        """Events should be all-day events. The four Great Fasts are
        legitimately multi-day; every other event (the daily commemoration
        entries) is exactly one day long."""

        url = reverse('ical', kwargs={'cal': Calendar.Gregorian})
        response = self.client.get(url)
        cal = icalendar.Calendar.from_ical(response.content)
        for event in cal.walk('vevent'):
            self.assertFalse(isinstance(event['dtstart'].dt, datetime.datetime))
            length = event['dtend'].dt - event['dtstart'].dt
            if str(event.get('uid')).startswith(_FAST_UID_PREFIXES):
                self.assertGreater(length, datetime.timedelta(days=1))
            else:
                self.assertEqual(length, datetime.timedelta(days=1))

    async def test_ical_includes_great_fasts(self):
        """The ical feed includes one multi-day event per Great Fast."""

        def build_absolute_uri(url):
            return urljoin('http://testserver', url)

        timestamp = datetime.datetime(2026, 1, 15, tzinfo=datetime.timezone.utc)
        cal = await generate_ical(timestamp, Calendar.Gregorian, Tradition.Slavic, build_absolute_uri)
        uids = {str(event.get('uid')) for event in cal.walk('vevent')}
        self.assertIn('great_lent-2026-02-23.Gregorian@orthocal.info', uids)
        self.assertIn('apostles_fast-2026-06-08.Gregorian@orthocal.info', uids)
        self.assertIn('nativity_fast-2025-11-15.Gregorian@orthocal.info', uids)

    async def test_ical_skips_empty_apostles_fast(self):
        """2024 has no Apostles' Fast (Pascha fell too late) -- it should
        be skipped rather than emitted as a malformed, inverted event."""

        def build_absolute_uri(url):
            return urljoin('http://testserver', url)

        timestamp = datetime.datetime(2024, 6, 20, tzinfo=datetime.timezone.utc)
        cal = await generate_ical(timestamp, Calendar.Gregorian, Tradition.Slavic, build_absolute_uri)
        for event in cal.walk('vevent'):
            self.assertNotIn('apostles_fast', str(event.get('uid')))
