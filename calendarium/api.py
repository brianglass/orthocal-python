import logging

from datetime import date
from typing import List

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404, HttpResponse
from django.template.loader import render_to_string
from django.urls import resolve, reverse
from django.urls.exceptions import Resolver404
from django.utils import timezone
from django.utils.translation import get_language_from_request
from ninja import Field, NinjaAPI, Redoc, Schema
from ninja.decorators import decorate_view
from ninja.renderers import JSONRenderer
from ninja.responses import NinjaJSONEncoder
from ninja.throttling import AnonRateThrottle
from pydantic import AnyUrl, AnyHttpUrl, conint, constr, validator

from . import datetools, liturgics, views
from .datetools import Calendar, Tradition, Translation
from orthocal.decorators import etag, etag_date, instrument_endpoint

logger = logging.getLogger(__name__)

BURST_RATE = settings.ORTHOCAL_API_RATELIMIT

class ClientIpMixin:
    """
    ninja's own get_ident() only extracts a single client IP out of
    X-Forwarded-For when NINJA_NUM_PROXIES is set; left unset (as it is
    here), it falls back to keying on the *entire* raw XFF string. Cloud
    Run's front end puts the real client IP first in that header and
    appends its own hop(s) after it, and those appended hops aren't
    guaranteed to stay the same across requests from the same client --
    so the unpatched behavior can fragment one client's requests across
    many different throttle-cache keys instead of accumulating against a
    single one, undercounting how often the real limit is actually hit.
    """
    def get_ident(self, request):
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            return xff.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

class ShadowAnonRateThrottle(ClientIpMixin, AnonRateThrottle):
    """
    Runs the real per-IP rate check and logs what WOULD be throttled, but
    always allows the request through -- no client sees a 429 yet. This is
    a deliberate rollout step: BURST_RATE was defined but never wired up to
    anything, so there's no data on how real (including third-party, non-
    browser) traffic would be affected by actually enforcing it. Watch the
    logs this produces for a while, then swap this for a plain
    ClientIpMixin + AnonRateThrottle combo (same rate, same identity-by-IP
    behavior, minus the shadow logging) once it looks safe.
    """
    def allow_request(self, request):
        allowed = super().allow_request(request)
        if not allowed:
            logger.warning(
                'Would rate-limit (shadow mode, not enforced): ip=%s path=%s ua=%s',
                self.get_ident(request),
                request.path,
                request.META.get('HTTP_USER_AGENT', ''),
            )
        return True

class Encoder(NinjaJSONEncoder):
    def default(self, o):
        if isinstance(o, AnyUrl):
            return str(o)

        return super().default(o)


class Renderer(JSONRenderer):
    encoder_class = Encoder
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
    docs=Redoc(),
    title='Orthocal API',
    version='1.2',
    docs_url='/docs/',
    description=(
        'Orthocal.info provides an API for looking up information about '
        'days and months in the Orthodox Calendar, including the ability '
        'to look up the scripture readings and lives of the saints for a given day.'
        'The API follow OCA rubrics.'
    ),
    servers=[
        {'url': settings.ORTHOCAL_PUBLIC_URL, 'description': 'Public API'},
    ],
    throttle=[ShadowAnonRateThrottle(BURST_RATE)],
)


year = conint(ge=1583, le=4099)
month = conint(ge=1, le=12)
day = conint(ge=1, le=31)


class VerseSchema(Schema):
    book: str = Field(..., description='The abbreviated book of the Bible.')
    chapter: int
    verse: int
    content: str
    paragraph_start: bool = Field(..., description='Whether this verse is the start of a paragraph.')


class ReadingSchemaLite(Schema):
    source: str = Field(..., description='Which service the passage is read during (e.g. Vespers).')
    book: str = Field(..., alias='pericope.book', description='The liturgical book the reading comes from (e.g. Apostol).')
    description: str = Field(..., alias='desc')
    display: str = Field(..., alias='pericope.display', description='The scripture reference.')
    short_display: str = Field(..., alias='pericope.sdisplay', description='The scripture reference with abbreviated book name.')
    passage: None = Field(None, alias='None')


