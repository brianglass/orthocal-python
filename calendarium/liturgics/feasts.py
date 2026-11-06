"""The feasts and fasting seasons of a civil year, for planning a year around
them."""

from calendar import isleap
from dataclasses import dataclass
from datetime import date, timedelta

from django.db.models import Q

from .. import fasting, models
from ..datetools import Calendar, FastLevelDesc, FastLevels, julian_to_gregorian
from .day import _YEAR_CLASSES, _merge_tradition_days, church_date

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
    queries each, mostly for saints this page never shows. Instead, `dates`
    finds the dates these rows fall on, and each one's rows are picked out the
    way `Day._collect_commemorations` selects them and merged by the same
    `_merge_tradition_days`, so no `Day` needs building at all. Every tradition
    row comes along whatever its values, since an override can lower a common
    row's feast level or fast."""

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

    def dates(self, year, calendar, tradition):
        """Return, in order, the civil dates in the year that a row falls on,
        or that are in the Apostles' Fast, which no row marks."""

        dates = set()

        # A fixed-date row's date is on the church calendar. On the Julian
        # calendar the civil year starts on church December 19 of the year
        # before.
        for month, day in self.by_date:
            if calendar == Calendar.Gregorian:
                if (month, day) != (2, 29) or isleap(year):
                    dates.add(date(year, month, day))
                continue
            for church_year in (year - 1, year):
                if (month, day) != (2, 29) or church_year % 4 == 0:
                    dates.add(julian_to_gregorian(church_year, month, day))

        # A civil year holds the end of one Paschal year and the start of the
        # next.
        for paschal_year in (year - 1, year):
            pyear = _YEAR_CLASSES[tradition](paschal_year, calendar)
            pdists = [pdist for pdist in self.by_pdist if pdist < 1000]
            pdists += [pdist for pdist, index in pyear.floats.items() if index in self.by_pdist]
            pdists += range(57, pyear.peter_and_paul)
            dates.update(_jdn_to_date(pyear.pascha + pdist) for pdist in pdists)

        return sorted(dt for dt in dates if dt.year == year)

    def levels(self, dt, calendar, tradition):
        """Return the date's Pascha distance, merged rows, feast level and
        fast level."""

        church, pdist, pyear, _ = church_date(dt, calendar)
        pyear = _YEAR_CLASSES[tradition](pyear, calendar)

        rows = self.by_pdist.get(pdist, []) + self.by_date.get((church.month, church.day), [])
        if float_index := pyear.floats.get(pdist):
            rows += self.by_pdist.get(float_index, [])

        # Leaving out rows below both thresholds can't change whether a date
        # reaches them. A date with none of these rows has neither.
        days = _merge_tradition_days(rows, tradition)
        feast_level = max((d.feast_level for d in days), default=0)
        return pdist, days, feast_level, fasting.fast_level(days, pdist, pyear)

def _jdn_to_date(jdn):
    """The civil date of a Julian day number."""

    return date.fromordinal(jdn - 1721425)

def _season_level(fast_level):
    """The fasting season a fast level belongs to, or None. The weekly
    Wednesday and Friday fast (FastLevels.Fast) isn't a season."""

    level = FastLevels(fast_level)
    return level if level >= FastLevels.LentenFast else None

def _feast(dt, pdist, days, feast_level):
    """The date's feast, named after its highest-ranked commemoration: a day's
    feast_name list can lead with a saint who shares the day (Palm Sunday has
    no feast_name of its own; its title names it)."""

    top = max(days, key=lambda d: d.feast_level)
    return Feast(dt, top.feast_name or top.title, feast_level, pdist)

def year_of_feasts(year, calendar, tradition):
    """Return the feasts that fall in the given civil year, in date order, and
    the fasting seasons that overlap it. A season that runs across New Year
    (on the Julian calendar the Nativity Fast ends on civil January 6) is
    given in full, including its days in the neighboring year."""

    rows = _Rows()
    first, last = date(year, 1, 1), date(year, 12, 31)

    feasts = []
    seasons = []
    for dt in rows.dates(year, calendar, tradition):
        pdist, days, feast_level, fast_level = rows.levels(dt, calendar, tradition)

        if feast_level >= FEAST_LEVEL:
            feasts.append(_feast(dt, pdist, days, feast_level))

        if (level := _season_level(fast_level)) is not None:
            if seasons and seasons[-1].level == level and seasons[-1].end == dt - timedelta(days=1):
                seasons[-1].end = dt
            else:
                seasons.append(FastSeason(level, dt, dt))

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
            *_, fast_level = rows.levels(dt + delta, calendar, tradition)
        except ValueError:
            return dt
        if _season_level(fast_level) != level:
            return dt
        dt += delta
