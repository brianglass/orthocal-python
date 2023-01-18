import logging

from datetime import date

from django.http import Http404
from django.utils import timezone
from ninja import Field, NinjaAPI, Schema
from ninja.renderers import JSONRenderer
from pydantic import validator

from . import liturgics

logger = logging.getLogger(__name__)

# We want the JSON in the api to be human readable.
JSONRenderer.json_dumps_params['indent'] = 4

api = NinjaAPI(urls_namespace='api')


class VerseSchema(Schema):
    book: str
    chapter: int
    verse: int
    content: str


class ReadingSchema(Schema):
    source: str
    book: str
    description: str = Field(None, alias='desc')
    display: str
    short_display: str = Field(None, alias='sdisplay')
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

    readings: list[ReadingSchema] = None

    @validator('titles', 'feasts', 'saints', 'service_notes')
    def list_or_null(cls, value):
        """Force empty list to be None for backward compatibility."""
        return value or None


class DaySchema(DaySchemaLite):
    stories: list[StorySchema] = None


@api.get('/{cal:cal}/{year}/{month}/{day}/', response=DaySchema)
async def get_calendar_day(request, cal: str, year: int, month: int, day: int):
    # Easter date functions don't work correctly outside this range
    if not 1583 <= year <= 4099:
        raise Http404

    try:
        date(year, month, day)
    except ValueError:
        raise Http404

    day = liturgics.Day(year, month, day, use_julian=cal=='julian')
    await day.ainitialize()
    await day.apopulate_readings()

    return day

@api.get('/{cal:cal}/{year}/{month}/', response=list[DaySchemaLite])
async def get_calendar_month(request, cal: str, year: int, month: int):
    # Easter date functions don't work correctly outside this range
    if not 1583 <= year <= 4099:
        raise Http404

    days = [d async for d in liturgics.amonth_of_days(year, month, use_julian=cal=='julian')]
    for day in days:
        await day.apopulate_readings(content=False)

    return days

@api.get('/{cal:cal}/', response=DaySchema)
async def get_calendar_default(request, cal: str):
    dt = timezone.localtime()
    return await get_calendar_day(request, cal, dt.year, dt.month, dt.day)