class ReadingSchema(ReadingSchemaLite):
    passage: List[VerseSchema] = Field(None, alias='pericope.passage')


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

    titles: List[str]
    summary_title: str = Field(..., description='Chooses the best option from titles, feasts, or saints to provide a succinct title for the day.')

    feast_level: conint(ge=-1, le=8) = Field(..., description='Best to use feast_level_description instead.')
    feast_level_description: str = Field(..., alias='feast_level_desc')
    feasts: List[str]

    fast_level: datetools.FastLevels
    fast_level_desc: str = Field(..., description='Best combined with fast_exception_desc')
    fast_exception: int
    fast_exception_desc: str
    fast_abstentions: List[str] = Field(
        ...,
        description=(
            "Food categories to abstain from on this day, e.g. ['meat', 'fish', 'dairy', 'eggs']. "
            "Derived from fast_level and fast_exception; empty on non-fasting days. A simpler "
            "alternative to fast_exception_desc's traditional 'X is allowed' phrasing for readers "
            "unfamiliar with it. Reflects typikon-strict practice -- consult your parish for any "
            "pastorally-relaxed local exceptions."
        ),
    )

    saints: List[str]
    service_notes: List[str]

    abbreviated_reading_indices: List[int] = Field(
        ...,
        description=(
            'This list of indices into the list of readings provides an abbreviated '
            'path through the readings. This usually includes just the Gospel and Epistle '
            'readings from the liturgy, or, during Lent, three readings from the Old Testament.'
        )
    )
    readings: List[ReadingSchemaLite]

    @validator('titles', 'feasts', 'saints', 'service_notes')
    def list_or_null(cls, value):
        """Force empty list to be None for backward compatibility."""
        return value or None


class DaySchema(DaySchemaLite):
    stories: List[StorySchema]
    readings: List[ReadingSchema]


class OembedSchema(Schema):
    type: str
    version: str
    title: str = None
    author_name: str = None
    author_url: AnyHttpUrl = None
    provider_name: str = None
    provider_url: str = None
    cache_age: int = None
    thumbnail_url: AnyHttpUrl = None
    thumbnail_width: int = None
    thumbnail_height: int = None
    width: int
    height: int
    url: AnyHttpUrl
    html: str


@api.exception_handler(NotImplementedError)
def not_implemented_handler(request, exc):
    return api.create_response(request, {'message': 'Not Implemented'}, status=501)

async def _get_calendar_day(request, cal, tradition, year, month, day, translation=None):
    try:
        day = liturgics.Day(year, month, day, calendar=cal, tradition=tradition, language=request.LANGUAGE_CODE, translation=translation)
    except ValueError:
        # The date is out of range or invalid
        raise Http404

    await day.ainitialize()
    await day.aget_readings(fetch_content=True)
    await day.aget_abbreviated_readings()

    return day

@api.get('{cal:cal}/{year:year}/{month:month}/{day:day}/', response=DaySchema)
@instrument_endpoint
@decorate_view(etag)
async def get_calendar_day(request, cal: Calendar, year: year, month: month, day: day, translation: Translation = None):
    """Get information about the liturgical day for the given calendar and date.
    The *cal* path parameter should be `gregorian` or `julian`. The legacy `oca` or `rocor`
    will still work, but should be avoided for new code. This serves the Slavic/OCA
    tradition; see the `{tradition}/{cal}/...` routes below for the Greek tradition.
    The optional *translation* query parameter selects the Bible translation
    (`kjv` or `lxx2012-web`); it only affects English content and defaults to
    `kjv` when omitted.
    """

    return await _get_calendar_day(request, cal, Tradition.Slavic, year, month, day, translation)

@api.get('{tradition:tradition}/{cal:cal}/{year:year}/{month:month}/{day:day}/', response=DaySchema)
@instrument_endpoint
@decorate_view(etag)
async def get_calendar_day_tradition(request, tradition: Tradition, cal: Calendar, year: year, month: month, day: day, translation: Translation = None):
    """Get information about the liturgical day for the given tradition, calendar, and date.
    The *tradition* path parameter should be `slavic` or `greek`. The legacy `oca`,
    `antiochian`, and `goa` will still work, but should be avoided for new code.
    The *cal* path parameter should be `gregorian` or `julian`.
    The optional *translation* query parameter selects the Bible translation
    (`kjv` or `lxx2012-web`); it only affects English content and defaults to
    `kjv` when omitted.
    """

    return await _get_calendar_day(request, cal, tradition, year, month, day, translation)

