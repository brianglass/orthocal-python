from datetime import date

from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone
from http.cookies import SimpleCookie

from ..views import render_calendar_html
from ..datetools import Calendar


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
