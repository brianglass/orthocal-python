import logging

from datetime import date
from functools import lru_cache

from django.utils.functional import cached_property
from jdcal import jd2gcal

from .. import datetools
from ..datetools import Calendar, Weekday, FloatIndex

logger = logging.getLogger(__name__)


class ByzantineYear:
    """Representation of a liturgical year.

    While the literal Church year begins on September 1, for the purposes of
    computing feasts, fasts, and readings, it is more practical to represent
    the year with Pascha as its locus. For that reason, this Year class
    represents the period from one Zacchaeus Sunday (77 days before Pascha)
    to the next.

    This base class holds everything that is common to both the Slavic and
    Greek liturgical traditions, both of which descend from the shared
    Byzantine rite: fixed-calendar-date anchors (Elevation, Nativity,
    Theophany, Annunciation, etc.), the floating-feast table, fasting
    periods, and paremia scheduling. This also includes the Lukan jump
    itself (`lukan_jump`, `lukan_jump_threshold`, `first_sun_luke`) --
    confirmed empirically identical between the two traditions (see
    `GreekYear`'s docstring) and not a point of divergence. What genuinely
    differs is how each tradition handles the numbered Sunday Gospels
    displaced by that jump: `reserves` defaults to empty here (correct for
    Greek, which has no use for saved/reserved gospels) and is overridden
    only by `SlavicYear`, which actually saves and replays them. See
    `SlavicYear` and `GreekYear`.
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

        eighteenth_monday = 49+1 + 7*17  # Pentecost+1 + 17 weeks
        mon_after_elevation = self.sun_after_elevation + 1
        return eighteenth_monday - mon_after_elevation

    @cached_property
    def lukan_jump_threshold(self):
        """The pdist after which the Lukan jump shift applies to the Gospel cycle."""
        return self.sun_after_elevation

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

        The base implementation is empty; only SlavicYear overrides it --
        GreekYear has no use for saved/reserved Sunday gospels (see its
        class docstring) and doesn't need to know this mechanism exists."""
        return []

    def sunday_gospel_override(self, pdist):
        """Override the Gospel pdist for a specific Sunday, or None to use the
        default gospel_pdist computation. Return False (not None) to mean "no
        daily-cycle Gospel/Epistle at all today" -- reserved for the rare
        case where a Sunday's regular content is genuinely never read that
        year (as opposed to merely coinciding with a floating feast, which is
        not a case for suppression -- see Day.gospel_pdist).

        The base implementation is a no-op; only GreekYear overrides it."""
        return None

    def sunday_epistle_override(self, pdist):
        """Like sunday_gospel_override, but for the Epistle -- these do not
        always coincide for GreekYear (see its override for why). The base
        implementation is a no-op; only GreekYear overrides it."""
        return None

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

    @cached_property
    def nativity_fast(self):
        start, end = date(self.year, 11, 15), date(self.year, 12, 24)

        if self.calendar == Calendar.Julian:
            start_jdn, end_jdn = datetools.julian_to_jdn(start), datetools.julian_to_jdn(end)
            start_y, start_m, start_d, _ = jd2gcal(start_jdn, 0)
            end_y, end_m, end_d, _ = jd2gcal(end_jdn, 0)
            return date(start_y, start_m, start_d), date(end_y, end_m, end_d)
        else:
            return start, end

    @cached_property
    def apostles_fast(self):
        # The Apostles fast begins on the Monday following All Saints
        start, end = jd2gcal(self.pascha + 57, 0), jd2gcal(self.peter_and_paul, 0)

        if self.calendar == Calendar.Julian:
            return (datetools.gregorian_to_julian(*start), datetools.gregorian_to_julian(*end))
        else:
            return (date(*start), date(*end))


@lru_cache
class SlavicYear(ByzantineYear):
    """The Slavic/Russian tradition's handling of the Matthew-to-Luke Gospel transition.

    The reading for the Monday of the 18th week after Pentecost, Luke
    3.19-22 (Lukan pericope 10), is read on the Monday after the Sunday
    after the Elevation of the Cross, regardless of how many weeks of
    Matthew that leaves unread -- those are simply never read that year.
    Sunday Gospels that get displaced by the Festal cycle between
    Forefathers Sunday and Theophany, and any Sundays of Luke skipped by the
    jump itself, are saved as `reserves` and read on the Sundays between
    Theophany and the Triodion.

    See https://www.orthodox.net/ustav/lukan-jump.html
    """

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