async def _get_calendar_month(request, cal, tradition, year, month) -> List[DaySchemaLite]:
    days = [d async for d in liturgics.amonth_of_days(year, month, calendar=cal, tradition=tradition)]
    for day in days:
        await day.aget_readings()
        await day.aget_abbreviated_readings()

    return days

@api.get('{cal:cal}/{year:year}/{month:month}/', response=List[DaySchemaLite])
@instrument_endpoint
@decorate_view(etag)
async def get_calendar_month(request, cal: Calendar, year: year, month: month) -> List[DaySchemaLite]:
    """Get information about all the liturgical days for the given calendar and month.
    This endpoint excludes the readings and stories in order to avoid returning
    a response that is too large.

    The *cal* path parameter should be `gregorian` or `julian`. The legacy `oca` or `rocor`
    will still work, but should be avoided for new code. This serves the Slavic/OCA
    tradition; see the `{tradition}/{cal}/...` routes below for the Greek tradition.
    """

    return await _get_calendar_month(request, cal, Tradition.Slavic, year, month)

@api.get('{tradition:tradition}/{cal:cal}/{year:year}/{month:month}/', response=List[DaySchemaLite])
@instrument_endpoint
@decorate_view(etag)
async def get_calendar_month_tradition(request, tradition: Tradition, cal: Calendar, year: year, month: month) -> List[DaySchemaLite]:
    """Get information about all the liturgical days for the given tradition, calendar, and month.
    This endpoint excludes the readings and stories in order to avoid returning
    a response that is too large.

    The *tradition* path parameter should be `slavic` or `greek`. The *cal* path
    parameter should be `gregorian` or `julian`.
    """

    return await _get_calendar_month(request, cal, tradition, year, month)

@api.get('{cal:cal}/', response=DaySchema, summary='Get Today')
@instrument_endpoint
@decorate_view(etag_date)
async def get_calendar_default(request, cal: Calendar, translation: Translation = None):
    """Get information about the current liturgical day for the given calendar.
    The timezone is Pacific Time. The *cal* path parameter should be
    `gregorian` or `julian`. The legacy `oca` or `rocor` will still work, but
    should be avoided for new code. This serves the Slavic/OCA tradition; see
    the `{tradition}/{cal}/` route below for the Greek tradition.
    The optional *translation* query parameter selects the Bible translation
    (`kjv` or `lxx2012-web`); it only affects English content and defaults to
    `kjv` when omitted.
    """
    dt = timezone.localtime()
    return await _get_calendar_day(request, cal, Tradition.Slavic, dt.year, dt.month, dt.day, translation)

@api.get('{tradition:tradition}/{cal:cal}/', response=DaySchema, summary='Get Today (by tradition)')
@instrument_endpoint
@decorate_view(etag_date)
async def get_calendar_default_tradition(request, tradition: Tradition, cal: Calendar, translation: Translation = None):
    """Get information about the current liturgical day for the given tradition and calendar.
    The timezone is Pacific Time. The *tradition* path parameter should be
    `slavic` or `greek`. The *cal* path parameter should be `gregorian` or `julian`.
    The optional *translation* query parameter selects the Bible translation
    (`kjv` or `lxx2012-web`); it only affects English content and defaults to
    `kjv` when omitted.
    """
    dt = timezone.localtime()
    return await _get_calendar_day(request, cal, tradition, dt.year, dt.month, dt.day, translation)

@api.get('oembed/calendar/', response=OembedSchema, exclude_none=True)
@instrument_endpoint
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
    calendar = kwargs.get('cal', Calendar.Gregorian)
    tradition = kwargs.get('tradition', Tradition.Slavic)

    if 'year' not in kwargs or 'month' not in kwargs:
        now = timezone.localtime()
        year, month = now.year, now.month
    else:
        year, month = kwargs['year'], kwargs['month']

    content = await views.render_calendar_html(request, year, month, cal=calendar, tradition=tradition, full_urls=True)
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
