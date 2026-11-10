from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from mcp.server.mcpserver.exceptions import ToolError

from calendarium import liturgics
from calendarium.api import DaySchema
from calendarium.datetools import Calendar, FeastLevels, Translation, Tradition
from calendarium.liturgics.day import _has_story
from commemorations.models import DayCommemoration, Saint
from commemorations.search import corrected_query, matching_lives, matching_saints

from orthocal.decorators import in_thread_pool

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
    Septuagint and the World English Bible), kjv (King James Version), or
    douay-rheims (Douay-Rheims); it has no effect on non-English content.
    """

    return await _get_day(year, month, day, calendar, tradition, translation)


@in_thread_pool
def _get_day(year, month, day, calendar, tradition, translation):
    try:
        liturgical_day = liturgics.Day(year, month, day, calendar=calendar, tradition=tradition, translation=translation)
    except ValueError as exc:
        raise ToolError(f'{year}-{month}-{day} is not a valid date: {exc}')

    liturgical_day.get_readings(fetch_content=True)
    liturgical_day.get_abbreviated_readings()

    return DaySchema.model_validate(liturgical_day, from_attributes=True).model_dump()


def _occasion_date(day):
    """Where a commemoration's calendar.Day falls, for search_saints and
    get_saint. See calendarium/models.py: pdist 999 is the fixed calendar,
    and 1000+ are float slots (FloatIndex) whose pdist isn't a distance
    from Pascha."""

    if day.pdist == 999:
        return {'month': day.month, 'day': day.day}
    if day.pdist >= 1000:
        return {'moveable': True}
    return {'moveable': True, 'pascha_distance': day.pdist}


@mcp.tool()
async def search_saints(query: str) -> list[dict]:
    """Search for a saint or commemoration by name, returning the fixed
    month/day each match is commemorated on (not a specific year's civil
    date -- the Orthodox calendar's fixed commemorations repeat every year
    on the same church-calendar day), or moveable=true, as in get_saint, for
    the few that move from year to year. Each result includes both the
    occasion-specific title (why they're commemorated on this particular
    day -- repose, translation of relics, etc.) and, when available, the
    saint's full_name -- a plainer, occasion-independent form of their
    identity.

    It searches every tradition at once. Each result's tradition says whose
    calendar keeps that commemoration: "common" (both), "slavic" or
    "greek". Pass "slavic" or "greek" on to get_saint and get_day, which
    show one tradition at a time.

    The query can also describe a saint instead of naming one ("physician",
    "Cappadocia", "fool for Christ"). After the name matches, by date, come
    up to 10 commemorations whose life mentions every word in
    the query, best match first. matched says which kind each result is,
    "name" or "life", and a life match has an excerpt around the words.

    Results never include the full life (story) text, since a search can
    match many commemorations. has_story says whether a result has one; to
    read it, pass one of the result's saint_slugs to get_saint.

    When nothing matches and a word looks misspelled ("Seraphm"), the search
    is retried with the closest known words, and each result's
    corrected_query says what was searched instead.
    """

    return await _search_saints(query)


# How many matches in the lives search_saints adds after the name matches.
LIFE_MATCH_LIMIT = 10


def _search_result(commemoration, **extra):
    return {
        **_occasion_date(commemoration.day),
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
        'has_story': _has_story(commemoration),
        'saint_slugs': [link.saint.slug for link in commemoration.daycommemorationsaint_set.all()],
        'tradition': commemoration.tradition,
        **extra,
    }


@in_thread_pool
def _search_saints(query):
    # As the saints page does (commemorations/views.py), retry a search that
    # finds nothing with its misspelled words corrected.
    results = _saint_results(query)
    if not results and (corrected := corrected_query(query)):
        results = [{**result, 'corrected_query': corrected} for result in _saint_results(corrected)]
    return results


def _saint_results(query):
    commemorations = DayCommemoration.objects.select_related('day').prefetch_related(
        'daycommemorationsaint_set__saint',
    )
    by_name = commemorations.filter(
        saints__in=matching_saints(query),
    ).order_by('day__month', 'day__day').distinct()

    results = [_search_result(commemoration, matched='name') for commemoration in by_name]

    # Lives are searched whole words only (no prefix): a client sends its
    # query complete, not as it types.
    seen = {commemoration.pk for commemoration in by_name}
    matches = matching_lives(query)
    in_lives = commemorations.exclude(saints=None).in_bulk(
        [match.commemoration_id for match in matches if match.commemoration_id not in seen],
    )
    life_results = []
    for match in matches:
        if commemoration := in_lives.get(match.commemoration_id):
            life_results.append(_search_result(commemoration, matched='life', excerpt=match.excerpt_text()))
            if len(life_results) == LIFE_MATCH_LIMIT:
                break

    return results + life_results


@mcp.tool()
async def get_saint(slug: str, tradition: Tradition = Tradition.Slavic) -> dict:
    """Look up one saint by the slug from a search_saints result's
    saint_slugs, returning every occasion they're commemorated on in the
    given tradition, each with its life (story) as HTML when there is one.

    A fixed commemoration has a church-calendar month and day. A moveable
    one has moveable=true instead, plus pascha_distance (days from Pascha)
    when it's tied to Pascha -- some, like a "first Saturday of November"
    feast, are tied to neither; use get_day to find where they fall.
    A story naming several saints is the shared life of a joint
    commemoration and appears under each of them.
    """

    return await _get_saint(slug, tradition)


@in_thread_pool
def _get_saint(slug, tradition):
    saint = Saint.objects.filter(slug=slug).first()
    if saint is None:
        raise ToolError(f'No saint with slug {slug!r}; use a slug from search_saints.')

    commemorations = DayCommemoration.objects.filter(
        saints=saint,
        tradition__in=(tradition, 'common'),
    ).select_related('day').order_by('day__month', 'day__day')

    return {
        'slug': saint.slug,
        # Same preference as the saint page (commemorations/views.py): name
        # is often occasion-specific ("Repose of..."), full_name is not.
        'name': saint.full_name or saint.name,
        'url': settings.ORTHOCAL_PUBLIC_URL + reverse('saint-detail', args=[saint.slug]),
        'commemorations': [
            {
                **_occasion_date(commemoration.day),
                'title': commemoration.title,
                'story': commemoration.story if _has_story(commemoration) else None,
            }
            for commemoration in commemorations
        ],
    }


@mcp.tool()
async def search_feasts(
    query: str = '',
    year: int | None = None,
    calendar: Calendar = Calendar.Gregorian,
    tradition: Tradition = Tradition.Slavic,
) -> dict:
    """Find feasts by name and the civil dates they fall on in a year (this
    year by default) -- "Pascha", "Palm Sunday", "Mid-Pentecost", "Sunday of
    Orthodoxy", "Leavetaking of Theophany", "Protection" -- including the
    moveable ones that change date every year. Fasting seasons whose names
    match come back too ("Nativity Fast", "Lent").

    Without a query, returns the year's great feasts (Pascha, the Twelve
    Great Feasts, and the other great feasts) and all its fasting seasons.

    Each feast's date is the civil date for the given calendar, so on the
    Julian (Old) calendar no conversion is needed. A fixed feast also has its
    church-calendar month and day; a moveable one has moveable=true, plus
    pascha_distance when it's tied to Pascha. level ranks the feast (8 and 7
    are Pascha and the Twelve Great Feasts, 6 the other great feasts, lower
    ones the smaller feasts, forefeasts and leavetakings). The major saints'
    days are here too ("St Nicholas"); search_saints finds every saint and
    icon, with their lives, but gives church-calendar dates only.
    """

    if year is None:
        year = timezone.localtime().year
    if not 1584 <= year <= 4099:
        raise ToolError(f'{year} is outside the supported years, 1584-4099.')

    return await _search_feasts(query, year, calendar, tradition)


def _feast_result(match, calendar, tradition):
    row, dt = match.row, match.date
    if row.pdist == 999:
        occasion = {'month': row.month, 'day': row.day}
    elif row.pdist >= 1000:
        occasion = {'moveable': True}
    else:
        occasion = {'moveable': True, 'pascha_distance': row.pdist}

    level = row.feast_level or 0
    return {
        'name': match.name,
        # A moveable day's own title, when its feast name is something else
        # ("Beginning of the Lenten Triodion" is the Sunday of the Publican
        # and the Pharisee).
        **({'title': row.title} if row.title and row.title != match.name else {}),
        'date': dt.isoformat(),
        'weekday': dt.strftime('%A'),
        **occasion,
        'level': level,
        'level_desc': FeastLevels[level],
        'tradition': row.tradition,
        'url': settings.ORTHOCAL_PUBLIC_URL + reverse(
            'readings', kwargs={'tradition': tradition, 'cal': calendar, 'year': dt.year, 'month': dt.month, 'day': dt.day},
        ),
    }


# How many feasts search_feasts returns for a query. Theophany's forefeasts,
# afterfeasts and leavetaking alone are 14.
FEAST_LIMIT = 25


@in_thread_pool
def _search_feasts(query, year, calendar, tradition):
    matches, seasons = liturgics.search_feasts(query, year, calendar=calendar, tradition=tradition)
    if query.strip():
        matches = matches[:FEAST_LIMIT]

    return {
        'year': year,
        'calendar': calendar,
        'tradition': tradition,
        'feasts': [_feast_result(match, calendar, tradition) for match in matches],
        'fasting_seasons': [
            {'name': season.name, 'start': season.start.isoformat(), 'end': season.end.isoformat(), 'days': season.days}
            for season in seasons
        ],
    }
