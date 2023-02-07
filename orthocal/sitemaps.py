from datetime import timedelta

from django.contrib import sitemaps
from django.urls import reverse
from django.utils import timezone

from dateutil.relativedelta import relativedelta
from dateutil.rrule import rrule, DAILY, MONTHLY


class StaticViewSitemap(sitemaps.Sitemap):
    priority = 1.0

    def items(self):
        return ['index', 'alexa', 'api', 'feeds', 'about']

    def location(self, item):
        return reverse(item)

    def changefreq(self, item):
        return 'daily' if item == 'index' else 'monthly'


class CalendarSitemap(sitemaps.Sitemap):
    priority = 0.50
    changefreq = 'monthly'

    def items(self):
        timestamp = timezone.localtime().replace(day=1)
        start_dt = timestamp.date() - relativedelta(months=12)
        end_dt = start_dt + relativedelta(months=24)
        return rrule(MONTHLY, dtstart=start_dt, until=end_dt)

    def location(self, item):
        return reverse('calendar', kwargs={'year': item.year, 'month': item.month, 'cal': 'gregorian',})


class CalendarJulianSitemap(CalendarSitemap):
    def location(self, item):
        return reverse('calendar', kwargs={'year': item.year, 'month': item.month, 'cal': 'julian',})


class ReadingsSitemap(sitemaps.Sitemap):
    priority = 0.75
    changefreq = 'monthly'

    def items(self):
        timestamp = timezone.localtime().replace(day=1)
        start_dt = timestamp.date() - timedelta(days=365)
        end_dt = start_dt + timedelta(days=365*2)
        return rrule(DAILY, dtstart=start_dt, until=end_dt)

    def location(self, item):
        return reverse('readings', kwargs={'year': item.year, 'month': item.month, 'day': item.day, 'cal': 'gregorian',})


class ReadingsJulianSitemap(ReadingsSitemap):
    def location(self, item):
        return reverse('readings', kwargs={'year': item.year, 'month': item.month, 'day': item.day, 'cal': 'julian',})
