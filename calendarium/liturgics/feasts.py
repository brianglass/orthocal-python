"""The feasts and fasting seasons of a civil year, for planning a year around
them."""

from dataclasses import dataclass
from datetime import date, timedelta

from ..datetools import FastLevelDesc, FastLevels
from .day import Day

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

def _day(dt, **kwargs):
    return Day(dt.year, dt.month, dt.day, **kwargs)

def _season_level(day):
    """The fasting season a day belongs to, or None. The weekly Wednesday and
    Friday fast (FastLevels.Fast) isn't a season."""

    level = FastLevels(day.fast_level)
    return level if level >= FastLevels.LentenFast else None

def _feast(day):
    """The day's feast if it ranks as one, named after its highest-ranked
    commemoration: a day's feast_name list can lead with a saint who shares
    the day (Palm Sunday has no feast_name of its own; its title names it)."""

    if day.feast_level < FEAST_LEVEL:
        return None

    top = max(day.days, key=lambda d: d.feast_level)
    return Feast(day.gregorian_date, top.feast_name or top.title, day.feast_level, day.pdist)

def year_of_feasts(year, calendar, tradition):
    """Return the feasts that fall in the given civil year, in date order, and
    the fasting seasons that overlap it. A season that runs across New Year
    (on the Julian calendar the Nativity Fast ends on civil January 6) is
    given in full, including its days in the neighboring year."""

    kwargs = {'calendar': calendar, 'tradition': tradition}
    first, last = date(year, 1, 1), date(year, 12, 31)

    days = []
    dt = first
    while dt <= last:
        days.append(_day(dt, **kwargs))
        dt += timedelta(days=1)

    feasts = [feast for day in days if (feast := _feast(day))]

    seasons = []
    for day in days:
        level = _season_level(day)
        if level is None:
            continue
        if seasons and seasons[-1].level == level and seasons[-1].end == day.gregorian_date - timedelta(days=1):
            seasons[-1].end = day.gregorian_date
        else:
            seasons.append(FastSeason(level, day.gregorian_date, day.gregorian_date))

    # Follow a season that is under way at either end of the year to its
    # actual start or end.
    if seasons and seasons[0].start == first:
        seasons[0].start = _extend(seasons[0].start, -1, seasons[0].level, kwargs)
    if seasons and seasons[-1].end == last:
        seasons[-1].end = _extend(seasons[-1].end, 1, seasons[-1].level, kwargs)

    return feasts, seasons

def _extend(dt, step, level, kwargs):
    """Step from dt a day at a time while the season continues, and return
    the last date still in it. Stops at the edge of the supported years."""

    delta = timedelta(days=step)
    while True:
        try:
            if _season_level(_day(dt + delta, **kwargs)) != level:
                return dt
        except ValueError:
            return dt
        dt += delta
