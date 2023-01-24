import logging

from datetime import date

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404, HttpResponse
from django.template.loader import render_to_string
from django.urls import resolve, reverse
from django.urls.exceptions import Resolver404
from django.utils import timezone
from ninja import Field, NinjaAPI, Schema
from ninja.renderers import JSONRenderer
from pydantic import AnyHttpUrl, validator

from . import liturgics, views

logger = logging.getLogger(__name__)

# We want the JSON in the api to be human readable.
JSONRenderer.json_dumps_params['indent'] = 4

api = NinjaAPI(urls_namespace='api')


@api.exception_handler(NotImplementedError)
def not_implemented_handler(request, exc):
    return api.create_response(request, {'message': 'Not Implemented'}, status=501)


class VerseSchema(Schema):
    book: str
    chapter: int
    verse: int
    content: str


class ReadingSchemaLite(Schema):
    source: str
    book: str
    description: str = Field(None, alias='desc')
    display: str
    short_display: str = Field(None, alias='sdisplay')
    passage: None = Field(None, alias='None')


class ReadingSchema(ReadingSchemaLite):
    passage: list[VerseSchema] = None


class StorySchema(Schema):
    title: str
    story: str


class DaySchemaLite(Schema):
    pascha_distance: int = Field(None, alias='pdist')
    julian_day_number: int = Field(None, alias='jdn')
    year: int
    month: int
    day: int
    weekday: int
    tone: int

    titles: list[str]

    feast_level: int
    feast_level_description: str = Field(None, alias='feast_level_desc')
    feasts: list[str]

    fast_level: int
    fast_level_desc: str
    fast_exception: int
    fast_exception_desc: str

    saints: list[str]
    service_notes: list[str]

    readings: list[ReadingSchemaLite] = None

    @validator('titles', 'feasts', 'saints', 'service_notes')
    def list_or_null(cls, value):
        """Force empty list to be None for backward compatibility."""
        return value or None


class DaySchema(DaySchemaLite):
    stories: list[StorySchema] = None
    readings: list[ReadingSchema] = None


class OembedSchema(Schema):
    type: str
    version: str
    title: str = None
    author_name: str = None
    author_url: str = None
    provider_name: str = None
    provider_url: str = None
    cache_age: int = None
    thumbnail_url: str = None
    thumbnail_width: int = None
    thumbnail_height: int = None
    width: int
    height: int
    url: str
    html: str


@api.get('/{cal:cal}/{year}/{month}/{day}/', response=DaySchema)
async def get_calendar_day(request, cal: str, year: int, month: int, day: int):
    # Easter date functions don't work correctly outside this range
    if not 1583 <= year <= 4099:
        raise Http404

    # Validate the date
    try:
        date(year, month, day)
    except ValueError:
        raise Http404

    day = liturgics.Day(year, month, day, use_julian=cal=='julian')
    await day.ainitialize()
    await day.aget_readings(fetch_content=True)

    return day

@api.get('/{cal:cal}/{year}/{month}/', response=list[DaySchemaLite])
async def get_calendar_month(request, cal: str, year: int, month: int):
    # Easter date functions don't work correctly outside this range
    if not 1583 <= year <= 4099:
        raise Http404

    days = [d async for d in liturgics.amonth_of_days(year, month, use_julian=cal=='julian')]
    for day in days:
        await day.aget_readings()

    return days

@api.get('/{cal:cal}/', response=DaySchema)
async def get_calendar_default(request, cal: str):
    dt = timezone.localtime()
    return await get_calendar_day(request, cal, dt.year, dt.month, dt.day)

@api.get('/oembed/calendar/', response=OembedSchema, exclude_none=True)
async def get_calendar_embed(request, url: AnyHttpUrl, maxwidth: int=800, maxheight: int=2000, format: str='json'):
    if format != 'json':
        raise NotImplementedError

    try:
        match = resolve(url.path)
    except Resolver404:
        raise Http404(url)

    if not match.url_name.startswith('calendar'):
        raise Http404(url)

    kwargs = match.kwargs
    use_julian = kwargs.get('cal', 'gregorian') == 'julian'

    if 'year' not in kwargs or 'month' not in kwargs:
        now = timezone.localtime()
        year, month = now.year, now.month
    else:
        year, month = kwargs['year'], kwargs['month']

    html = await views.render_calendar_html(year, month, use_julian=use_julian)

    return {
            'type': 'rich',
            'version': '1.0',
            'title': 'Orthodox Calendar',
            'provider_name': 'Orthocal.info',
            'provider_url': request.build_absolute_uri('/'),
            'width': maxwidth,
            'height': maxheight,
            'url': url,
            'html': html,
    }
