import logging
import zoneinfo

from datetime import date, datetime, timedelta

import icalendar

from dateutil.rrule import rrule, DAILY
from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import cache_control

from . import liturgics
from .datetools import Calendar, Tradition
from .liturgics.year import SlavicYear, GreekYear

logger = logging.getLogger(__name__)

_YEAR_CLASSES = {
    Tradition.Slavic: SlavicYear,
    Tradition.Greek: GreekYear,
}

# The four Great Fasts, in calendar-year order (Great Lent falls in
# spring, Nativity Fast in Nov/Dec) -- attribute name on the
# liturgics.year.ByzantineYear subclasses, paired with its display name.
_GREAT_FASTS = [
    ('great_lent', 'Great Lent'),
    ('apostles_fast', "Apostles' Fast"),
    ('dormition_fast', 'Dormition Fast'),
    ('nativity_fast', 'Nativity Fast'),
]

@cache_control(max_age=settings.ORTHOCAL_ICAL_TTL*60*60)
async def ical(request, cal=Calendar.Gregorian, tradition=Tradition.Slavic):
    key = f'ical-feed-{tradition}-{cal}'

    if not (serialized_calendar := await cache.aget(key)):
        timestamp = timezone.localtime()
        calendar = await generate_ical(timestamp, cal, tradition, request.build_absolute_uri)
        serialized_calendar = calendar.to_ical()
        await cache.aset(key, serialized_calendar, timeout=settings.ORTHOCAL_ICAL_TTL*60*60)

    return HttpResponse(serialized_calendar, content_type='text/calendar')

async def generate_ical(timestamp, cal, tradition, build_absolute_uri):
    # Slavic keeps its original title/uid format unchanged, since existing
    # subscribers' calendar apps use the uid to track/dedupe events -- only
    # the newer, non-default traditions get a distinguishing prefix.
    title = cal.title() if tradition == Tradition.Slavic else f'{tradition.title()} {cal.title()}'
    ttl = settings.ORTHOCAL_ICAL_TTL

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
        dt = dt.date()
        day = liturgics.Day(dt.year, dt.month, dt.day, calendar=cal, tradition=tradition)
        await day.ainitialize()

        day_path = reverse('readings', kwargs={
            'cal': cal,
            'tradition': tradition,
            'year': dt.year,
            'month': dt.month,
            'day': dt.day
        })
        url = build_absolute_uri(day_path)
        uid = f'{dt.strftime("%Y-%m-%d")}.{title}@orthocal.info'

        event = icalendar.Event()
        event.add('uid', uid)
        event.add('dtstamp', timestamp)
        event.add('dtstart', dt)
        event.add('dtend', dt + timedelta(days=1))
        event.add('summary', day.summary_title)
        event.add('description', await ical_description(day, url))
        event.add('url', url)
        event.add('class', 'public')
        calendar.add_component(event)

    year_class = _YEAR_CLASSES[tradition]
    for year in range(start_dt.year, end_dt.year + 1):
        pyear = year_class(year, cal)

        for attr, name in _GREAT_FASTS:
            fast_start, fast_end = getattr(pyear, attr)

            # In years with a sufficiently late Pascha, the Apostles' Fast
            # shrinks to nothing -- Peter and Paul falls before there would
            # even be a first day of the fast, giving an inverted range
            # (e.g. 2024: fast_start 7/1, fast_end 6/28). Nothing to add.
            if fast_start > fast_end:
                continue

            if fast_end < start_dt or fast_start > end_dt:
                continue

            fast_day_path = reverse('readings', kwargs={
                'cal': cal,
                'tradition': tradition,
                'year': fast_start.year,
                'month': fast_start.month,
                'day': fast_start.day,
            })
            fast_url = build_absolute_uri(fast_day_path)

            event = icalendar.Event()
            event.add('uid', f'{attr}-{fast_start.strftime("%Y-%m-%d")}.{title}@orthocal.info')
            event.add('dtstamp', timestamp)
            event.add('dtstart', fast_start)
            event.add('dtend', fast_end + timedelta(days=1))
            event.add('summary', name)
            event.add('description', f'The season of {name} begins today.\n\nFollow this link for full readings:\n{fast_url}')
            event.add('url', fast_url)
            event.add('class', 'public')
            calendar.add_component(event)

    return calendar

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
