"""The feasts and fasting seasons of a civil year, for planning a year around
them."""

from dataclasses import dataclass
from datetime import date, timedelta

from django.db.models import Q

from .. import fasting, models
from ..datetools import FastLevelDesc, FastLevels
from .day import _YEAR_CLASSES, Day, _merge_tradition_days, church_date

# Feast levels 7 and 8 are the major feasts of the Theotokos and of the Lord:
# Pascha and the Twelve Great Feasts. Level 6 is the typikon's great-feast
# symbol, which marks the other great feasts.
GREAT_FEAST_LEVEL = 7
FEAST_LEVEL = 6

@dataclass
class Feast:
    date: date
    name: str
    level: int
    pdist: int

    @property
    def is_pascha(self):
        return self.pdist == 0

    @property
    def is_great(self):
        return self.level >= GREAT_FEAST_LEVEL

@dataclass
class FastSeason:
    level: FastLevels
    start: date
    end: date

    @property
    def name(self):
        return FastLevelDesc[self.level]

    @property
    def days(self):
        return (self.end - self.start).days + 1

class _Rows:
    """The `Day` rows that can make a date a feast or put it in a fasting
    season, fetched in one query.

    Building a liturgical `Day` for every date of the year costs two to five
    queries each, mostly for saints this page never shows. Instead, each date's
    rows are picked out here the way `Day._collect_commemorations` selects them,
    and merged by the same `_merge_tradition_days`. Every tradition row comes
    along whatever its values, since an override can lower a common row's feast
    level or fast."""

    def __init__(self):
        rows = models.Day.objects.filter(
            Q(feast_level__gte=FEAST_LEVEL) | Q(fast__gte=FastLevels.LentenFast) |
            Q(fast_exception=fasting.FAST_FREE) | ~Q(tradition='common'))

        self.by_pdist = {}
        self.by_date = {}
        for row in rows:
            if row.pdist == 999:
                self.by_date.setdefault((row.month, row.day), []).append(row)
            else:
                self.by_pdist.setdefault(row.pdist, []).append(row)

    def levels(self, dt, calendar, tradition):
        """Return the date's Pascha distance, feast level and fast level."""

        church, pdist, pyear, _ = church_date(dt, calendar)
        pyear = _YEAR_CLASSES[tradition](pyear, calendar)

        rows = self.by_pdist.get(pdist, []) + self.by_date.get((church.month, church.day), [])
        if float_index := pyear.floats.get(pdist):
            rows += self.by_pdist.get(float_index, [])

        # Leaving out rows below both thresholds can't change whether a date
        # reaches them. A date with none of these rows has neither.
        days = _merge_tradition_days(rows, tradition)
        feast_level = max((d.feast_level for d in days), default=0)
        return pdist, feast_level, fasting.fast_level(days, pdist, pyear)

def _season_level(fast_level):
    """The fasting season a fast level belongs to, or None. The weekly
    Wednesday and Friday fast (FastLevels.Fast) isn't a season."""

    level = FastLevels(fast_level)
    return level if level >= FastLevels.LentenFast else None

def _feast(dt, calendar, tradition):
    """The date's feast, named after its highest-ranked commemoration: a day's
    feast_name list can lead with a saint who shares the day (Palm Sunday has
    no feast_name of its own; its title names it)."""

    day = Day(dt.year, dt.month, dt.day, calendar=calendar, tradition=tradition)
    top = max(day.days, key=lambda d: d.feast_level)
    return Feast(day.gregorian_date, top.feast_name or top.title, day.feast_level, day.pdist)

def year_of_feasts(year, calendar, tradition):
    """Return the feasts that fall in the given civil year, in date order, and
    the fasting seasons that overlap it. A season that runs across New Year
    (on the Julian calendar the Nativity Fast ends on civil January 6) is
    given in full, including its days in the neighboring year."""

    rows = _Rows()
    first, last = date(year, 1, 1), date(year, 12, 31)

    feast_dates = []
    seasons = []
    dt = first
    while dt <= last:
        _, feast_level, fast_level = rows.levels(dt, calendar, tradition)

        if feast_level >= FEAST_LEVEL:
            feast_dates.append(dt)

        if (level := _season_level(fast_level)) is not None:
            if seasons and seasons[-1].level == level and seasons[-1].end == dt - timedelta(days=1):
                seasons[-1].end = dt
            else:
                seasons.append(FastSeason(level, dt, dt))

        dt += timedelta(days=1)

    # Only the feasts themselves need a whole Day, for their names.
    feasts = [_feast(dt, calendar, tradition) for dt in feast_dates]

    # Follow a season that is under way at either end of the year to its
    # actual start or end.
    if seasons and seasons[0].start == first:
        seasons[0].start = _extend(rows, seasons[0].start, -1, seasons[0].level, calendar, tradition)
    if seasons and seasons[-1].end == last:
        seasons[-1].end = _extend(rows, seasons[-1].end, 1, seasons[-1].level, calendar, tradition)

    return feasts, seasons

def _extend(rows, dt, step, level, calendar, tradition):
    """Step from dt a day at a time while the season continues, and return
    the last date still in it. Stops at the edge of the supported years."""

    delta = timedelta(days=step)
    while True:
        try:
            _, _, fast_level = rows.levels(dt + delta, calendar, tradition)
        except ValueError:
            return dt
        if _season_level(fast_level) != level:
            return dt
        dt += delta
