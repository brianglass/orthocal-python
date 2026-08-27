from datetime import date

from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone
from http.cookies import SimpleCookie

from ..views import render_calendar_html
from ..datetools import Calendar, Translation


class TestReadingsView(TestCase):
    fixtures = ['calendarium.json', 'commemorations.json']

    def test_gregorian_default(self):
        now = timezone.localtime()
        url = reverse('index')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['date'], now.date())
        self.assertEqual(response.context['cal'], Calendar.Gregorian)

    def test_julian_default(self):
        """Pages should default to Julian after visiting a Julian page."""
        url = reverse('readings', kwargs={
            'cal': 'julian',
            'year': 2022,
            'month': 1,
            'day': 7,
        })
        response = self.client.get(url)

        now = timezone.localtime()
        url = reverse('index')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['date'], now.date())
        self.assertEqual(response.context['cal'], Calendar.Julian)

    def test_gregorian(self):
        url = reverse('readings', kwargs={
            'cal': 'gregorian',
            'year': 2022,
            'month': 1,
            'day': 7,
        })
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['date'].day, 7)
        self.assertEqual(response.context['date'].month, 1)
        self.assertEqual(response.context['cal'], Calendar.Gregorian)

    def test_gregorian_404(self):
        url = reverse('readings', kwargs={
            'cal': 'gregorian',
            'year': 2022,
            'month': 2,
            'day': 29,
        })
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_translation_default(self):
        """Pages should default to lxx2012-web after visiting an lxx2012-web page."""
        url = reverse('readings', kwargs={
            'tradition': 'slavic',
            'cal': 'gregorian',
            'translation': 'lxx2012-web',
            'year': 2022,
            'month': 1,
            'day': 7,
        })
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['translation'], Translation.LXX2012WEB)

        url = reverse('index')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['translation'], Translation.LXX2012WEB)

    def test_translation_dropdown_shown_for_english_only(self):
        """The translation dropdown only makes sense for English -- Romanian
        and Serbian each still have exactly one translation."""
        url = reverse('readings', kwargs={
            'cal': 'gregorian',
            'year': 2022,
            'month': 1,
            'day': 7,
        })

        response = self.client.get(url)
        self.assertContains(response, 'id="translation-select"')

        response = self.client.get(url, headers={'Accept-Language': 'ro'})
        self.assertNotContains(response, 'id="translation-select"')

    def test_greek_extra_sundays_overflow_does_not_500(self):
        """GreekYear.greek_extra_sundays can be 6 or 7 (roughly a quarter of
        all years -- e.g. the 2020 and 2023 cycles below), but
        _THEOPHANY_INTERPOLATION only has entries for 0-5. That left
        sunday_gospel_override returning None for every "extra Sunday" in
        those years, falling through to a Slavic-only branch in
        Day.gospel_pdist (self.pyear.reserves[i-1]) that always raises
        IndexError for Greek, since GreekYear.reserves is hardcoded to [].
        This produced a 500 on every affected Sunday."""

        dates = [
            (2021, 1, 24),  # 2020 cycle, greek_extra_sundays=6
            (2024, 1, 14),  # 2023 cycle, greek_extra_sundays=7
        ]

        for year, month, day in dates:
            url = reverse('readings', kwargs={
                'tradition': 'greek',
                'cal': 'gregorian',
                'year': year,
                'month': month,
                'day': day,
            })
            with self.subTest((year, month, day)):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)


