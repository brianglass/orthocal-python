import zoneinfo

from datetime import date, datetime, timedelta
from urllib.parse import urljoin

import icalendar

from dateutil.rrule import rrule, DAILY
from django.conf import settings
from django.http import HttpResponse, Http404
from django.urls import reverse
from rest_framework import viewsets
from rest_framework.response import Response

from . import liturgics
from . import serializers


class DayViewSet(viewsets.ViewSet):
    def retrieve(self, request, year, month, day, jurisdiction='oca'):
        if jurisdiction == 'oca':
            day = liturgics.Day(year, month, day)
        else:
            day = liturgics.Day(year, month, day, use_julian=True)

        day.initialize()
        serializer = serializers.DaySerializer(day)
        return Response(serializer.data)

    def list(self, request, year, month, jurisdiction='oca'):
        if jurisdiction == 'oca':
            days = liturgics.month_of_days(year, month)
        else:
            days = liturgics.month_of_days(year, month, use_julian=True)

        # Exclude the scriptures passages for the list view to keep the response times low.
        serializer = serializers.DaySerializer(days, many=True, context={'exclude_passage': True})
        return Response(serializer.data)


async def ical(request, jurisdiction):
    base_url = request.build_absolute_uri('/')
    title = jurisdiction.upper()
    ttl = settings.ORTHOCAL_ICAL_TTL
    timestamp = datetime.now()

    calendar = icalendar.Calendar()
    calendar.add('prodid', '-//brianglass//Orthocal//en')
    calendar.add('version', '2.0')
    calendar.add('name', f'Orthodox Feasts and Fasts ({title})')
    calendar.add('x-wr-calname', f'Orthodox Feasts and Fasts ({title})')
    calendar.add('refresh-interval;value=duration', f'PT{ttl}H')
    calendar.add('x-published-ttl', f'PT{ttl}H')
    calendar.add('timezone-id', settings.ORTHOCAL_ICAL_TZ)
    calendar.add('x-wr-timezone', settings.ORTHOCAL_ICAL_TZ)

    start_dt = date.today() - timedelta(days=30)
    end_dt = start_dt + timedelta(days=30 * 7)

    for dt in rrule(DAILY, dtstart=start_dt, until=end_dt):
        day = liturgics.Day(dt.year, dt.month, dt.day)
        await day.ainitialize()

        uid = f'{dt.strftime("%Y-%m-%d")}.{title}@orthocal.info'
        day_path = reverse('calendar', kwargs={
            'jurisdiction': jurisdiction,
            'year': day.year,
            'month': day.month,
            'day': day.day
        })

        event = icalendar.Event()
        event.add('uid', uid)
        event.add('dtstamp', timestamp)
        event.add('dtstart', dt)
        event.add('summary', '; '.join(day.titles))
        event.add('description', await ical_description(day))
        event.add('url', urljoin(base_url, day_path))
        event.add('class', 'public')
        calendar.add_component(event)

    return HttpResponse(calendar.to_ical(), content_type='text/calendar')

async def ical_description(day):
    description = ''

    if day.feasts:
        description += '; '.join(day.feasts) + '\n\n'

    if day.saints:
        description += '; '.join(day.saints) + '\n\n'

    if day.fast_exception_desc and day.fast_level:
        description += f'{day.fast_level_desc} \u2013 {day.fast_exception_desc}\n\n'
    else:
        description += f'{day.fast_level_desc}\n\n'

    for reading in await day.aget_readings():
        if reading.desc:
            description += f'{reading.display} ({reading.source}, {reading.desc})\n'
        else:
            description += f'{reading.display} ({reading.source})\n'

    return description