@lru_cache
class GreekYear(ByzantineYear):
    """The Byzantine-Greek tradition's handling of the Matthew-to-Luke Gospel transition.

    The weekday jump itself is identical to SlavicYear -- confirmed
    empirically (2026-09-21, "Monday of the 1st week [of Luke]", reads Luke
    3.19-22, matching raw pdist 169 exactly) and stated explicitly in the
    byzcath.org "Lukan Jump" thread: "the St. Luke period begins on the
    Monday after the Sunday which follows the Exaltation." The same thread
    notes the Russian Church reinstated this identical automatic-jump rule
    (on Professor Uspensky's advice), so the jump itself is not a point of
    difference between the traditions today.

    What *does* differ is which numbered "Gospel of Luke" each Sunday reads.
    Naive week-counting from the jump breaks down because a fixed set of
    calendar-date windows is reserved, by long-standing convention, for
    specific numbered readings regardless of the naive week count -- and a
    small set of higher-rank Apostle/Evangelist feasts (Luke, Matthew,
    Andrew) can claim a Sunday outright, permanently dropping whatever
    number was due that day with no makeup later. Both tables below are
    quoted verbatim from the byzcath.org "Lukan Jump" thread (citing "the
    Ustav list archive") and were cross-validated against every Sunday in
    the antiochian.org official liturgical charts for 2023, 2024, 2025, and
    2026 -- 100% match, including every reserved-window and Apostle-override
    case encountered in those four years.

    See https://www.orthodox.net/ustav/lukan-jump.html
    and https://www.byzcath.org/forums/ubbthreads.php/topics/133274/lukan-jump
    """

    # "many of the Sunday Gospels between October and December are reserved
    # for a special date as follows: to be read on the Sunday which falls
    # between: Oct 11 and 17, the 4th Gospel of St Luke; Oct 30 and Nov 5,
    # the 5th Gospel of St Luke; Nov 24 and 30, the 13th Gospel of St Luke;
    # Dec 1 and 3, the 14th Gospel of St Luke; Dec 4 and 10, the 10th Gospel
    # of St Luke; Dec 11 and 17, the 11th Gospel of St Luke."
    _LUKAN_RESERVED_WINDOWS = (
        # (start_month, start_day, end_month, end_day, forced_number)
        (10, 11, 10, 17, 4),
        (10, 30, 11, 5, 5),
        (11, 24, 11, 30, 13),
        (12, 1, 12, 3, 14),
        (12, 4, 12, 10, 10),
        (12, 11, 12, 17, 11),
    )

    # Higher-rank Apostle/Evangelist feasts that, when they land on a Sunday
    # in this range, claim it outright -- the Lukan number due that day
    # (whether from a reserved window or the plain sequence) is consumed but
    # never displayed, and is not made up on a later Sunday. Confirmed against
    # all four validation years: 2026 (Luke, Oct 18), 2025 (Matthew, Nov 16;
    # Andrew, Nov 30). Lower-rank saints landing on these same Sundays (e.g.
    # Demetrius, Nektarios, Nicholas, Cosmas & Damian) do not have this
    # effect -- their day simply combines with the numbered Sunday.
    _LUKAN_OVERRIDE_FEASTS = (
        (10, 18),  # Apostle and Evangelist Luke
        (11, 16),  # Apostle Matthew
        (11, 30),  # Apostle Andrew, the First-Called
    )

    # The byzcath.org "Lukan Jump" thread (quoted in the original version of
    # this comment) only enumerated cases up to "five Sundays between
    # Theophany and the Triodion" and was never checked against a real n=5
    # year. Rebuilt from scratch against real antiochian.org data across 4
    # independent years (2022=n4, 2018=n5, 2020=n6, 2023=n7 -- see
    # docs/greek-weekday-drift.md for the full derivation) -- this revealed
    # the n=5 entry above was simply wrong (real 2018 data: 12th, 15th,
    # *16th* of Matthew, 17th of Matthew/"Canaanite Woman" -- not 12th,
    # 14th, 15th, 17th), and confirmed a clean, monotonic insertion pattern
    # building up from n=3: each larger n adds exactly one entry, always in
    # the same relative position, never simply extending forward:
    #   3: 12th, 15th
    #   4: 12th, 15th, +Canaanite Woman (17th of Matthew)
    #   5: 12th, 15th, +16th of Matthew, Canaanite Woman
    #   6: 12th, +14th, 15th, 16th of Matthew, Canaanite Woman
    #
    # The trailing "Canaanite Woman"/"15th of Luke"/"25th of Luke" entry --
    # i.e. whatever each row's last element would be -- is *never actually
    # reachable through this table* and is omitted below. By construction,
    # the last entry in an n-row sequence always lands exactly at pdist -77
    # (Zacchaeus/Canaanite Woman Sunday, 11 weeks before Pascha -- the same
    # fixed, Pascha-anchored occasion in both traditions per Wikipedia's
    # Paschal cycle article), and Day always resolves a real calendar date
    # at that exact pdist via the *following* GreekYear instance rather
    # than this one (confirmed via Day(2018,1,21), a real n=2 year: it
    # picks GreekYear(2018), landing on pdist -77, not GreekYear(2017)
    # where this table's n=2 entry would have applied). See
    # canaanite_woman_applies, which is what actually governs that
    # position, checked directly in sunday_gospel_override before this
    # table is ever consulted. This is confirmed correct for every
    # magnitude tested (n=2 through 7), not just the n>=4 cases where
    # Canaanite Woman genuinely applies -- for n=2/3 canaanite_woman_applies
    # is False and the position simply falls through to the shared
    # common/slavic table's own content there, unaffected by whatever this
    # table's now-removed trailing entry used to claim.
    #
    # n=7 is handled separately -- see theophany_interpolation below --
    # because of the Leavetaking-of-Theophany-falls-on-Sunday special case.
    _THEOPHANY_INTERPOLATION = {
        0: (),
        1: (),
        2: (),
        3: ((None, 12),),
        4: ((None, 12), (None, 15)),
        5: ((None, 12), (None, 15), ('matthew', 16)),
        6: ((None, 12), (None, 14), (None, 15), ('matthew', 16)),
    }

    @staticmethod
    def _lukan_sunday_target(n):
        """Raw pdist storing the nth "Gospel of Luke" (1st = Luke 5.1-11 at pdist 175)."""
        return 168 + 7*n

    @staticmethod
    def _matthew_sunday_target(n):
        """Raw pdist storing the nth "Gospel of Matthew" (Sunday-numbered, unshifted)."""
        return 49 + 7*n

    @cached_property
    def lukan_sunday_numbers(self):
        """Map each Sunday's pdist, from first_sun_luke through forefathers,
        to its assigned "nth Gospel of Luke" number. Sundays fully claimed by
        an override feast are omitted entirely (see _LUKAN_OVERRIDE_FEASTS)."""

        windows = [
            (self.date_to_pdist(m1, d1, self.year), self.date_to_pdist(m2, d2, self.year), n)
            for m1, d1, m2, d2, n in self._LUKAN_RESERVED_WINDOWS
        ]
        reserved_numbers = {n for _, _, n in windows}
        override_pdists = {self.date_to_pdist(m, d, self.year) for m, d in self._LUKAN_OVERRIDE_FEASTS}

        result = {}
        next_seq = 1
        pdist = self.first_sun_luke
        while pdist <= self.forefathers:
            forced = next((n for start, end, n in windows if start <= pdist <= end), None)
            if forced is not None:
                assigned = forced
            else:
                while next_seq in reserved_numbers:
                    next_seq += 1
                assigned = next_seq
                next_seq += 1

            if pdist not in override_pdists:
                result[pdist] = assigned

            pdist += 7

        return result

    @cached_property
    def triodion_start(self):
        """pdist of the Sunday of the Publican and Pharisee (Triodion begins)."""
        return self.next_pascha - self.pascha - 70

    @cached_property
    def greek_extra_sundays(self):
        """Number of Sundays needing content between Theophany and Triodion,
        counting the Sunday after Theophany itself. Unlike SlavicYear's
        extra_sundays, this counts straight through to the Triodion with no
        Zacchaeus Sunday buffer -- confirmed empirically: for a small enough
        gap (regular_extra_sundays <= 3), Greek practice does not observe
        Zacchaeus/Canaanite Woman Sunday as its own occasion at all (e.g.
        2026-01-25, the Sunday immediately before Triodion begins that year,
        reads plainly as "15th Sunday of Luke," not "Canaanite Woman") --
        see canaanite_woman_applies for the larger-gap case, where it is."""
        return (self.triodion_start - self.sun_after_theophany) // 7

    @cached_property
    def regular_extra_sundays(self):
        """greek_extra_sundays, adjusted for the Leavetaking-of-Theophany-
        falls-on-Sunday special case (see theophany_interpolation) -- the
        count that actually indexes _THEOPHANY_INTERPOLATION and determines
        whether canaanite_woman_applies."""
        n = self.greek_extra_sundays
        if datetools.weekday_from_pdist(self.theophany + 8) == Weekday.Sunday:
            n -= 1
        return n

    @cached_property
    def theophany_interpolation(self):
        """Map the pdist of each interpolated Sunday (after the Sunday after
        Theophany itself, which needs no override -- see Day.gospel_pdist's
        has_daily_readings guard) to its (book, n) assignment.

        Leavetaking of Theophany (theophany+8, always a fixed calendar date)
        structurally always lands exactly on this table's first slot
        (sun_after_theophany + 7) whenever it happens to fall on a Sunday,
        since both are always exactly one week after sun_after_theophany.
        When that happens, it preempts whatever the plain numbered sequence
        would otherwise show there, and the *remaining* slots use the same
        table entry as if greek_extra_sundays were one smaller (that's what
        regular_extra_sundays computes) -- confirmed against 2023 (n=7,
        Leavetaking-on-Sunday): the entries after the Leavetaking slot
        exactly match n=6's full sequence. Not confirmed against any other
        magnitude (the disambiguating case, 2034, was outside every
        reachable source's reliable window), but well-motivated by the
        structure rather than a blind guess.

        Note this table never actually covers the *last* Sunday before
        Triodion (Zacchaeus/Canaanite Woman) -- see canaanite_woman_applies
        for why and how that one is handled separately.
        """

        n = self.regular_extra_sundays
        leading = ()
        if n != self.greek_extra_sundays:
            leading = (('direct', FloatIndex.SunAfterTheophany),)

        entries = leading + self._THEOPHANY_INTERPOLATION.get(n, ())
        result = {}
        pdist = self.sun_after_theophany + 7
        for book, val in entries:
            result[pdist] = (book, val)
            pdist += 7
        return result

    @cached_property
    def canaanite_woman_applies(self):
        """Whether pdist -77 (Zacchaeus/Canaanite Woman Sunday, 11 weeks
        before Pascha -- confirmed via Wikipedia's Paschal cycle article to
        be the same fixed, Pascha-anchored occasion in both traditions,
        just named differently) should show the Greek-specific "Canaanite
        Woman" content (Matt 15:21-28) instead of falling through to the
        shared common/slavic table's own Zacchaeus content there.

        This can't be decided from this instance's own
        theophany_interpolation: Day always resolves a real calendar date
        at pdist -77 via the *following* GreekYear instance (whichever
        Pascha is closer -- confirmed via Day(2026,1,25), which picks
        GreekYear(2026) rather than GreekYear(2025) even though the latter
        is what actually computed the "15th Sunday of Luke" assignment for
        that date). So this must be computed by checking the *preceding*
        year's (whose winter actually leads into this Sunday)
        regular_extra_sundays instead: whenever that gap was large enough
        to exhaust the plain Luke/Matthew numbering (n>=4), Canaanite Woman
        is what actually shows there; for a small gap (n<=3) the shared
        table's plain Zacchaeus content is correct as-is.
        """
        preceding = GreekYear(self.year - 1)
        return preceding.regular_extra_sundays >= 4

    def sunday_gospel_override(self, pdist):
        if pdist == -77 and self.canaanite_woman_applies:
            return self._matthew_sunday_target(17)

        if self.first_sun_luke <= pdist <= self.forefathers:
            n = self.lukan_sunday_numbers.get(pdist)
            if n is None:
                # Claimed outright by a higher-rank Apostle feast; no daily-
                # cycle Gospel/Epistle today at all -- see class docstring.
                return False
            return self._lukan_sunday_target(n)

        if (entry := self.theophany_interpolation.get(pdist)) is not None:
            book, val = entry
            if book == 'matthew':
                return self._matthew_sunday_target(val)
            if book == 'direct':
                return val
            return self._lukan_sunday_target(val)

        return None

    def sunday_epistle_override(self, pdist):
        """Like sunday_gospel_override, but for the Epistle -- these do NOT
        always coincide. Confirmed against real antiochian.org data across
        multiple independent years: on the *ordinary* numbered Sundays of
        Luke (first_sun_luke..forefathers, the natural Oct-Dec progression),
        the Epistle keeps following its own ordinary continuous-cycle
        position -- only the Gospel is subject to the numbered-Sunday
        scheme there (e.g. 1st Sunday of Luke reads whatever Epistle the
        plain pdist gives, `2 Cor 4:6-15` in 2022 vs `2 Cor 6:16-7:1` in
        2026 -- never the same target both years, so it can't be paired to
        the Gospel's number). The Canaanite Woman (-77) and post-Theophany
        interpolation cases DO pair the Epistle with the same numbered
        target as the Gospel -- confirmed separately for each (4/5 years
        for Canaanite Woman; 2022-2025 for the interpolation window's own
        numbered targets, modulo a higher-rank saint occasionally
        displacing the whole Sunday, which this project already shows
        additively elsewhere rather than suppressing -- see the class
        docstring's `_LUKAN_OVERRIDE_FEASTS` note and existing site
        precedent for combined readings)."""

        if self.first_sun_luke <= pdist <= self.forefathers:
            n = self.lukan_sunday_numbers.get(pdist)
            # Still suppressed outright when an Apostle feast claims the day;
            # otherwise no override -- fall through to the plain pdist.
            return False if n is None else None

        return self.sunday_gospel_override(pdist)
