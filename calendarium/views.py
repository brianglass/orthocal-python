import calendar
import csv
import logging

from datetime import date, timedelta

from dateutil.relativedelta import relativedelta
from django.http import Http404, HttpResponse
from django.template.loader import render_to_string
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from orthocal.converters import CalendarConverter
from . import liturgics, models

logger = logging.getLogger(__name__)
cal_converter = CalendarConverter()


async def readings_view(request, cal=None, year=None, month=None, day=None):
    now = timezone.localtime()

    if not cal:
        converter = CalendarConverter()
        slug = request.COOKIES.get('__session', 'gregorian')
        cal = converter.to_python(slug)

    use_julian = cal == 'julian'

    if year and month and day:
        try:
            dt = date(year, month, day)
        except ValueError:
            raise Http404

        day = liturgics.Day(year, month, day, use_julian=use_julian)
    else:
        dt = now
        day = liturgics.Day(dt.year, dt.month, dt.day, use_julian=use_julian)

    await day.ainitialize()
    await day.aget_readings(fetch_content=True)

    context = {
            'day': day,
            'date': dt,
            'now': now,
            'next_date': dt + timedelta(days=1),
            'previous_date': dt - timedelta(days=1),
            'cal': cal,
    }

    return render(request, 'readings.html', context=context)

async def calendar_view(request, cal=None, year=None, month=None):
    if not cal:
        slug = request.COOKIES.get('__session', 'gregorian')
        cal = cal_converter.to_python(slug)

    if not year or not month:
        now = timezone.localtime()
        year, month = now.year, now.month

    first_day = date(year, month, 1)

    content = await render_calendar_html(request, year, month, use_julian=cal=='julian')

    return render(request, 'calendar.html', context={
        'content': content,
        'cal': cal,
        'this_month': first_day,
        'previous_month': first_day - relativedelta(months=1),
        'next_month': first_day + relativedelta(months=1),
    })

async def calendar_embed_view(request, cal=None, year=None, month=None):
    if not cal:
        slug = request.COOKIES.get('__session', 'gregorian')
        cal = cal_converter.to_python(slug)

    if not year or not month:
        now = timezone.localtime()
        year, month = now.year, now.month

    first_day = date(year, month, 1)

    content = await render_calendar_html(request, year, month, use_julian=cal=='julian')

    return render(request, 'calendar_embed.html', context={
        'content': content,
        'cal': cal,
        'this_month': first_day,
        'previous_month': first_day - relativedelta(months=1),
        'next_month': first_day + relativedelta(months=1),
    })

async def lectionary(request):
    response = HttpResponse(
        content_type='text/csv',
        headers={'Content-Disposition': 'attachment; filename="lectionary.csv"'},
    )
    sources = models.Reading.objects.filter(pdist__lt=700).values_list('source', flat=True).distinct()

    fieldnames = ['Pascha Distance', 'Day Name'] + [s async for s in sources]
    writer = csv.DictWriter(response, fieldnames=fieldnames)
    writer.writeheader()

    queryset = models.Reading.objects.filter(pdist__lt=700).select_related('pericope')
    async for r in queryset.order_by('pdist', 'ordering'):
        writer.writerow({
            'Pascha Distance': r.pdist,
            'Day Name': r.day_name,
            r.source: r.pericope.display
        })

    return response

async def render_calendar_html(request, year, month, use_julian=False, full_urls=False):
    class LiturgicalCalendar(calendar.HTMLCalendar):
        def formatday(self, day, weekday):
            if not day:
                return super().formatday(day, weekday)

            return render_to_string('calendar_day.html', request=request, context={
                'cal': 'julian' if use_julian else 'gregorian',
                'day_number': day,
                'day': days[day-1],  # days is 0-origin and day is 1-origin
                'cell_class': self.cssclasses[weekday],
                'full_urls': full_urls,
            })

    day_generator = liturgics.amonth_of_days(year, month, use_julian=use_julian)

    # d.day is the Julian day if use_julian is True. We can't use that since
    # we're rendering as a Gregorian calendar. So instead of a dict with d.day
    # as key, we just index into a list by sequence.
    days = [d async for d in day_generator]

    lcal = LiturgicalCalendar(firstweekday=6)
    content = lcal.formatmonth(year, month)

    return content
