import json
import os

from pathlib import Path
from unittest import mock

from dateutil.rrule import rrule, DAILY
from django.core.cache import cache
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from .. import api

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent


class ClientIpMixinTestCase(TestCase):
    def setUp(self):
        self.throttle = api.ShadowAnonRateThrottle('5/s')
        self.factory = RequestFactory()

    def test_uses_first_xff_entry(self):
        """Cloud Run puts the real client IP first in X-Forwarded-For and
        appends its own hop(s) after it; those appended hops can vary
        between requests from the same client, so only the first entry is
        a stable per-client identity."""
        request = self.factory.get('/', HTTP_X_FORWARDED_FOR='203.0.113.5, 66.249.82.68')
        self.assertEqual('203.0.113.5', self.throttle.get_ident(request))

    def test_falls_back_to_remote_addr(self):
        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '203.0.113.5'
        self.assertEqual('203.0.113.5', self.throttle.get_ident(request))


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

    def test_get_day_invalid(self):
        with open(BASE_DIR / 'data/last_bday.json') as f:
            expected = json.loads(f.read())

        url = reverse('api:get_calendar_day', kwargs={
            'cal': 'gregorian',
            'year': 2022,
            'month': 2,
            'day': 29,
        })
        response = self.client.get(url, format='json')
        self.assertEqual(404, response.status_code)

    def test_get_day_translation(self):
        """The optional translation query parameter should change passage
        content without needing a new route, defaulting to KJV when absent."""
        url = reverse('api:get_calendar_day', kwargs={
            'cal': 'gregorian',
            'year': 2022,
            'month': 1,
            'day': 7,
        })

        kjv_response = self.client.get(url, format='json')
        lxx_response = self.client.get(url, {'translation': 'lxx2012-web'}, format='json')

        kjv_gospel = kjv_response.json()['readings'][2]
        lxx_gospel = lxx_response.json()['readings'][2]

        self.assertEqual(kjv_gospel['display'], 'John 1.29-34')
        self.assertEqual(lxx_gospel['display'], 'John 1.29-34')
        self.assertNotEqual(kjv_gospel['passage'][0]['content'], lxx_gospel['passage'][0]['content'])

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

    def test_nativity_julian(self):
        url = reverse('api:get_calendar_day', kwargs={
            'cal': 'julian',
            'year': 2023,
            'month': 1,
            'day': 7,
        })
        response = self.client.get(url, format='json')
        actual = response.json()

        self.assertIn('Nativity of Christ', actual['feasts'])

    def test_calendar_month_julian(self):
        url = reverse('api:get_calendar_month', kwargs={
            'cal': 'julian',
            'year': 2023,
            'month': 1,
        })
        response = self.client.get(url, format='json')
        actual = response.json()
        nativity = actual[6]

        self.assertIn('Nativity of Christ', nativity['feasts'])

    def test_calendar_month_julian_range_error_low(self):
        url = reverse('api:get_calendar_month', kwargs={
            'cal': 'julian',
            'year': 1583,
            'month': 1,
        })
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, 404)

    def test_calendar_month_julian_century_leap_day(self):
        """A Julian leap year is not always a Gregorian leap year: the Julian
        Feb 29 in 1700, 1900, 2100... falls in civil March."""

        for year, civil_day in [(1700, 11), (1900, 13), (2100, 14)]:
            with self.subTest(year):
                url = reverse('api:get_calendar_month', kwargs={
                    'cal': 'julian',
                    'year': year,
                    'month': 3,
                })
                response = self.client.get(url, format='json')
                self.assertEqual(response.status_code, 200)

                leap_day = response.json()[civil_day - 1]
                self.assertEqual((leap_day['month'], leap_day['day']), (2, 29))

    def test_calendar_day_julian_century_leap_day(self):
        url = reverse('api:get_calendar_day', kwargs={
            'cal': 'julian',
            'year': 2100,
            'month': 3,
            'day': 14,
        })
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual((response.json()['month'], response.json()['day']), (2, 29))

    def test_calendar_month_julian_range_error_high(self):
        url = reverse('api:get_calendar_month', kwargs={
            'cal': 'julian',
            'year': 4100,
            'month': 12,
        })
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, 404)

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

    def test_oembed_calendar(self):
        """The oEmbed endpoint should return a response with a status of 200."""

        # We need this to build an absolute url
        request = RequestFactory().get('/')

        calendar_path = reverse('calendar', kwargs={
            'cal': 'gregorian',
            'year': 2023,
            'month': 1,
        })
        calendar_url = request.build_absolute_uri(calendar_path)

        url = reverse('api:get_calendar_embed')

        response = self.client.get(url, {'url': calendar_url}, format='json')
        self.assertEqual(response.status_code, 200)


