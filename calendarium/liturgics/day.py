import logging

from datetime import date, timedelta

from asgiref.sync import async_to_sync
from django.db.models import Q
from django.utils.functional import cached_property

from .. import datetools, models
from ..datetools import Calendar, Tradition, Weekday, FastLevels, FastLevelDesc, FastExceptions, FeastLevels, FloatIndex
from commemorations.models import DayCommemoration

from .year import SlavicYear, GreekYear

logger = logging.getLogger(__name__)

_YEAR_CLASSES = {
    Tradition.Slavic: SlavicYear,
    Tradition.Greek: GreekYear,
}


def _prefer_tradition(rows, tradition):
    """Resolve a mixed common/tradition-specific row list down to one row per slot.

    Rows tagged for the requested tradition take precedence over the shared
    'common' row for the same (pdist, month, day, source, ordering, desc)
    slot; this is symmetric for both traditions -- neither is privileged.
    """

    kept = []
    slot_index = {}

    for row in rows:
        if row.tradition not in (tradition, 'common'):
            continue

        slot = (row.pdist, row.month, row.day, row.source, row.ordering, row.desc)

        if slot in slot_index:
            if row.tradition != 'common':
                kept[slot_index[slot]] = row
        else:
            slot_index[slot] = len(kept)
            kept.append(row)

    return kept


def _speech_worthy(dc):
    """Should the Alexa skill (alexa/speech.py) say this commemoration's name?

    Excludes only the story-less tradition='greek' overlay -- the bulk
    antiochian.org-harvested commemorations added without a story (see
    docs/saint-model-refactor.md). Everything else speaks regardless of
    whether it has a story, matching this project's behavior before that
    overlay existed."""

    return bool(dc.story) or dc.tradition != 'greek'


def _prefer_tradition_days(rows, tradition):
    """Like _prefer_tradition, but for Day rows, which have no
    source/ordering/desc -- the slot is just (pdist, month, day)."""

    kept = []
    slot_index = {}

    for row in rows:
        if row.tradition not in (tradition, 'common'):
            continue

        slot = (row.pdist, row.month, row.day)

        if slot in slot_index:
            if row.tradition != 'common':
                kept[slot_index[slot]] = row
        else:
            slot_index[slot] = len(kept)
            kept.append(row)

    return kept


