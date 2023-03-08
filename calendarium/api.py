import logging

from datetime import date

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404, HttpResponse
from django.template.loader import render_to_string
from django.urls import resolve, reverse
from django.urls.exceptions import Resolver404
from django.utils import timezone
from django.utils.translation import get_language_from_request
from ninja import Field, NinjaAPI, Schema
from ninja.renderers import JSONRenderer
from pydantic import AnyHttpUrl, conint, constr, validator

from . import datetools, liturgics, views
from orthocal.converters import CAL_RE

logger = logging.getLogger(__name__)

class Renderer(JSONRenderer):
    json_dumps_params = {
            'indent': 4,
            'ensure_ascii': False,
    }

class API(NinjaAPI):
    def get_openapi_operation_id(self, operation):
        return operation.view_func.__name__

api = API(
    urls_namespace='api',
    renderer=Renderer(),
    title='Orthocal API',
    version='1.1',
    docs_url='/docs/',
    description=(
        'Orthocal.info provides an API for looking up information about '
        'days and months in the Orthodox Calendar, including the ability '
        'to look up the scripture readings and lives of the saints for a given day.'
        'The API follow OCA rubrics.'
    ),
    servers=[
        {'url': settings.ORTHOCAL_PUBLIC_URL, 'description': 'Public API'},
    ]
)


calname = constr(regex=CAL_RE)
year = conint(ge=1583, le=4099)
month = conint(ge=1, le=12)
day = conint(ge=1, le=31)


class VerseSchema(Schema):
    book: str = Field(..., description='The book of the Bible. This is abbreviated.')
    chapter: int
    verse: int
    content: str


class ReadingSchemaLite(Schema):
    source: str
    book: str = Field(..., alias='pericope.book', description='The liturgical book the reading comes from (e.g. Apostol).')
    description: str = Field(..., alias='desc')
    display: str = Field(..., alias='pericope.display', description='The scripture reference.')
    short_display: str = Field(..., alias='pericope.sdisplay', description='The scripture reference with abbreviated book name.')
    passage: None = Field(None, alias='None')


class ReadingSchema(ReadingSchemaLite):
    passage: list[VerseSchema] = Field(None, alias='pericope.passage')


class StorySchema(Schema):
    title: str
    story: str = Field(..., description='HTML content of the story.')


class DaySchemaLite(Schema):
    pascha_distance: int = Field(..., alias='pdist')
    julian_day_number: int = Field(..., alias='jdn')
    # gregorian_date: date
    year: year
    month: month
    day: day
    weekday: datetools.Weekday
    tone: conint(ge=0, le=8)

    titles: list[str]
    summary_title: str = Field(..., description='Chooses the best option from titles, feasts, or saints to provide a succinct title for the day.')

    feast_level: conint(ge=-1, le=8) = Field(..., description='Best to use feast_level_description instead.')
    feast_level_description: str = Field(..., alias='feast_level_desc')
    feasts: list[str]

    fast_level: datetools.FastLevels
    fast_level_desc: str = Field(..., description='Best combined with fast_exception_desc')
    fast_exception: int
    fast_exception_desc: str

    saints: list[str]
    service_notes: list[str]

    abbreviated_reading_indices: list[int] = Field(
        ...,
        description=(
            'This list of indices into the list of readings provides an abbreviated '
            'path through the readings. This usually includes just the Gospel and Epistle '
            'readings from the liturgy, or, during Lent, three readings from the Old Testament.'
        )
    )
    readings: list[ReadingSchemaLite]

    @validator('titles', 'feasts', 'saints', 'service_notes')
    def list_or_null(cls, value):
        """Force empty list to be None for backward compatibility."""
        return value or None


class DaySchema(DaySchemaLite):
    stories: list[StorySchema]
    readings: list[ReadingSchema]


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
    url: AnyHttpUrl
    html: str


@api.exception_handler(NotImplementedError)
def not_implemented_handler(request, exc):
    return api.create_response(request, {'message': 'Not Implemented'}, status=501)

@api.get('/{cal:cal}/{year:year}/{month:month}/{day:day}/', response=DaySchema)
async def get_calendar_day(request, cal: calname, year: year, month: month, day: day):
    """Get information about the liturgical day for the given calendar and date.
    The *cal* path parameter should be `gregorian` or `julian`. The legacy `oca` or `rocor`
    will still work, but should be avoided for new code.
    """

    try:
        day = liturgics.Day(year, month, day, use_julian=cal=='julian', language=request.LANGUAGE_CODE)
    except ValueError:
        # The date is out of range or invalid
        raise Http404

    await day.ainitialize()
    await day.aget_readings(fetch_content=True)
    await day.aget_abbreviated_readings()

    return day

@api.get('/{cal:cal}/{year:year}/{month:month}/', response=list[DaySchemaLite])
async def get_calendar_month(request, cal: calname, year: year, month: month) -> list[DaySchemaLite]:
    """Get information about all the liturgical days for the given calendar and month.
    This endpoint excludes the readings and stories in order to avoid returning 
    a response that is too large.

    The *cal* path parameter should be `gregorian` or `julian`. The legacy `oca` or `rocor`
    will still work, but should be avoided for new code.
    """

    days = [d async for d in liturgics.amonth_of_days(year, month, use_julian=cal=='julian')]
    for day in days:
        await day.aget_readings()
        await day.aget_abbreviated_readings()

    return days

@api.get('/{cal:cal}/', response=DaySchema, summary='Get Today')
async def get_calendar_default(request, cal: calname):
    """Get information about the current liturgical day for the given calendar.
    The timezone is Pacific Time. The *cal* path parameter should be
    `gregorian` or `julian`. The legacy `oca` or `rocor` will still work, but
    should be avoided for new code.
    """
    dt = timezone.localtime()
    return await get_calendar_day(request, cal, dt.year, dt.month, dt.day)

@api.get('/oembed/calendar/', response=OembedSchema, exclude_none=True)
async def get_calendar_embed(request, url: AnyHttpUrl, maxwidth: int=800, maxheight: int=2000, format: str='json'):
    """Get an oEmbed response for the given calendar URL. This will return HTML
    code for a full month calendar that can be embedded in a website. The *url* parameter
    links to the desired calendar page on orthocal.info. The `year` and `month` path parameters
    can be omitted to get the current month. Only `json` is supported for the *format* parameter.

    Example: https://orthocal.info/calendar/gregorian/2023/3/

    See https://oembed.com/ for details on how to use oEmbed in your own site."""

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

    content = await views.render_calendar_html(request, year, month, use_julian=use_julian, full_urls=True)
    html = render_to_string('oembed_calendar.html', {'content': content})

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