class MonthCacheTestCase(TestCase):
    """api._get_calendar_month caches each month's response."""

    fixtures = ['calendarium.json', 'commemorations.json']

    def setUp(self):
        cache.clear()

    def _get(self, **kwargs):
        url = reverse('api:get_calendar_month', kwargs={'cal': 'gregorian', 'year': 2022, 'month': 1, **kwargs})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_cached_response_matches_the_golden_file(self):
        with open(BASE_DIR / 'data/january.json') as f:
            expected = json.loads(f.read())

        self.assertEqual(expected, self._get())  # computed
        self.assertEqual(expected, self._get())  # from the cache

    def test_cache_hit_skips_computation(self):
        self._get()

        with mock.patch.object(api.liturgics, 'month_of_days', side_effect=AssertionError('recomputed')):
            self._get()

    def test_months_are_cached_separately(self):
        january = self._get()
        julian_january = self._get(cal='julian')

        self.assertNotEqual(january, julian_january)
        self.assertEqual(julian_january, self._get(cal='julian'))


class DayCacheTestCase(TestCase):
    """api._get_calendar_day caches each day's response."""

    fixtures = ['calendarium.json', 'commemorations.json']

    def setUp(self):
        api.day_cache.clear()

    def _get(self, cal='gregorian', year=2022, month=1, day=7, tradition=None, **params):
        kwargs = {'cal': cal, 'year': year, 'month': month, 'day': day}
        name = 'api:get_calendar_day'
        if tradition:
            kwargs['tradition'] = tradition
            name = 'api:get_calendar_day_tradition'
        response = self.client.get(reverse(name, kwargs=kwargs), params, format='json')
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_cached_response_matches_the_computed_one(self):
        computed = self._get()
        self.assertEqual('Synaxis of St John the Baptist', computed['summary_title'])
        self.assertTrue(computed['readings'][0]['passage'])
        self.assertEqual(computed, self._get())

    def test_cache_hit_skips_computation(self):
        self._get()

        with mock.patch.object(api.liturgics, 'Day', side_effect=AssertionError('recomputed')):
            self._get()

    def test_days_are_cached_separately(self):
        self.assertEqual((1, 7), (self._get()['month'], self._get()['day']))
        self.assertEqual((1, 8), (self._get(day=8)['month'], self._get(day=8)['day']))
        self.assertEqual((12, 25), (self._get(cal='julian')['month'], self._get(cal='julian')['day']))

        # Tradition and translation can leave a day's content unchanged, so
        # check that they get entries of their own.
        self._get(tradition='greek')
        self._get(translation='lxx2012-web')
        self.assertEqual(5, len(api.day_cache._list_cache_files()))

    def test_invalid_date_is_still_a_404(self):
        url = reverse('api:get_calendar_day', kwargs={'cal': 'gregorian', 'year': 2022, 'month': 2, 'day': 30})
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.get(url).status_code, 404)


class TrailingSlashTestCase(TestCase):
    """orthocal.middleware.append_api_slash and the APPEND_SLASH redirect"""

    fixtures = ['calendarium.json', 'commemorations.json']

    def test_slashless_api_url_is_served_directly(self):
        url = reverse('api:get_calendar_day', kwargs={'cal': 'gregorian', 'year': 2022, 'month': 1, 'day': 7})
        slashless = self.client.get(url.rstrip('/'))

        self.assertEqual(slashless.status_code, 200)
        self.assertEqual(slashless.json(), self.client.get(url).json())

    def test_unknown_slashless_api_url_is_still_a_404(self):
        self.assertEqual(self.client.get('/api/no/such/thing').status_code, 404)

    def test_slashless_page_url_redirects_cacheably(self):
        url = reverse('readings', kwargs={'tradition': 'slavic', 'cal': 'gregorian', 'year': 2022, 'month': 1, 'day': 7})
        response = self.client.get(url.rstrip('/'))

        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], url)
        self.assertIn('public', response['Cache-Control'])
        self.assertIn('s-maxage', response['Cache-Control'])


class RecordWorkerTestCase(TestCase):
    """orthocal.middleware.record_worker"""

    fixtures = ['calendarium.json', 'commemorations.json']

    def test_transaction_is_tagged_with_the_worker(self):
        url = reverse('api:get_calendar_day', kwargs={'cal': 'gregorian', 'year': 2022, 'month': 1, 'day': 7})

        with mock.patch('newrelic.agent.add_custom_attribute') as add_custom_attribute:
            self.client.get(url)

        attributes = dict(c.args for c in add_custom_attribute.call_args_list)
        self.assertEqual(os.getpid(), attributes['worker.pid'])
        self.assertIn('worker.instance', attributes)