class TestCalendarView(TestCase):
    fixtures = ['calendarium.json', 'commemorations.json']

    def test_gregorian_default(self):
        now = timezone.localtime()
        this_month = date(now.year, now.month, 1)
        url = reverse('calendar-default')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['this_month'], this_month)
        self.assertEqual(response.context['cal'], Calendar.Gregorian)
        self.assertEqual(response.context['day'].pyear.calendar, Calendar.Gregorian)

    def test_julian_default(self):
        """Pages should default to Julian after visiting a Julian page."""
        url = reverse('readings', kwargs={
            'cal': 'julian',
            'year': 2022,
            'month': 1,
            'day': 7,
        })
        response = self.client.get(f'{url}?foo')  # We send an argument to bypass caching

        now = timezone.localtime()
        this_month = date(now.year, now.month, 1)
        url = reverse('calendar-default')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['this_month'], this_month)
        self.assertEqual(response.context['cal'], Calendar.Julian)
        self.assertEqual(response.context['day'].pyear.calendar, Calendar.Julian)

    async def test_render_calendar_html(self):
        now = date(2022, 1, 7)
        request = RequestFactory().get('/')
        html = await render_calendar_html(request, 2022, 1, cal=Calendar.Gregorian)
        self.assertIn(now.strftime('%B'), html)
        self.assertIn('Synaxis 3 Hierarchs', html)

    async def test_render_calendar_html_julian(self):
        now = date(2022, 1, 7)
        request = RequestFactory().get('/')
        html = await render_calendar_html(request, 2022, 1, cal=Calendar.Julian)
        self.assertIn(now.strftime('%B'), html)
        self.assertIn('Nativity of Christ', html)


class TestAntiochianTraditionRouting(TestCase):
    """The `antiochian` URL segment now resolves to its own tradition.

    It previously aliased to Greek (see orthocal/converters.py), so this is a
    deliberate behaviour change for anyone already using those URLs -- they now
    get the Antiochian calendar rather than the Greek Archdiocese's, which is
    presumably what they wanted when they typed it.
    """

    fixtures = ['calendarium.json', 'commemorations.json']

    def test_readings_view_distinguishes_the_traditions(self):
        # 2021-01-19 is an annual-ordo date where the two jurisdictions differ.
        greek = self.client.get('/readings/greek/gregorian/2021/1/19/')
        antiochian = self.client.get('/readings/antiochian/gregorian/2021/1/19/')
        self.assertEqual(greek.status_code, 200)
        self.assertEqual(antiochian.status_code, 200)
        self.assertContains(greek, 'Matthew 22.1-14')
        self.assertContains(antiochian, 'Matthew 19.16-26')
        self.assertNotContains(antiochian, 'Matthew 22.1-14')

    def test_goa_alias_still_means_greek(self):
        goa = self.client.get('/readings/goa/gregorian/2021/1/19/')
        self.assertEqual(goa.status_code, 200)
        self.assertContains(goa, 'Matthew 22.1-14')

    def test_api_distinguishes_the_traditions(self):
        def gospels(tradition):
            response = self.client.get(f'/api/{tradition}/gregorian/2021/1/19/')
            self.assertEqual(response.status_code, 200)
            return [r['display'] for r in response.json()['readings'] if r['source'] == 'Gospel']

        self.assertEqual(gospels('greek'), ['Matthew 22.1-14'])
        self.assertEqual(gospels('antiochian'), ['Matthew 19.16-26'])

    def test_picker_offers_all_three_traditions(self):
        response = self.client.get('/readings/greek/gregorian/2021/1/19/')
        for label in ('>OCA<', '>GOA<', '>Antiochian<'):
            self.assertContains(response, label)
        # the selected one is the tradition actually being viewed
        self.assertContains(response, 'selected>GOA<')

    def test_every_legacy_url_segment_still_resolves(self):
        """Backward compatibility: no pre-existing segment may 404 or change shape.

        `antiochian` is the one whose *content* changed -- it used to alias
        `greek` and now selects the Antiochian calendar. Everything else,
        including the `oca` and `goa` aliases, is untouched.
        """
        for segment in ('slavic', 'oca', 'greek', 'goa', 'antiochian'):
            with self.subTest(segment=segment):
                page = self.client.get(f'/readings/{segment}/gregorian/2021/1/19/')
                self.assertEqual(page.status_code, 200)

                api = self.client.get(f'/api/{segment}/gregorian/2021/1/19/')
                self.assertEqual(api.status_code, 200)
                self.assertIn('readings', api.json())
                self.assertIn('pascha_distance', api.json())

        # the aliases still track their principals exactly
        self.assertEqual(
                self.client.get('/api/oca/gregorian/2021/1/19/').json(),
                self.client.get('/api/slavic/gregorian/2021/1/19/').json())
        self.assertEqual(
                self.client.get('/api/goa/gregorian/2021/1/19/').json(),
                self.client.get('/api/greek/gregorian/2021/1/19/').json())
