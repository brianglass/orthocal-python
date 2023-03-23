from datetime import date

from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone
from http.cookies import SimpleCookie

from ..views import render_calendar_html
from ..datetools import Calendar


class TestReadingsView(TestCase):
    fixtures = ['calendarium.json', 'commemorations.json']

    # reset cookies after each test
    def tearDown(self):
        self.client.cookies = SimpleCookie()

    def test_gregorian_default(self):
        now = timezone.localtime()
        url = reverse('index')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['date'], now.date())
        self.assertEqual(response.context['cal'], Calendar.Gregorian)

    def test_julian_default(self):
        now = timezone.localtime()
        url = reverse('index')
        self.client.cookies = SimpleCookie({'__session': 'julian'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['date'], now.date())
        self.assertEqual(response.context['cal'], Calendar.Julian)

class TestCalendarView(TestCase):
    fixtures = ['calendarium.json', 'commemorations.json']

    # reset cookies after each test
    def tearDown(self):
        self.client.cookies = SimpleCookie()

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
        now = timezone.localtime()
        this_month = date(now.year, now.month, 1)
        url = reverse('calendar-default')
        self.client.cookies = SimpleCookie({'__session': 'julian'})
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
        self.assertIn('Circumcision of Our Lord', html)

    async def test_render_calendar_html_julian(self):
        now = date(2022, 1, 7)
        request = RequestFactory().get('/')
        html = await render_calendar_html(request, 2022, 1, cal=Calendar.Julian)
        self.assertIn(now.strftime('%B'), html)
        self.assertIn('Nativity of Christ', html)
