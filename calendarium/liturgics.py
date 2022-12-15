from datetime import date, datetime, timedelta, timezone

from . import datetools


class LiturgicalDay:
    def __init__(self, year, month, day, use_julian=False):
        if use_julian:
            dt = datetools.gregorian_to_julian(year, month, day)
        else:
            dt = date(year=year, month=month, day=day)

        self._date = dt
        self.year = dt.year
        self.month = dt.month
        self.day = dt.day

        if use_julian:
            pdist, pyear = datetools.compute_julian_pascha_distance(dt)
            self.jdn = datetools.julian_to_jdn(dt)
        else:
            pdist, pyear = datetools.compute_pascha_distance(dt)
            self.jdn = datetools.gregorian_to_jdn(dt)

        self.pdist = pdist
        self.weekday = datetools.weekday_from_pdist(pdist)

        self.year = LiturgicalYear(year, use_julian)

    def __str__(self):
        return str(self._date)


class LiturgicalYear:
    def __init__(self, year, use_julian=False):
        self.year = year
        self.use_julian = use_julian
        self.pascha = datetools.compute_pascha_jdn(year)
        self.previous_pascha = datetools.compute_pascha_jdn(year - 1)
        self.next_pascha = datetools.compute_pascha_jdn(year + 1)
