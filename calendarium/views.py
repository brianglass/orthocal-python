from datetime import date, timedelta

import icalendar

from django.http import Http404
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
