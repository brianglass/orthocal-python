from datetime import date, datetime, timedelta, timezone

from django.utils.functional import cached_property

from . import datetools
from .datetools import Weekday


class Day:
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

        self.year = Year(year, use_julian)

    def __str__(self):
        return str(self._date)


class Year:
    def __init__(self, year, use_julian=False):
        self.year = year
        self.use_julian = use_julian
        self.pascha = datetools.compute_pascha_jdn(year)

    @cached_property
    def previous_pascha(self):
        return datetools.compute_pascha_jdn(self.year - 1)

    @cached_property
    def next_pascha(self):
        return datetools.compute_pascha_jdn(self.year + 1)

    def has_daily_readings(self, pdist):
        return pdist not in self.no_daily

    def has_paremias(self, pdist):
        return self.paremias.get(pdist, None)

    def has_no_paremias(self, pdist):
        return self.paremias.get(pdist, None) is False

    @cached_property
    def no_daily(self):
        """Return a set() of days on which daily readings are suppressed"""

        _, sun_before_theophany, sat_after_theophany, sun_after_theophany = \
                datetools.surrounding_weekends(self.theophany)
        _, sun_before_nativity, _, sun_after_nativity = \
                datetools.surrounding_weekends(self.nativity)

        no_daily = {
                sun_before_theophany, sun_after_theophany, self.theophany-5,
                self.theophany-1, self.theophany, self.forefathers,
                sun_before_nativity, self.nativity-1, self.nativity,
                self.nativity+1, sun_after_nativity,
        }

        if sat_after_theophany == self.theophany+1:
            no_daily.add(sat_after_theophany)

        if datetools.weekday_from_pdist(self.annunciation) == Weekday.Saturday:
            nodaily.add(self.annunciation)

        return no_daily

    @cached_property
    def theophany(self):
        return self._date_to_pdist(1, 6, self.year+1)

    @cached_property
    def finding(self):
        return self._date_to_pdist(2, 24, self.year)

    @cached_property
    def annunciation(self):
        return self._date_to_pdist(3, 25, self.year)

    @cached_property
    def peter_and_paul(self):
        return self._date_to_pdist(6, 29, self.year)

    @cached_property
    def beheading(self):
        return self._date_to_pdist(8, 29, self.year)

    @cached_property
    def nativity_theotokos(self):
        return self._date_to_pdist(9, 8, self.year)

    @cached_property
    def elevation(self):
        return self._date_to_pdist(9, 14, self.year)

    @cached_property
    def nativity(self):
        return self._date_to_pdist(12, 25, self.year)

    @cached_property
    def fathers_six(self):
        # The Fathers of the Sixth Ecumenical Council falls on the Sunday nearest 7/16
        pdist = self._date_to_pdist(7, 16, self.year)
        weekday = datetools.weekday_from_pdist(pdist)
        if weekday < Weekday.Thursday:
            return pdist - weekday
        else:
            return pdist + 7 - weekday

    @cached_property
    def fathers_seven(self):
        # The Fathers of the Seventh Ecumenical Council falls on the Sunday
        # following 10/11 or 10/11 itself if it is a Sunday.
        pdist = self._date_to_pdist(10, 11, self.year)
        weekday = datetools.weekday_from_pdist(pdist)
        if weekday > Weekday.Sunday:
            pdist += 7 - weekday
        return pdist

    @cached_property
    def demetrius_saturday(self):
        # Demetrius Saturday is the Saturday before 10/26
        pdist = self._date_to_pdist(10, 26, self.year)
        return pdist - datetools.weekday_from_pdist(pdist) - 1

    @cached_property
    def synaxis_unmercenaries(self):
        # The Synaxis of the Unmercenaries is the Sunday following 11/1
        pdist = self._date_to_pdist(11, 1, self.year)
        return pdist + 7 - datetools.weekday_from_pdist(pdist)

    @cached_property
    def forefathers(self):
        # Forefathers Sunday is the week before the week of Nativity
        weekday = datetools.weekday_from_pdist(self.nativity)
        return self.nativity - 14 + ((7 - weekday) % 7)

    @cached_property
    def lucan_jump(self):
        # 168 - (Sunday after Elevation)
        return 168 - (self.elevation + 7 - datetools.weekday_from_pdist(self.elevation))

    @cached_property
    def extra_sundays(self):
        _, _, _, sun_after_theophany = datetools.surrounding_weekends(self.theophany)
        return (self.next_pascha - self.pascha - 84 - sun_after_theophany) // 7

    @cached_property
    def reserves(self):
        """Return a list of pascha distances for days with unread Sunday gospels"""

        reserves = []

        if self.extra_sundays:
            first = self.forefathers + self.lucan_jump + 7
            reserves.extend(range(first, 267, 7))
            if remainder := self.extra_sundays - len(reserves):
                start = 175 - remainder * 7
                reserves.extend(range(start, 169, 7))

        return reserves

    @cached_property
    def paremias(self):
        # minor feasts on weekdays in lent have their paremias moved to previous day

        paremias = {}

        days = (2, 24), (2, 27), (3, 9), (3, 31), (4, 7), (4, 23), (4, 25), (4, 30)
        for month, day in days:
            pdist = self._date_to_pdist(month, day, self.year)
            weekday = datetools.weekday_from_pdist(pdist)
            if pdist > -44 and pdist < -7 and weekday > Weekday.Monday:
                paremias[pdist] = False
                paremias[pdist-1] = True

        return paremias

    def _date_to_pdist(self, month, day, year):
        dt = date(year, month, day)
        if self.use_julian:
            # TODO: Need to test this and confirm it's valid
            return datetools.julian_to_jdn(dt) - self.pascha
        else:
            return datetools.gregorian_to_jdn(dt) - self.pascha

    @cached_property
    def floats(self):
        """Return a dict of floating feasts and their indexes into the database."""

        sat_before_elevation, sun_before_elevation, sat_after_elevation, sun_after_elevation = \
                datetools.surrounding_weekends(self.elevation)
        sat_before_theophany, sun_before_theophany, sat_after_theophany, sun_after_theophany = \
                datetools.surrounding_weekends(self.theophany)
        sat_before_nativity, sun_before_nativity, sat_after_nativity, sun_after_nativity = \
                datetools.surrounding_weekends(self.nativity)

        floats = {
                self.fathers_six: 1001,
                self.fathers_seven: 1002,
                self.demetrius_saturday: 1003,
                self.synaxis_unmercenaries: 1004,
                sun_before_elevation: 1007,
                sat_after_elevation: 1008,
                sun_after_elevation: 1009,
                self.forefathers: 1010,
                sat_after_theophany: 1029,
                sun_after_theophany: 1030,
        }

        if sat_before_elevation == self.nativity_theotokos:
            floats[self.elevation - 1] = 1005
        else:
            floats[sat_before_elevation] = 1006

        nativity_eve = self.nativity - 1
        if nativity_eve == sat_before_nativity:
            floats.update({
                self.nativity - 2: 1013,
                sun_before_nativity: 1012,
                nativity_eve: 1015,
            })
        elif nativity_eve == sun_before_nativity:
            floats.update({
                self.nativity - 2: 1013,
                sat_before_nativity: 1011,
                nativity_eve: 1016,
            })
        else:
            floats.update({
                nativity_eve: 1014,
                sat_before_nativity: 1011,
                sun_before_nativity: 1012,
            })

        match datetools.weekday_from_pdist(self.nativity):
            case Weekday.Sunday:
                floats.update({
                    sat_after_nativity: 1017,
                    self.nativity+1: 1020,
                    sun_before_theophany: 1024,
                    self.theophany-1: 1026,
                })
            case Weekday.Monday:
                floats.update({
                    sat_after_nativity: 1017,
                    sun_after_nativity: 1021,
                    self.theophany-5: 1023,
                    self.theophany-1: 1026,
                })
            case Weekday.Tuesday:
                floats.update({
                    sat_after_nativity: 1019,
                    sun_after_nativity: 1021,
                    sat_before_theophany: 1027,
                    self.theophany-5: 1023,
                    self.theophany-2: 1025,
                })
            case Weekday.Wednesday:
                floats.update({
                    sat_after_nativity: 1019,
                    sun_after_nativity: 1021,
                    sat_before_theophany: 1022,
                    sun_before_theophany: 1028,
                    self.theophany-3: 1025,
                })
            case Weekday.Thursday | Weekday.Friday:
                floats.update({
                    sat_after_nativity: 1019,
                    sun_after_nativity: 1021, 
                    sat_before_theophany: 1022,
                    sun_before_theophany: 1024, 
                    self.theophany-1: 1026, 
                })
            case Weekday.Saturday:
                floats.update({
                    self.nativity+6: 1018, 
                    sun_after_nativity: 1021, 
                    sat_before_theophany: 1022, 
                    sun_before_theophany: 1024, 
                    self.theophany-1: 1026, 
                })

        # New Martyrs of Russia (OCA) is the Sunday on or before 1/31
        martyrs = self._date_to_pdist(1, 31, self.year)
        weekday = datetools.weekday_from_pdist(martyrs)
        if weekday != Weekday.Sunday:
            # The Sunday before 1/31
            martyrs = martyrs - 7 + ((7 - weekday) % 7)

        floats[martyrs] = 1031

        # Floats around Annunciation
        match datetools.weekday_from_pdist(self.annunciation):
            case Weekday.Saturday:
                floats[self.annunciation-1] = 1032
                floats[self.annunciation] = 1033
            case Weekday.Sunday:
                floats[self.annunciation] = 1034
            case Weekday.Monday:
                floats[self.annunciation] = 1035
            case _:
                floats[self.annunciation-1] = 1036
                floats[self.annunciation] = 1037

        return floats
