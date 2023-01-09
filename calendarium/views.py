import calendar

from datetime import date, timedelta

from dateutil.relativedelta import relativedelta
from django.http import Http404
from django.template.loader import render_to_string
from django.shortcuts import render
from django.utils import timezone

from . import liturgics


def readings(request, jurisdiction=None, year=None, month=None, day=None):
    now = timezone.localtime()

    if not jurisdiction:
        jurisdiction = request.COOKIES.get('jurisdiction', 'oca')

    use_julian = jurisdiction == 'rocor'

    if year and month and day:
        try:
            dt = date(year, month, day)
        except ValueError:
            raise Http404

        day = liturgics.Day(year, month, day, use_julian=use_julian)
    else:
        dt = now
        day = liturgics.Day(dt.year, dt.month, dt.day, use_julian=use_julian)

    day.initialize()

    context = {
            'day': day,
            'date': dt,
            'now': now,
            'next_date': dt + timedelta(days=1),
            'previous_date': dt - timedelta(days=1),
            'jurisdiction': jurisdiction,
    }

    return render(request, 'index.html', context=context)

async def calendar_view(request, jurisdiction=None, year=None, month=None):
    class LiturgicalCalendar(calendar.HTMLCalendar):
        def formatday(self, day, weekday):
            if not day:
                return super().formatday(day, weekday)

            return render_to_string('calendar_day.html', {
                'jurisdiction': jurisdiction,
                'day_number': day,
                'day': days[day-1],  # days is 0-origin and day is 1-origin
                'cell_class': self.cssclasses[weekday],
            })

    if not jurisdiction:
        jurisdiction = request.COOKIES.get('jurisdiction', 'oca')

    use_julian = jurisdiction == 'rocor'

    if not year or not month:
        now = timezone.localtime()
        year, month = now.year, now.month

    first_day = date(year, month, 1)

    day_generator = liturgics.amonth_of_days(year, month, use_julian=use_julian)

    # d.day is the Julian day if use_julian is True. We can't use that since
    # we're rendering as a Gregorian calendar. So instead of a dict with d.day
    # as key, we just index into a list by sequence.
    days = [d async for d in day_generator]

    cal = LiturgicalCalendar(firstweekday=6)
    content = cal.formatmonth(year, month)

    return render(request, 'calendar.html', context={
        'content': content,
        'jurisdiction': jurisdiction,
        'previous_month': first_day - relativedelta(months=1),
        'next_month': first_day + relativedelta(months=1),
    })