class Day:
    """Representation of a liturgical day.

    This class is a composite of feasts, fasts, scripture readings, and lives
    of the saints from both the Paschal cycle and the festal cycle.

    Constructing `Day(..., tradition=...)` actually returns a `SlavicDay` or
    `GreekDay` instance (see `__new__` below) -- the two traditions' fasting
    rules diverge enough (see docs/greek-fasting.md) that each owns its own
    concrete `_apply_fasting_adjustments`, mirroring the `SlavicYear`/
    `GreekYear` split in `year.py`. Everything else about a liturgical day is
    shared and lives here in the base class.
    """

    def __new__(cls, year, month, day, calendar=Calendar.Gregorian, tradition=Tradition.Slavic, language='en', translation=None):
        if cls is Day:
            cls = _DAY_CLASSES[tradition]
        return super().__new__(cls)

    def __init__(self, year, month, day, calendar=Calendar.Gregorian, tradition=Tradition.Slavic, language='en', translation=None):
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
        self.tradition = tradition
        self.calendar = calendar
        self.pyear = _YEAR_CLASSES[tradition](pyear, calendar)
        self.language = language
        self.translation = translation

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
    def translation_label(self):
        """Human-readable label for the Bible translation actually in effect
        -- resolves the per-language default the same way VerseManager does,
        since self.translation is often None (meaning "use the default")
        rather than always holding a concrete value."""

        from bible.models import DEFAULT_TRANSLATIONS

        return datetools.TRANSLATION_LABELS[self.translation or DEFAULT_TRANSLATIONS[self.language]]

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

        return ''

    async def _collect_commemorations(self):
        """Fetch the feasts, fasts, and saints and bake them into a composite day.

        Fetches every Day row matching this slot regardless of tradition
        tag, not just the ones tagged for self.tradition/common -- feast-
        level facts (feast_level/fast/fast_exception/feast_name/titles/
        service_notes) still come only from whichever single row wins via
        _prefer_tradition_days (a tradition-specific row is a genuine
        whole-day replacement for those facts, e.g. Greek observing a
        lower/zero feast_level on a day Slavic elevates). But the full,
        untradition-filtered id list is also kept (self._commemoration_day_ids)
        for _add_supplemental_commemorations, since a saint can be shared
        across traditions via its own DayCommemoration.tradition tag even
        when it happens to be attached to a Day row tagged for a different
        tradition than the one requesting it -- see
        docs/saint-model-refactor.md, Stage 9, for why conflating these two
        concerns (retagging the whole Day row to share saints) caused a
        real fasting-rule regression."""

        # Select items from the Paschal cycle
        q = Q(pdist=self.pdist)

        # Select floating feasts; These are usually based on the Festal calendar
        if float_index := self.pyear.floats.get(self.pdist):
            q |= Q(pdist=float_index)

        # Select items from the Festal cycle
        q |= Q(month=self.month, day=self.day)

        # Fetch every candidate Day row for this slot, regardless of tradition.
        all_days = [d async for d in models.Day.objects.filter(q)]
        self._commemoration_day_ids = [d.id for d in all_days]

        # Bake the multiple "days" down into a single composite day for
        # feast-level facts only -- this part keeps the original
        # tradition-filtered, single-winner selection.
        self.days = _prefer_tradition_days(
            [d for d in all_days if d.tradition in (self.tradition, 'common')],
            self.tradition,
        )

        self.titles = [title for d in self.days if (title := d.full_title)]
        self.feasts = [d.feast_name for d in self.days if d.feast_name]
        self.service_notes = [d.service_note for d in self.days if d.service_note]

        self.feast_level = max(d.feast_level for d in self.days)
        self.fast_level = max(d.fast for d in self.days)
        self.fast_exception = max(d.fast_exception for d in self.days)

    async def _add_supplemental_commemorations(self):
        """Fetch saints and their stories from the Saint/DayCommemoration
        relational model (day_native entries mirror the position they'd
        have had in the old Day.saints list; additive entries are
        commemorations that only ever existed as an abbamoses story with no
        terse Day-side counterpart).

        new_style commemorations (see docs/saint-model-refactor.md, issue
        #146) are modern events recorded against the civil/Gregorian date --
        both Old- and New-Calendar jurisdictions observe them on the same
        real day, unlike the traditional Menaion whose OS dates are
        genuinely offset in Julian mode. In Julian mode self.month/self.day
        are the Julian-shifted label, not the civil date, so these
        commemorations are excluded from whichever shifted day they happen
        to be attached to and re-fetched keyed on self.gregorian_date
        instead. In Gregorian mode self.month/self.day already equal the
        civil date, so no special-casing is needed.

        DayCommemoration.tradition (Stage 6) is a sparse, additive overlay
        at the individual-commemoration level, mirroring Reading's
        common/tradition-specific pattern -- a tradition-specific
        commemoration supplements the day's common ones rather than
        replacing them, which is why the query below filters by tradition
        directly rather than scoping to self.days (the
        _prefer_tradition_days-selected winner). self._commemoration_day_ids
        (Stage 9) deliberately includes every Day row matching this slot
        regardless of tradition tag, so a saint can be shared via its own
        DayCommemoration.tradition even when attached to a Day row tagged
        for a different tradition than the one requesting it -- this is
        what lets Herman's Glorification (attached to a slavic-tagged Aug 9
        row) show for Greek too, without Greek also inheriting Slavic's
        elevated feast_level/fast for that day."""

        query = DayCommemoration.objects.filter(
            day_id__in=self._commemoration_day_ids, tradition__in=(self.tradition, 'common'),
        )
        if self.calendar == Calendar.Julian:
            query = query.exclude(new_style=True)
        commemorations = [dc async for dc in query.order_by('day_id', 'ordering')]

        if self.calendar == Calendar.Julian:
            civil_days = [
                d async for d in models.Day.objects.filter(
                    month=self.gregorian_date.month, day=self.gregorian_date.day,
                )
            ]
            civil_day_ids = [d.id for d in civil_days]
            new_style_commemorations = [
                dc async for dc in
                DayCommemoration.objects.filter(
                    day_id__in=civil_day_ids, new_style=True, tradition__in=(self.tradition, 'common'),
                )
                .order_by('ordering')
            ] if civil_day_ids else []
            commemorations = commemorations + new_style_commemorations
        else:
            new_style_commemorations = []

        winning_day_ids = {d.id for d in self.days}
        day_native_by_day = {}
        additive = []
        for dc in commemorations:
            if self.calendar == Calendar.Julian and dc.new_style:
                # Re-fetched above keyed on the civil date -- always additive
                # here regardless of its original day_native/ordering, since
                # those describe its position on its *native* shifted day,
                # not this civil-anchored view.
                additive.append(dc)
            elif dc.day_native and dc.ordering >= 0:
                day_native_by_day.setdefault(dc.day_id, []).append(dc)
            elif not dc.day_native:
                additive.append(dc)
            elif dc.day_id not in winning_day_ids:
                # day_native with ordering < 0 (feast_name-matched), but its
                # own Day row lost _prefer_tradition_days's preference for
                # this request -- e.g. a saint shared via
                # DayCommemoration.tradition='common' whose day_native
                # entry lives on a different tradition's Day row than the
                # one whose feast_name is actually being shown. Its
                # feast_name isn't surfacing via self.feasts at all in that
                # case, so fall back to showing it plainly rather than
                # silently dropping it.
                additive.append(dc)
            # else: day_native with ordering < 0, and its own Day row is the
            # one whose feast_name is being shown -- already represented via
            # self.feasts; story-only, excluded here.

        self.saints = []
        # Parallel to self.saints, but pairs each title with the story's id
        # (or None) so the readings template can link a commemoration to its
        # full story further down the page, without changing self.saints
        # itself -- it's consumed as plain strings elsewhere (ical.py, RSS).
        self.saint_links = []
        self.spoken_saints = []
        self.minimal_saints = []
        for dcs in day_native_by_day.values():
            # Grouped by whichever Day row the entries originally came from
            # (dc.day_id may not be in self.days -- see the class docstring
            # on _add_supplemental_commemorations), not by self.days, since a
            # shared saint can be attached to a Day row that lost the
            # feast-level-facts preference for this tradition.
            titles = [dc.title for dc in dcs]
            self.saints.extend(titles)
            self.saint_links.extend((dc.title, dc.id if dc.story else None) for dc in dcs)
            self.spoken_saints.extend(dc.title for dc in dcs if _speech_worthy(dc))
            if titles:
                self.minimal_saints.append('; '.join(titles))

        self.saints.extend(dc.title for dc in additive)
        self.saint_links.extend((dc.title, dc.id if dc.story else None) for dc in additive)
        self.spoken_saints.extend(dc.title for dc in additive if _speech_worthy(dc))

        # spoken_saints excludes only the story-less tradition='greek' overlay
        # (the bulk antiochian.org-harvested commemorations, see
        # docs/saint-model-refactor.md) -- those would otherwise bloat the
        # Alexa skill's spoken commemorations sentence (see alexa/speech.py).
        # Everything that predates that overlay speaks exactly as it always
        # has, story or not -- a plain "has story" filter would also have
        # silently dropped pre-existing, story-less but clearly important
        # commemorations (e.g. St Sava of Serbia, Peter and Fevronia of
        # Murom) whenever some other minor commemoration on the same day
        # happened to have a story. Fall back to the full list when nothing
        # on a given day is speech-worthy, so an ordinary day never goes
        # silent.
        if not self.spoken_saints:
            self.spoken_saints = list(self.saints)

        self.stories = [dc for dc in commemorations if dc.story]

    def _apply_fasting_adjustments(self):
        """Tradition-specific -- see SlavicDay/GreekDay."""
        raise NotImplementedError

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
                    await reading.pericope.aget_passage(language=self.language, translation=self.translation)

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
        query &= Q(tradition__in=(self.tradition, 'common'))

        # Generate the list of readings

        # Do select_related to avoid later synchronous foreign key lookup
        queryset = models.Reading.objects.filter(query).select_related('pericope')

        rows = [reading async for reading in queryset.order_by('ordering')]
        rows = _prefer_tradition(rows, self.tradition)

        self.readings = []
        for reading in rows:
            if fetch_content:
                await reading.pericope.aget_passage(language=self.language, translation=self.translation)

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
                    await reading.pericope.aget_passage(language=self.language, translation=self.translation)

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

        query &= Q(tradition__in=(self.tradition, 'common'))

        # Generate the list of readings.
        # Do select_related to avoid later synchronous foreign key lookup.
        queryset = models.Reading.objects.filter(query).select_related('pericope')
        readings = [reading async for reading in queryset.order_by('ordering')]
        readings = _prefer_tradition(readings, self.tradition)

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
                await reading.pericope.aget_passage(language=self.language, translation=self.translation)

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
    def _sunday_gospel_override(self):
        """Cache of pyear.sunday_gospel_override(pdist) for this day.

        Returns None (no override -- use the default computation), False (no
        daily-cycle Epistle/Gospel at all today -- see GreekYear's class
        docstring), or a raw pdist to use in place of the default one.
        """
        if self.weekday != Weekday.Sunday:
            return None
        return self.pyear.sunday_gospel_override(self.pdist)

    @cached_property
    def _sunday_epistle_override(self):
        """Like _sunday_gospel_override, but for the Epistle -- these do NOT
        always coincide for GreekYear. Confirmed against real antiochian.org
        data: on the ordinary numbered Sundays of Luke the Epistle keeps
        following its own ordinary continuous-cycle position (matching
        SlavicYear's behavior exactly), while the Canaanite Woman and
        post-Theophany-interpolation Sundays DO pair the Epistle with the
        same numbered target as the Gospel. See GreekYear.sunday_epistle_override.
        """
        if self.weekday != Weekday.Sunday:
            return None
        return self.pyear.sunday_epistle_override(self.pdist)

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

        if self._sunday_epistle_override is False:
            return None

        if self._sunday_epistle_override is not None:
            # The numbered-Sunday target pdists (e.g. "12th Sunday of Luke")
            # already have the correct Epistle paired with the Gospel in the
            # shared common/slavic table -- without this, the Epistle fell
            # through to the branches below, which are keyed off calendar
            # pdist rather than the target the Gospel actually resolved to,
            # producing an unrelated (if plausible-looking) citation. This
            # only applies to the Canaanite Woman/interpolation cases now --
            # see _sunday_epistle_override.
            return self._sunday_epistle_override

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

        if self._sunday_gospel_override is False:
            return None

        if self._sunday_gospel_override is not None:
            return self._sunday_gospel_override

        if self.pdist == self.pyear.first_sun_luke + 10*7:
            # On the 11th Sunday of Luke we commemorate the forefathers of the
            # Lord. We read the Gospel that is assigned to Forefathers Sunday
            # from the Paschal cycle. On Forefathers Sunday, we read the Gospel
            # pulled from the Festal cycle for that day (from self.pyear.floats).
            return self.pyear.forefathers + self.pyear.lukan_jump

        if self.weekday == Weekday.Sunday and self.pdist > self.pyear.sun_after_theophany and self.pyear.extra_sundays > 1:
            # On Sundays after Theophany, use the Gospels left unread after the Lukan jump.
            # This is a Slavic-specific mechanism (self.pyear.reserves is always empty for
            # GreekYear, and greek_extra_sundays/theophany_interpolation is its own separate
            # counterpart -- see sunday_gospel_override above). It's also not guaranteed to
            # cover every Sunday extra_sundays implies even for Slavic. Degrade to the
            # fallback below rather than raise IndexError when the index isn't covered.
            i = (self.pdist - self.pyear.sun_after_theophany) // 7
            if 0 <= i - 1 < len(self.pyear.reserves):
                return self.pyear.reserves[i-1]

        if self.pdist > self.pyear.sat_before_theophany:
            # We jump into the paschal cycle for the upcoming Pascha.
            # Some sources say this jump should happen after the 13th week of Luke
            return self.jdn - self.pyear.next_pascha

        if self.pdist > self.pyear.lukan_jump_threshold:
            return self.pdist + self.pyear.lukan_jump

        return self.pdist


