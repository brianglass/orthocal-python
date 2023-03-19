import zoneinfo

from datetime import date, datetime, timedelta

import icalendar

from dateutil.rrule import rrule, DAILY
from django.conf import settings
from django.http import HttpResponse
from django.urls import reverse
from django.utils import timezone

from . import liturgics


async def ical(request, cal):
    title = cal.title()
    ttl = settings.ORTHOCAL_ICAL_TTL
    timestamp = timezone.localtime()

    use_julian = True if cal == 'julian' else False

    calendar = icalendar.Calendar()
    calendar.add('prodid', '-//brianglass//Orthocal//en')
    calendar.add('version', '2.0')
    calendar.add('name', f'Orthodox Feasts and Fasts ({title})')
    calendar.add('x-wr-calname', f'Orthodox Feasts and Fasts ({title})')
    calendar.add('refresh-interval;value=duration', f'PT{ttl}H')
    calendar.add('x-published-ttl', f'PT{ttl}H')
    calendar.add('timezone-id', settings.ORTHOCAL_ICAL_TZ)
    calendar.add('x-wr-timezone', settings.ORTHOCAL_ICAL_TZ)

    start_dt = timestamp.date() - timedelta(days=30)
    end_dt = start_dt + timedelta(days=30 * 7)

    for dt in rrule(DAILY, dtstart=start_dt, until=end_dt):
        day = liturgics.Day(dt.year, dt.month, dt.day, use_julian=use_julian)
        await day.ainitialize()

        day_path = reverse('readings', kwargs={
            'cal': cal,
            'year': day.gregorian_date.year,
            'month': day.gregorian_date.month,
            'day': day.gregorian_date.day
        })
        url = request.build_absolute_uri(day_path)
        uid = f'{dt.strftime("%Y-%m-%d")}.{title}@orthocal.info'

        event = icalendar.Event()
        event.add('uid', uid)
        event.add('dtstamp', timestamp)
        event.add('dtstart', icalendar.vDate(dt))  # We use vDate to make an all-day event
        event.add('summary', day.summary_title)
        event.add('description', await ical_description(day, url))
        event.add('url', url)
        event.add('class', 'public')
        calendar.add_component(event)

    return HttpResponse(calendar.to_ical(), content_type='text/calendar')

async def ical_description(day, url):
    description = ''

    if day.fast_exception_desc and day.fast_level:
        description += f'{day.fast_level_desc} \u2013 {day.fast_exception_desc}\n\n'
    else:
        description += f'{day.fast_level_desc}\n\n'

    if day.feasts:
        description += ' \u2022 '.join(day.feasts) + '\n\n'

    if day.saints:
        description += ' \u2022 '.join(day.saints) + '\n\n'

    for reading in await day.aget_readings():
        if reading.desc:
            description += f'{reading.pericope.display} ({reading.source}, {reading.desc})\n'
        else:
            description += f'{reading.pericope.display} ({reading.source})\n'

    # HTML links seem to actually work in Google Calendar, but not ical, so we
    # just leave the link raw.
    description += f'\nFollow this link for full readings:\n{url}'

    return description
