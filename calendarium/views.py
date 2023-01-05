from datetime import date, timedelta

from django.http import Http404
from django.shortcuts import render

from . import liturgics


def readings(request, jurisdiction='oca', year=None, month=None, day=None):
    if jurisdiction not in ('oca', 'rocor'):
        raise Http404

    use_julian = jurisdiction == 'rocor'

    if year and month and day:
        dt = date(year, month, day)
        day = liturgics.Day(year, month, day, use_julian=use_julian)
    else:
        dt = date.today()
        day = liturgics.Day(dt.year, dt.month, dt.day, use_julian=use_julian)

    day.initialize()

    context = {
            'day': day,
            'date': dt,
            'now': date.today(),
            'next_date': dt + timedelta(days=1),
            'previous_date': dt - timedelta(days=1),
            'jurisdiction': jurisdiction,
    }

    return render(request, 'index.html', context=context)
