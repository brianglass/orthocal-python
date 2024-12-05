import logging

from datetime import date, timedelta

from asgiref.sync import async_to_sync
from django.db.models import Q
from django.utils.functional import cached_property

from .. import datetools, models
from ..datetools import Calendar, Weekday, FastLevels, FastLevelDesc, FastExceptions, FeastLevels, FloatIndex
from commemorations.models import Commemoration

from .year import Year

logger = logging.getLogger(__name__)


class Day:
    """Representation of a liturgical day.

    This class is a composite of feasts, fasts, scripture readings, and lives
    of the saints from both the Paschal cycle and the festal cycle.
    """

    def __init__(self, year, month, day, calendar=Calendar.Gregorian, language='en'):
        self.gregorian_date = date(year, month, day)

        if calendar == Calendar.Gregorian:
            dt = self.gregorian_date
            pdist, pyear = datetools.compute_pascha_distance(dt)
            self.jdn = datetools.gregorian_to_jdn(dt)
        else:
            dt = datetools.gregorian_to_julian(year, month, day)
            pdist, pyear = datetools.compute_julian_pascha_distance(dt)
            self.jdn = datetools.julian_to_jdn(dt)

        self.date = dt
        self.year = dt.year
        self.month = dt.month
        self.day = dt.day
        self.pdist = pdist
        self.weekday = datetools.weekday_from_pdist(pdist)
        self.pyear = Year(pyear, calendar)
        self.language = language

    async def ainitialize(self):
        """Do the expensive stuff here to keep it out of the constructor."""

        if not hasattr(self, '_initialized'):
            await self._collect_commemorations()
            await self._add_supplemental_commemorations()
            self._apply_fasting_adjustments()
            self._initialized = True

    initialize = async_to_sync(ainitialize)

    def __str__(self):
        return str(self.date)

    @cached_property
    def summary_title(self):
        """A simplified title that summarizes the day's commemorations."""

        if self.weekday == 0 or -9 < self.pdist < 7:
            if self.titles:
                return '; '.join(self.titles)

        if self.feasts:
            return '; '.join(self.feasts)

        if self.saints:
            return '; '.join(self.minimal_saints)

        if self.titles:
            return '; '.join(self.titles)

    async def _collect_commemorations(self):
        """Fetch the feasts, fasts, and saints and bake them into a composite day."""

        # Select items from the Paschal cycle
        q = Q(pdist=self.pdist)

        # Select floating feasts; These are usually based on the Festal calendar
        if float_index := self.pyear.floats.get(self.pdist):
            q |= Q(pdist=float_index)

        # Select items from the Festal cycle
        q |= Q(month=self.month, day=self.day)

        # Fetch the items from the database
        days = [d async for d in models.Day.objects.filter(q)]

        # Bake the mutliple "days" down into a single composite day.

        self.titles = [title for d in days if (title := d.full_title)]
        self.saints = [saint.strip() for d in days for saint in d.saint.split(';') if saint]
        self.minimal_saints = [d.saint for d in days if d.saint]
        self.feasts = [d.feast_name for d in days if d.feast_name]
        self.service_notes = [d.service_note for d in days if d.service_note]

        self.feast_level = max(d.feast_level for d in days)
        self.fast_level = max(d.fast for d in days)
        self.fast_exception = max(d.fast_exception for d in days)

    async def _add_supplemental_commemorations(self):
        """Add additional commemorations and stories from Abbamoses.com."""

        self.stories = [s async for s in Commemoration.objects.filter(month=self.month, day=self.day)]

        if not self.stories:
            return

        commemorations = self.titles + self.feasts + self.saints

        # Add unmatched stories to the list of commemorations
        self.saints.extend(
            s.title
            for s in self.stories
            if not s.alt_title or not any(s.alt_title in c for c in commemorations)
        )
        
    def _apply_fasting_adjustments(self):
        # Adjust for fast free days
        if self.fast_exception == 11:
            self.fast_level = FastLevels.NoFast
            return

        # Are we in the Apostles fast? This can't be gleaned from the database
        # because the feast of Sts. Peter and Paul is part of the Festal cycle,
        # but the beginning of this fast is defined by the Paschal cycle.
        if 56 < self.pdist < self.pyear.peter_and_paul:
            self.fast_level = FastLevels.ApostlesFast
            if self.pdist == 57:
                self.service_notes.append("Beginning of Apostles' Fast")

        match self.fast_level:
            case FastLevels.LentenFast:
                # Remove fish for minor feast days in Lent
                if self.fast_exception == 2:
                    self.fast_exception -= 1
            case FastLevels.DormitionFast:
                # Allow wine and oil on weekends during the Dormition fast
                if self.weekday in (Weekday.Sunday, Weekday.Saturday) and self.fast_exception == 0:
                    self.fast_exception += 1
            case FastLevels.ApostlesFast | FastLevels.NativityFast:
                match self.weekday:
                    case Weekday.Tuesday | Weekday.Thursday:
                        if self.fast_exception == 0:
                            self.fast_exception += 1
                    case Weekday.Wednesday | Weekday.Friday:
                        if self.feast_level < 4 and self.fast_exception > 1:
                            self.fast_exception = 1
                    case Weekday.Sunday | Weekday.Saturday:
                        self.fast_exception = 2

                # Disallow fish for the week before Nativity
                if self.pyear.nativity-6 < self.pdist < self.pyear.nativity-1 and self.fast_exception > 1:
                    self.fast_exception = 1

        # The days before Nativity and Theophany are wine and oil days
        if self.pdist in (self.pyear.nativity-1, self.pyear.theophany-1) and self.weekday in (Weekday.Sunday, Weekday.Saturday):
            self.fast_exception = 1

    @cached_property
    def fast_level_desc(self):
        return FastLevelDesc[self.fast_level]

    @cached_property
    def fast_exception_desc(self):
        return FastExceptions[self.fast_exception]

    @cached_property
    def feast_level_desc(self):
        return FeastLevels[self.feast_level]

    @cached_property
    def has_no_memorial(self):
        """True if Memorial Saturday is cancelled."""
        return self.pdist in (-36, -29, -22) and self.month == 3 and self.day in (9, 24, 25, 26)

    @cached_property
    def has_matins_gospel(self):
        """True if there could be a non-Eothinon Gospel reading for Matins, otherwise False."""

        if self.weekday != Weekday.Sunday:
            return True

        if -8 < self.pdist < 50:
            return False

        if self.feast_level < 7:
            return False

        return True

    @cached_property
    def preceding_pdist(self):
        """The number of days from the Pascha preceding this day to this day."""
        return self.pdist if self.pdist >= 0 else self.jdn - self.pyear.previous_pascha

    @cached_property
    def tone(self):
        """The proper tone for this day."""

        # See https://mci.archpitt.org/liturgy/EightTones.html

        # The last day of Lent is on the Friday before Lazarus Saturday. From
        # Lazarus Saturday until Holy Saturday, the octoechoes are not employed.
        if -9 < self.pdist < 0:
            return 0

        # Bright week is different. We cycle through the tones one per day, skipping tone 7.
        # Tone 7 is said to be too somber for bright week.
        if 0 <= self.pdist < 7:
            bright_tones = 1, 2, 3, 4, 5, 6, 8
            return bright_tones[self.pdist]

        # TODO: check for great feasts and set tone to 0 for them
        pass

        # We start the cycle with Thomas Sunday, which has pdist == 7 and so is
        # the 1st Sunday (7 // 7 == 1).  The mod cycle is 0 origin, so 0-7 for
        # mod 8. We add 1 to shift it to 1-8.
        nth_sunday = self.preceding_pdist // 7
        return (nth_sunday-1) % 8 + 1

    @cached_property
    def eothinon_gospel(self):
        """The number of the Sunday Eothinon Gospel if relevant, otherwise None."""

        if self.weekday != Weekday.Sunday:
            return None

        # There are no matins gospels from Holy Week until Pentecost
        if -8 < self.pdist < 50:
            return None

        # high ranking feasts preempt the Eothinon
        if self.feast_level >= 7:
            return None

        # Compute the number of the correct Eothinon Gospel.  We cycle through
        # the 11 gospels starting on the 1st Sunday after Pentecost.
        nth_sunday = (self.preceding_pdist - 49) // 7
        return (nth_sunday - 1) % 11 + 1

    @cached_property
    def has_no_paremias(self):
        """True if the paremias for this day have been moved."""
        return self.pyear.has_no_paremias(self.pdist)

    @cached_property
    def has_moved_paremias(self):
        """True if this day has moved paremias for the succeeding day."""
        return self.pyear.has_moved_paremias(self.pdist)

    async def aget_readings(self, fetch_content=False):
        """Return a list of lectionary readings."""

        # Return cached readings if we already have them

        if hasattr(self, 'readings'):
            if fetch_content:
                for reading in self.readings:
                    await reading.pericope.aget_passage(language=self.language)

            return self.readings

        # Select readings based on the Paschal cycle. These include the moveable
        # feasts.

        query = Q(pdist=self.pdist) & ~Q(source='Gospel') & ~Q(source='Epistle')

        if self.gospel_pdist is not None:
            if self.has_no_memorial:
                query |= Q(pdist=self.gospel_pdist, source='Gospel') & ~Q(desc='Departed')
            else:
                query |= Q(pdist=self.gospel_pdist, source='Gospel')

        if self.epistle_pdist is not None:
            if self.has_no_memorial:
                query |= Q(pdist=self.epistle_pdist, source='Epistle') & ~Q(desc='Departed')
            else:
                query |= Q(pdist=self.epistle_pdist, source='Epistle')

        # Select readings for floating feasts. Most of these are based on the
        # Festal cycle. That is, their occurrence is not related to the date of Pascha.

        if float_index := self.pyear.floats.get(self.pdist):
            query |= Q(pdist=float_index)

        # Add Matins Eothinon gospel. This is a cycle of 11 readings sync'd
        # with the Paschal cycle.

        if self.eothinon_gospel:
            query |= Q(pdist=self.eothinon_gospel + 700)

        # Select readings based on the Festal cycle. These are the fixed feasts.

        if self.has_moved_paremias:
            # If paremias have been moved, fetch from the following day
            dt = self.date + timedelta(days=1)
            query |= Q(month=dt.month, day=dt.day, source='Vespers')

        subquery = Q(month=self.month, day=self.day)
        if not self.has_matins_gospel:
            subquery &= ~Q(source='Matins Gospel')

        if self.has_no_paremias:
            subquery &= ~Q(source='Vespers')

        if self.month == 3 and self.day == 26 and self.weekday in [Weekday.Monday, Weekday.Tuesday, Weekday.Thursday]:
            # There are no readings for leavetaking of Annunciation on a non-liturgy day
            subquery &= ~Q(desc='Theotokos')

        query |= subquery

        # Generate the list of readings

        # Do select_related to avoid later synchronous foreign key lookup
        queryset = models.Reading.objects.filter(query).select_related('pericope')

        self.readings = []
        async for reading in queryset.order_by('ordering'):
            if fetch_content:
                await reading.pericope.aget_passage(language=self.language)

            if -42 < self.pdist < -7 and self.feast_level < 7 and reading.source == 'Matins Gospel':
                # Place Lenten Matins Gospel at the top
                self.readings.insert(0, reading)
            else:
                self.readings.append(reading)

        return self.readings

    get_readings = async_to_sync(aget_readings)

    async def aget_abbreviated_readings(self, fetch_content=False):
        """Return an abbreviated list of lectionary readings."""

        # Return cached readings if we already have them
        if hasattr(self, 'abbreviated_readings'):
            if fetch_content:
                for reading in self.abbreviated_readings:
                    await reading.pericope.aget_passage(language=self.language)

            return self.abbreviated_readings

        # Pull in the usual items from the Paschal cycle

        # This pulls in the OT readings we do on weekdays in Lent
        query = Q(pdist=self.pdist) & ~Q(source='Gospel') & ~Q(source='Epistle')

        if self.gospel_pdist is not None:
            if self.has_no_memorial:
                query |= Q(pdist=self.gospel_pdist, source='Gospel') & ~Q(desc='Departed')
            else:
                query |= Q(pdist=self.gospel_pdist, source='Gospel')

        if self.epistle_pdist is not None:
            if self.has_no_memorial:
                query |= Q(pdist=self.epistle_pdist, source='Epistle') & ~Q(desc='Departed')
            else:
                query |= Q(pdist=self.epistle_pdist, source='Epistle')

        # Pull in just Epistles and Gospels from the Festal cycle, but not
        # during clean week or Holy week.
        if self.feast_level >= 2 and self.fast_exception != 10:
            subquery = Q(month=self.month, day=self.day, source__in=['Epistle', 'Gospel'])

            if self.month == 3 and self.day == 26 and self.weekday in [Weekday.Monday, Weekday.Tuesday, Weekday.Thursday]:
                # There are no readings for leavetaking of Annunciation on a non-liturgy day
                subquery &= ~Q(desc='Theotokos')

            query |= subquery

        # Add Epistles and Gospels from the floating feasts as well
        if float_index := self.pyear.floats.get(self.pdist):
            query |= Q(pdist=float_index, source__in=['Epistle', 'Gospel'])

        # Generate the list of readings.
        # Do select_related to avoid later synchronous foreign key lookup.
        queryset = models.Reading.objects.filter(query).select_related('pericope')
        readings = [reading async for reading in queryset.order_by('ordering')]

        # Include only the first Epistle and Gospel if we have them.
        sources = [r.source for r in readings]
        if 'Epistle' in sources and 'Gospel' in sources:
            epistle = readings[start := sources.index('Epistle')]
            try:
                # Attempt to fetch the gospel that comes after the selected epistle
                gospel = readings[sources.index('Gospel', start)]
            except ValueError:
                # If this goes wrong, we'll take any epistle. This shouldn't
                # happen, but there are some epistles out of order in the
                # database. This should be fixed in the data, but for now we'll
                # be forgiving.
                gospel = readings[sources.index('Gospel')]

            readings = [epistle, gospel]

        if fetch_content:
            for reading in readings:
                await reading.pericope.aget_passage(language=self.language)

        self.abbreviated_readings = readings
        return readings

    get_abbreviated_readings = async_to_sync(aget_abbreviated_readings)

    @cached_property
    def abbreviated_reading_indices(self):
        if not hasattr(self, 'readings') or not hasattr(self, 'abbreviated_readings'):
            raise RuntimeError('get_readings and get_abbreviated_readings must be called before abbreviated_reading_indices')

        texts = [r.pericope.display for r in self.readings]
        return [texts.index(r.pericope.display) for r in self.abbreviated_readings]

    @cached_property
    def has_daily_readings(self):
        """True if daily readings are not suppressed for this day."""
        return self.pyear.has_daily_readings(self.pdist)

    @cached_property
    def epistle_pdist(self):
        """Adjusted pdist for the epistle.

        This needs to jump into the following year's Paschal cycle. The Paschal
        cycle is shorter than the full 365 days in a year and we run out of
        readings at the end of the range.

        models.Reading has records as far back as pdist == -133
        """

        if not self.has_daily_readings:
            return None

        if self.pdist == 49 + 29*7:  # Pentecost + 29 weeks
            # 29th Sunday after Pentecost
            return self.pyear.forefathers

        if self.pdist >= 49 + 32*7:  # Pentecost + 32 weeks
            # Starting on the 32nd Sunday after Pentecost, we wrap around to
            # the beginning of the next year.
            return self.jdn - self.pyear.next_pascha

        return self.pdist

    @cached_property
    def gospel_pdist(self):
        """Adjusted pdist for the Gospel.

        This needs to be adjusted for the Lukan jump.

        It will also need to jump into the following year's Paschal cycle. The
        Paschal cycle is shorter than the full 365 days in a year and we run
        out of readings at the end of the range.

        models.Reading has records as far back as pdist == -133
        """

        if not self.has_daily_readings:
            return None

        if self.pdist == self.pyear.first_sun_luke + 10*7:
            # On the 11th Sunday of Luke we commemorate the forefathers of the
            # Lord. We read the Gospel that is assigned to Forefathers Sunday
            # from the Paschal cycle. On Forefathers Sunday, we read the Gospel
            # pulled from the Festal cycle for that day (from self.pyear.floats).
            #
            # This might not happen in the Greek lectionary. This reading seems
            # to be included in the reserves for the Greeks.
            return self.pyear.forefathers + self.pyear.lukan_jump

        if self.weekday == Weekday.Sunday and self.pdist > self.pyear.sun_after_theophany and self.pyear.extra_sundays > 1:
            # On Sundays after Theophany, use the Gospels left unread after the Lukan jump
            i = (self.pdist - self.pyear.sun_after_theophany) // 7
            return self.pyear.reserves[i-1]

        if self.pdist > self.pyear.sat_before_theophany:
            # We jump into the paschal cycle for the upcoming Pascha.
            # Some sources say this jump should happen after the 13th week of Luke
            return self.jdn - self.pyear.next_pascha

        if self.pdist > self.pyear.sun_after_elevation:
            return self.pdist + self.pyear.lukan_jump

        return self.pdist
