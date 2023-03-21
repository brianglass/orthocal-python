from datetime import date
from functools import lru_cache

from django.utils.functional import cached_property

from .. import datetools
from ..datetools import Calendar, Weekday, FloatIndex


@lru_cache
class Year:
    """Representation of a liturgical year.

    While the literal Church year begins on September 1, for the purposes of
    computing feasts, fasts, and readings, it is more practical to represent
    the year with Pascha as its locus. For that reason, this Year class
    represents the period from one Zacchaeus Sunday (77 days before Pascha)
    to the next.
    """

    def __init__(self, year, calendar: Calendar=Calendar.Gregorian):
        self.year = year
        self.calendar = calendar
        self.pascha = datetools.compute_pascha_jdn(year)

        (self.sat_before_elevation,
         self.sun_before_elevation,
         self.sat_after_elevation,
         self.sun_after_elevation) = datetools.surrounding_weekends(self.elevation)

        (self.sat_before_theophany,
         self.sun_before_theophany,
         self.sat_after_theophany,
         self.sun_after_theophany) = datetools.surrounding_weekends(self.theophany)

        (self.sat_before_nativity,
         self.sun_before_nativity,
         self.sat_after_nativity,
         self.sun_after_nativity) = datetools.surrounding_weekends(self.nativity)

    @cached_property
    def previous_pascha(self):
        return datetools.compute_pascha_jdn(self.year - 1)

    @cached_property
    def next_pascha(self):
        return datetools.compute_pascha_jdn(self.year + 1)

    def has_daily_readings(self, pdist):
        return pdist not in self.no_daily

    def has_moved_paremias(self, pdist):
        return self.paremias.get(pdist) is True

    def has_no_paremias(self, pdist):
        return self.paremias.get(pdist) is False

    @cached_property
    def no_daily(self):
        """Return a set() of days on which daily readings are suppressed"""

        no_daily = {
                self.sun_before_theophany, self.sun_after_theophany, self.theophany-5,
                self.theophany-1, self.theophany, self.forefathers,
                self.sun_before_nativity, self.nativity-1, self.nativity,
                self.nativity+1, self.sun_after_nativity,
        }

        if self.sat_after_theophany == self.theophany+1:
            no_daily.add(self.sat_after_theophany)

        if datetools.weekday_from_pdist(self.annunciation) == Weekday.Saturday:
            no_daily.add(self.annunciation)

        return no_daily

    @cached_property
    def theophany(self):
        return self.date_to_pdist(1, 6, self.year+1)

    @cached_property
    def finding(self):
        return self.date_to_pdist(2, 24, self.year)

    @cached_property
    def annunciation(self):
        return self.date_to_pdist(3, 25, self.year)

    @cached_property
    def peter_and_paul(self):
        return self.date_to_pdist(6, 29, self.year)

    @cached_property
    def beheading(self):
        return self.date_to_pdist(8, 29, self.year)

    @cached_property
    def nativity_theotokos(self):
        return self.date_to_pdist(9, 8, self.year)

    @cached_property
    def elevation(self):
        return self.date_to_pdist(9, 14, self.year)

    @cached_property
    def nativity(self):
        return self.date_to_pdist(12, 25, self.year)

    @cached_property
    def fathers_six(self):
        # The Fathers of the Sixth Ecumenical Council falls on the Sunday nearest 7/16
        pdist = self.date_to_pdist(7, 16, self.year)
        weekday = datetools.weekday_from_pdist(pdist)
        if weekday < Weekday.Thursday:
            return pdist - weekday
        else:
            return pdist + 7 - weekday

    @cached_property
    def fathers_seven(self):
        # The Fathers of the Seventh Ecumenical Council falls on the Sunday
        # following 10/11 or 10/11 itself if it is a Sunday.
        pdist = self.date_to_pdist(10, 11, self.year)
        weekday = datetools.weekday_from_pdist(pdist)
        if weekday > Weekday.Sunday:
            pdist += 7 - weekday
        return pdist

    @cached_property
    def demetrius_saturday(self):
        # Demetrius Saturday is the Saturday before 10/26
        pdist = self.date_to_pdist(10, 26, self.year)
        return pdist - datetools.weekday_from_pdist(pdist) - 1

    @cached_property
    def synaxis_unmercenaries(self):
        # The Synaxis of the Unmercenaries is the Sunday following 11/1
        pdist = self.date_to_pdist(11, 1, self.year)
        return pdist + 7 - datetools.weekday_from_pdist(pdist)

    @cached_property
    def forefathers(self):
        # Forefathers Sunday is the week before the week of Nativity
        weekday = datetools.weekday_from_pdist(self.nativity)
        return self.nativity - 14 + ((7 - weekday) % 7)

    @cached_property
    def new_martyrs_russia(self):
        # Holy New Martyrs and Confessors of Russia On the Sunday closest to January 25
        pdist = self.date_to_pdist(1, 25, self.year+1)
        weekday = datetools.weekday_from_pdist(pdist)
        if weekday < Weekday.Thursday:
            return pdist - weekday
        else:
            return pdist - weekday + 7

    @cached_property
    def lukan_jump(self):
        """The number of days to jump forward in the gospel cycle. Divisible by 7."""

        # The Gospel reading for the Monday of the 18th week after Pentecost,
        # Luke 3.19-22 (Lukan pericope 10), must be read on the Monday AFTER
        # the Sunday AFTER the Elevation of the cross.
        #
        # This syncs the remainder of the paschal cycle to within 1 week of a
        # fixed point in the festal cycle, but only for the Gospel.
        #
        # See https://www.orthodox.net/ustav/lukan-jump.html

        eighteenth_monday = 49+1 + 7*17  # Pentecost+1 + 17 weeks
        mon_after_elevation = self.sun_after_elevation + 1
        return eighteenth_monday - mon_after_elevation

    @cached_property
    def first_sun_luke(self):
        """The first Sunday of Luke, after the Lukan jump."""
        # Reading of Luke starts on self.sun_after_elevation + 1, which is a Monday
        return self.sun_after_elevation + 7

    @cached_property
    def extra_sundays(self):
        """The number of sundays between Sunday after Theophany and the Triodion."""
        sun_before_zaccheus = self.next_pascha - 12*7
        sun_after_theophany = self.pascha + self.sun_after_theophany
        return (sun_before_zaccheus - sun_after_theophany) // 7

    @cached_property
    def reserves(self):
        """A list of pascha distances for days with unread Sunday gospels.

        These are saved for use between Theophany and the Triodion. 
        """

        reserves = []

        # This is the Gospel we read on the first Sunday of Luke. It is
        # assigned to the eighteenth Sunday after Pentecost. 
        first_luke = 49 + 7*18

        # The Gospel that is read on the 13th Sunday of Luke.
        thirteenth_luke = first_luke + 7*13
        
        if self.extra_sundays:
            # These are the Sunday Gospels we skipped between Forefathers
            # Sunday and Theophany because they were overshadowed by the
            # readings from the Festal cycle (e.g. Nativity).
            forefathers = self.forefathers + self.lukan_jump + 7
            reserves.extend(range(forefathers, thirteenth_luke+1, 7))

            if remainder := self.extra_sundays - len(reserves):
                # these are the Sunday Gospels we jumped over in the lukan jump.
                start = first_luke - remainder * 7
                end = first_luke - 6  # First Monday of Luke
                reserves.extend(range(start, end, 7))

        return reserves

    @cached_property
    def paremias(self):
        """Return a table of paremias that should be moved."""

        # minor feasts on weekdays in lent have their paremias moved to previous day

        paremias = {}

        # These seem to be feasts with 3 <= FeastLevel <= 5. We could probably
        # grab this from the database at run time.
        days = (
                (2, 24),    # 1st and 2nd finding of the head of John the Baptist
                (2, 27),    # St. Raphael, Bishop of Brooklyn
                (3, 9),     # Holy Forty Martyrs of Sebaste
                (3, 31),    # Repose St Innocent, Metr. Moscow and Apostle to Americas
                (4, 7),     # Repose St. Tikhon, Patriarch of Moscow, Enlightener N. America
                (4, 23),    # Holy Greatmartyr, Victorybearer and Wonderworker George
                (4, 25),    # Holy Apostle and Evangelist Mark
                (4, 30),    # Holy Apostle James, Brother of St John
        )
        for month, day in days:
            pdist = self.date_to_pdist(month, day, self.year)
            weekday = datetools.weekday_from_pdist(pdist)
            if -44 < pdist < -7 and weekday > Weekday.Monday:
                paremias[pdist] = False
                paremias[pdist-1] = True

        return paremias

    def date_to_pdist(self, month, day, year):
        dt = date(year, month, day)
        if self.calendar == Calendar.Julian:
            return datetools.julian_to_jdn(dt) - self.pascha
        else:
            return datetools.gregorian_to_jdn(dt) - self.pascha

    @cached_property
    def floats(self):
        """Return a dict of floating feast pdists and their indices into the database."""

        floats = {
                self.fathers_six:               FloatIndex.FathersSix,
                self.fathers_seven:             FloatIndex.FathersSeventh,
                self.demetrius_saturday:        FloatIndex.DemetriusSaturday,
                self.synaxis_unmercenaries:     FloatIndex.SynaxisUnmercenaries,
                self.sun_before_elevation:      FloatIndex.SunBeforeElevation,
                self.sat_after_elevation:       FloatIndex.SatAfterElevation,
                self.sun_after_elevation:       FloatIndex.SunAfterElevation,
                self.forefathers:               FloatIndex.SunForefathers,
                self.sat_after_theophany:       FloatIndex.SatAfterTheophany,
                self.sun_after_theophany:       FloatIndex.SunAfterTheophany,
                self.new_martyrs_russia:        FloatIndex.NewMartyrsRussia,
        }

        if self.sat_before_elevation == self.nativity_theotokos:
            # If the Saturday before the Elevation falls on the Nativity of the
            # Theotokos, we move its readings to the eve of the Elevation.
            floats[self.elevation - 1] = FloatIndex.SatBeforeElevationMoved
        else:
            floats[self.sat_before_elevation] = FloatIndex.SatBeforeElevation

        nativity_eve = self.nativity - 1
        if nativity_eve == self.sat_before_nativity:
            # Nativity is on Sunday; Royal Hours on Friday
            floats.update({
                self.nativity - 2:          FloatIndex.RoyalHoursNativityFriday,
                self.sun_before_nativity:   FloatIndex.SunBeforeNativity,
                nativity_eve:               FloatIndex.SatBeforeNativityEve,
            })
        elif nativity_eve == self.sun_before_nativity:
            # Nativity is on Monday; Royal Hours on Friday
            floats.update({
                self.nativity - 3:          FloatIndex.RoyalHoursNativityFriday,
                self.sat_before_nativity:   FloatIndex.SatBeforeNativity,
                nativity_eve:               FloatIndex.SunBeforeNativityEve,
            })
        else:
            floats.update({
                nativity_eve:               FloatIndex.EveNativity,
                self.sat_before_nativity:   FloatIndex.SatBeforeNativity,
                self.sun_before_nativity:   FloatIndex.SunBeforeNativity,
            })

        match datetools.weekday_from_pdist(self.nativity):
            case Weekday.Sunday:
                floats.update({
                    self.sat_after_nativity:    FloatIndex.SatAfterNativityBeforeTheophany,
                    self.nativity+1:            FloatIndex.SunAfterNativityMonday,
                    self.sun_before_theophany:  FloatIndex.SunBeforeTheophany,
                    self.theophany-1:           FloatIndex.TheophanyEve,
                })
            case Weekday.Monday:
                floats.update({
                    self.sat_after_nativity:    FloatIndex.SatAfterNativityBeforeTheophany,
                    self.sun_after_nativity:    FloatIndex.SunAfterNativitiy,
                    self.theophany-5:           FloatIndex.SatBeforeTheophanyJan,
                    self.theophany-1:           FloatIndex.TheophanyEve,
                })
            case Weekday.Tuesday:
                floats.update({
                    self.sat_after_nativity:    FloatIndex.SatAfterNativity,
                    self.sun_after_nativity:    FloatIndex.SunAfterNativitiy,
                    self.sat_before_theophany:  FloatIndex.SatBeforeTheophanyEve,
                    self.theophany-5:           FloatIndex.SatBeforeTheophanyJan,
                    self.theophany-2:           FloatIndex.RoyalHoursTheophanyFriday,
                })
            case Weekday.Wednesday:
                floats.update({
                    self.sat_after_nativity:    FloatIndex.SatAfterNativity,
                    self.sun_after_nativity:    FloatIndex.SunAfterNativitiy,
                    self.sat_before_theophany:  FloatIndex.SatBeforeTheophany,
                    self.sun_before_theophany:  FloatIndex.SunBeforeTheophanyEve,
                    self.theophany-3:           FloatIndex.RoyalHoursTheophanyFriday,
                })
            case Weekday.Thursday | Weekday.Friday:
                floats.update({
                    self.sat_after_nativity:    FloatIndex.SatAfterNativity,
                    self.sun_after_nativity:    FloatIndex.SunAfterNativitiy,
                    self.sat_before_theophany:  FloatIndex.SatBeforeTheophany,
                    self.sun_before_theophany:  FloatIndex.SunBeforeTheophany,
                    self.theophany-1:           FloatIndex.TheophanyEve,
                })
            case Weekday.Saturday:
                floats.update({
                    self.nativity+6:            FloatIndex.SatAfterNativityFriday,
                    self.sun_after_nativity:    FloatIndex.SunAfterNativitiy,
                    self.sat_before_theophany:  FloatIndex.SatBeforeTheophany,
                    self.sun_before_theophany:  FloatIndex.SunBeforeTheophany,
                    self.theophany-1:           FloatIndex.TheophanyEve,
                })

        # Floats around Annunciation
        match datetools.weekday_from_pdist(self.annunciation):
            case Weekday.Saturday:
                floats[self.annunciation-1]     = FloatIndex.AnnunciationParemFriday
                floats[self.annunciation]       = FloatIndex.AnnunciationSat
            case Weekday.Sunday:
                floats[self.annunciation]       = FloatIndex.AnnunciationSun
            case Weekday.Monday:
                floats[self.annunciation]       = FloatIndex.AnnunciationMon
            case _:
                floats[self.annunciation-1]     = FloatIndex.AnnunciationParemEve
                floats[self.annunciation]       = FloatIndex.AnnunciationWeekday

        return floats
