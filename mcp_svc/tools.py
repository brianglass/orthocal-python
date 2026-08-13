from calendarium import liturgics
from calendarium.api import DaySchema
from calendarium.datetools import Calendar, Translation, Tradition
from commemorations.models import DayCommemoration
from commemorations.search import matching_saints

from .server import mcp


@mcp.tool()
async def get_day(
    year: int,
    month: int,
    day: int,
    calendar: Calendar = Calendar.Gregorian,
    tradition: Tradition = Tradition.Slavic,
    translation: Translation = Translation.LXX2012WEB,
) -> dict:
    """Look up feasts, fasting rules, scripture readings, and lives of the
    saints for a single day in the Eastern Orthodox liturgical calendar.

    calendar selects Gregorian (New) or Julian (Old) reckoning. tradition
    selects Slavic (OCA/ROCOR) or Greek (Antiochian/GOARCH) practice.
    translation selects the Bible translation for English readings --
    lxx2012-web (the default, a modern-English pairing of the Brenton
    Septuagint and the World English Bible) or kjv (King James Version);
    it has no effect on non-English content.
    """

    try:
        liturgical_day = liturgics.Day(year, month, day, calendar=calendar, tradition=tradition, translation=translation)
    except ValueError as exc:
        raise ValueError(f'{year}-{month}-{day} is not a valid date: {exc}')

    await liturgical_day.ainitialize()
    await liturgical_day.aget_readings(fetch_content=True)
    await liturgical_day.aget_abbreviated_readings()

    return DaySchema.model_validate(liturgical_day, from_attributes=True).model_dump()


@mcp.tool()
async def search_saints(query: str, tradition: Tradition = Tradition.Slavic) -> list[dict]:
    """Search for a saint or commemoration by name, returning the fixed
    month/day each match is commemorated on (not a specific year's civil
    date -- the Orthodox calendar's fixed commemorations repeat every year
    on the same church-calendar day). Each result includes both the
    occasion-specific title (why they're commemorated on this particular
    day -- repose, translation of relics, etc.) and, when available, the
    saint's full_name -- a plainer, occasion-independent form of their
    identity.
    """

    commemorations = [
        commemoration
        async for commemoration in DayCommemoration.objects.filter(
            saints__in=matching_saints(query),
            tradition__in=(tradition, 'common'),
        ).select_related('day').prefetch_related('daycommemorationsaint_set__saint').order_by(
            'day__month', 'day__day',
        ).distinct()
    ]

    return [
        {
            'month': commemoration.day.month,
            'day': commemoration.day.day,
            'title': commemoration.title,
            # daycommemorationsaint_set (not the saints M2M directly) so
            # DayCommemorationSaint.order controls display order for
            # commemorations naming more than one saint -- .saints.all()
            # falls back to Saint's own (undefined) ordering instead.
            'full_name': ' and '.join(full_names) if (
                full_names := [
                    link.saint.full_name
                    for link in commemoration.daycommemorationsaint_set.all()
                    if link.saint.full_name
                ]
            ) else None,
        }
        for commemoration in commemorations
    ]