class SlavicDay(Day):
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


class GreekDay(Day):
    def _apply_fasting_adjustments(self):
        """Confirmed via docs/greek-fasting.md: the Apostles Fast, Lenten
        Fast, and Dormition Fast all follow the identical weekly pattern as
        Slavic practice. Only the Nativity Fast differs -- Greek practice
        treats every day but Wednesday/Friday as a fish day for the first
        four weeks (Nov 15 - Dec 12), then tightens for the final 12 days
        (Dec 13 - 24) more than Slavic practice does: no fish at all, and
        only Saturday/Sunday keep any wine-and-oil allowance (Monday/
        Tuesday/Thursday drop to the same strictness as Wednesday/Friday,
        rather than just losing fish the way Slavic's ~5-day-shorter
        stricter period does)."""

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
            case FastLevels.ApostlesFast:
                match self.weekday:
                    case Weekday.Tuesday | Weekday.Thursday:
                        if self.fast_exception == 0:
                            self.fast_exception += 1
                    case Weekday.Wednesday | Weekday.Friday:
                        if self.feast_level < 4 and self.fast_exception > 1:
                            self.fast_exception = 1
                    case Weekday.Sunday | Weekday.Saturday:
                        self.fast_exception = 2
            case FastLevels.NativityFast:
                stricter_period = self.pdist >= self.pyear.nativity - 12

                match self.weekday:
                    case Weekday.Wednesday | Weekday.Friday:
                        if self.feast_level < 4 and self.fast_exception > 1:
                            self.fast_exception = 1
                    case Weekday.Sunday | Weekday.Saturday:
                        if stricter_period:
                            # Force wine-and-oil, but never loosen a
                            # deliberately stricter override (7+, e.g. the
                            # "Strict Fast" baseline on Nativity Eve itself).
                            if self.fast_exception == 0 or 1 < self.fast_exception <= 6:
                                self.fast_exception = 1
                        else:
                            self.fast_exception = 2
                    case _:  # Monday, Tuesday, Thursday
                        if stricter_period:
                            if self.feast_level < 4 and 1 < self.fast_exception <= 6:
                                self.fast_exception = 1
                        else:
                            self.fast_exception = 2

        # The days before Nativity and Theophany are wine and oil days
        if self.pdist in (self.pyear.nativity-1, self.pyear.theophany-1) and self.weekday in (Weekday.Sunday, Weekday.Saturday):
            self.fast_exception = 1


_DAY_CLASSES = {
    Tradition.Slavic: SlavicDay,
    Tradition.Greek: GreekDay,
}
