import calendar
import functools
import logging

from datetime import date, timedelta

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from . import liturgics, models
from .datetools import Calendar

logger = logging.getLogger(__name__)

async def readings_view(request, cal=None, year=None, month=None, day=None):
    cal = remember_cal(request, cal)

    if year and month and day:
        try:
            day = liturgics.Day(year, month, day, calendar=cal, language=request.LANGUAGE_CODE)
        except ValueError:
            raise Http404
    else:
        now = timezone.localtime()
        day = liturgics.Day(now.year, now.month, now.day, calendar=cal, language=request.LANGUAGE_CODE)

    await day.ainitialize()
    await day.aget_readings(fetch_content=True)

    return render(request, 'readings.html', context={
            'day': day,
            'date': day.gregorian_date,
            'next_date': day.gregorian_date + timedelta(days=1),
            'previous_date': day.gregorian_date - timedelta(days=1),
            'cal': cal,
    })

async def calendar_view(request, cal=None, year=None, month=None):
    cal = remember_cal(request, cal)

    if not year or not month:
        now = timezone.localtime()
        year, month = now.year, now.month

    first_day = date(year, month, 1)

    content = await render_calendar_html(request, year, month, cal=cal)

    return render(request, 'calendar.html', context={
        'content': content,
        'cal': cal,
        'this_month': first_day,
        'previous_month': first_day - relativedelta(months=1),
        'next_month': first_day + relativedelta(months=1),
    })

async def calendar_embed_view(request, cal=Calendar.Gregorian, year=None, month=None):
    if not year or not month:
        now = timezone.localtime()
        year, month = now.year, now.month

    first_day = date(year, month, 1)

    content = await render_calendar_html(request, year, month, cal=cal)

    return render(request, 'calendar_embed.html', context={
        'content': content,
        'cal': cal,
        'this_month': first_day,
        'previous_month': first_day - relativedelta(months=1),
        'next_month': first_day + relativedelta(months=1),
    })

async def render_calendar_html(request, year, month, cal=Calendar.Gregorian, full_urls=False):
    class LiturgicalCalendar(calendar.HTMLCalendar):
        def formatday(self, day, weekday):
            if not day:
                return super().formatday(day, weekday)

            return render_to_string('calendar_day.html', request=request, context={
                'cal': cal,
                'day_number': day,
                'day': days[day-1],  # days is 0-origin and day is 1-origin
                'cell_class': self.cssclasses[weekday],
                'full_urls': full_urls,
            })

    days = [
        d async for d in
        liturgics.amonth_of_days(year, month, calendar=cal)
    ]

    lcal = LiturgicalCalendar(firstweekday=6)
    content = lcal.formatmonth(year, month)

    return content

# Helper functions

def remember_cal(request, cal):
    if cal:
        if cal != request.session.get('cal', Calendar.Gregorian):
            request.session['cal'] = cal

        # Don't send vary on cookie header when we have an explicit cal.
        # In this case, the session does not actually impact the content.
        request.session.accessed = False
    else:
        cal = request.session.get('cal', Calendar.Gregorian)

    return cal
