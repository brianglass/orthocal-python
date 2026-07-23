from datetime import date

from django.test import TestCase

from .. import datetools, liturgics, models
from ..datetools import Tradition
from bible.models import Verse


class TestYear(TestCase):
    fixtures = ['calendarium.json', 'commemorations.json']

    def test_pascha(self):
        year = liturgics.SlavicYear(2018)
        pascha = datetools.gregorian_to_jdn(date(2018, 4, 8))
        self.assertEqual(year.pascha, pascha)

    def test_pdists(self):
        year = liturgics.SlavicYear(2018)
        pascha = datetools.gregorian_to_jdn(date(2018, 4, 8))

        data = [
                (date(2019, 1, 6), 'theophany'),
                (date(2018, 2, 24), 'finding'),
                (date(2018, 3, 25), 'annunciation'),
                (date(2018, 6, 29), 'peter_and_paul'),
                (date(2018, 7, 15), 'fathers_six'),
                (date(2018, 8, 29), 'beheading'),
                (date(2018, 9, 8), 'nativity_theotokos'),
                (date(2018, 9, 14), 'elevation'),
                (date(2018, 10, 14), 'fathers_seven'),
                (date(2018, 10, 20), 'demetrius_saturday'),
                (date(2018, 12, 16), 'forefathers'),
                (date(2018, 12, 25), 'nativity'),
        ]

        for dt, feast in data:
            with self.subTest(feast):
                actual = getattr(year, feast)
                expected = datetools.gregorian_to_jdn(dt) - pascha
                self.assertEqual(actual, expected)

    def test_lukan_jump(self):
        # TODO: Confirm this is actually working
        year = liturgics.SlavicYear(2018)
        self.assertEqual(year.lukan_jump, 7) 

    def test_daily_readings(self):
        data = [
            (2018, {266, 280, 268, 272, 273, 252, 259, 260, 261, 262, 266}),
            (2023, {259, 266, 260, 264, 265, 245, 252, 252, 253, 254, 259, -22}),
        ]

        for year, days in data:
            year = liturgics.SlavicYear(year)
            with self.subTest(year):
                self.assertSetEqual(year.no_daily, days)

    def test_reserves(self):
        year = liturgics.SlavicYear(2018)

        self.assertEqual(year.extra_sundays, 3)
        expected = 266, 161, 168
        self.assertSequenceEqual(year.reserves, expected)

    def test_has_no_paremias(self):
        year = liturgics.SlavicYear(2018)
        noparemias = -43, -40, -30, -8
        for pdist in noparemias:
            with self.subTest(pdist):
                self.assertTrue(year.has_no_paremias(pdist))

    def test_has_paremias(self):
        year = liturgics.SlavicYear(2018)
        paremias = -44, -41, -31, -9
        for pdist in paremias:
            with self.subTest(pdist):
                self.assertTrue(year.has_moved_paremias(pdist))

    def test_nativity_fast(self):
        year = liturgics.SlavicYear(2025)
        start, end = year.nativity_fast
        self.assertEqual(start, date(2025, 11, 15))
        self.assertEqual(end, date(2025, 12, 24))

    def test_nativity_fast_julian(self):
        year = liturgics.SlavicYear(2025, calendar=datetools.Calendar.Julian)
        start, end = year.nativity_fast
        self.assertEqual(start, date(2025, 11, 28))
        self.assertEqual(end, date(2026, 1, 6))


class TestTraditionOverlay(TestCase):
    """Tests for the Slavic/Greek tradition axis added on top of the shared
    Byzantine base -- these cover the overlay mechanism itself (Year class
    selection, Reading fallback/override)."""

    fixtures = ['calendarium.json', 'commemorations.json']

    def test_slavic_and_greek_year_are_distinct_subclasses(self):
        # Note: SlavicYear/GreekYear are decorated with @lru_cache, which
        # (as with the pre-existing Year class) turns the name into a
        # cache-wrapper object rather than a real type, so isinstance()
        # against SlavicYear/GreekYear themselves doesn't work -- compare
        # via type() instead.
        slavic = liturgics.SlavicYear(2026)
        greek = liturgics.GreekYear(2026)

        self.assertIsInstance(slavic, liturgics.ByzantineYear)
        self.assertIsInstance(greek, liturgics.ByzantineYear)
        self.assertNotEqual(type(slavic), type(greek))

    def test_byzantine_year_shares_lukan_jump_and_defaults_reserves_empty(self):
        """lukan_jump/lukan_jump_threshold/first_sun_luke are confirmed
        identical between SlavicYear and GreekYear (see GreekYear's class
        docstring), so they live on ByzantineYear directly rather than being
        duplicated per subclass. reserves defaults to empty here since only
        SlavicYear actually uses the reserve/replay mechanism."""

        base = liturgics.ByzantineYear(2026)
        slavic = liturgics.SlavicYear(2026)
        greek = liturgics.GreekYear(2026)

        for attr in ('lukan_jump', 'lukan_jump_threshold', 'first_sun_luke'):
            with self.subTest(attr):
                value = getattr(base, attr)
                self.assertEqual(value, getattr(slavic, attr))
                self.assertEqual(value, getattr(greek, attr))

        self.assertEqual(base.reserves, [])
        self.assertEqual(greek.reserves, [])

    def test_shared_anchors_agree_between_traditions(self):
        """Fixed-calendar-date anchors should be identical for both traditions."""

        slavic = liturgics.SlavicYear(2026)
        greek = liturgics.GreekYear(2026)

        for attr in ('elevation', 'nativity', 'theophany', 'annunciation', 'floats'):
            with self.subTest(attr):
                self.assertEqual(getattr(slavic, attr), getattr(greek, attr))

    async def test_common_reading_is_shared_by_both_traditions(self):
        """With no tradition-specific override, both traditions should see the
        same 'common' Reading row -- this is the day-to-day case today, since
        no overlay rows exist yet."""

        for tradition in (Tradition.Slavic, Tradition.Greek):
            with self.subTest(tradition):
                day = liturgics.Day(2026, 9, 14, tradition=tradition)
                await day.ainitialize()
                readings = await day.aget_readings()
                displays = {r.pericope.sdisplay for r in readings}
                self.assertIn('John 19.6-11, 13-20, 25-28, 30-35', displays)

    async def test_tradition_specific_row_overrides_common_row(self):
        """A tradition-tagged row should shadow the 'common' row for the same slot."""

        pericope = await models.Pericope.objects.afirst()

        common = await models.Reading.objects.acreate(
            month=8, day=29, pdist=0, source='Epistle', desc='__test__',
            pericope=pericope, ordering=821, flag=0, tradition='common',
        )
        greek_override = await models.Reading.objects.acreate(
            month=8, day=29, pdist=0, source='Epistle', desc='__test__',
            pericope=pericope, ordering=821, flag=0, tradition='greek',
        )

        try:
            rows = liturgics.day._prefer_tradition([common, greek_override], Tradition.Greek)
            self.assertEqual(rows, [greek_override])

            rows = liturgics.day._prefer_tradition([common, greek_override], Tradition.Slavic)
            self.assertEqual(rows, [common])
        finally:
            await common.adelete()
            await greek_override.adelete()


class TestGreekLukanNumbering(TestCase):
    """GreekYear.lukan_sunday_numbers and theophany_interpolation, checked
    against every Sunday in the antiochian.org official liturgical charts
    for 2023, 2024, 2025, and 2026 -- confirmed exact match across all four
    years, including every reserved-window and Apostle-override case
    encountered (see GreekYear's class docstring in liturgics/year.py for
    the source and full derivation)."""

    def test_reserved_window_and_override_numbering(self):
        # (year, month, day, expected number or None if claimed outright by
        # an override feast that year)
        data = [
            # 2023: no Apostle-override collisions this year -- exercises
            # the plain reserved-window + sequential-fill path only.
            (2023, 9, 24, 1), (2023, 10, 1, 2), (2023, 10, 8, 3),
            (2023, 10, 15, 4), (2023, 10, 22, 6), (2023, 10, 29, 7),
            (2023, 11, 5, 5), (2023, 11, 12, 8), (2023, 11, 19, 9),
            (2023, 11, 26, 13), (2023, 12, 3, 14), (2023, 12, 10, 10),
            (2023, 12, 17, 11),
            # 2024: also no override collisions.
            (2024, 9, 22, 1), (2024, 9, 29, 2), (2024, 10, 6, 3),
            (2024, 10, 13, 4), (2024, 10, 20, 6), (2024, 10, 27, 7),
            (2024, 11, 3, 5), (2024, 11, 10, 8), (2024, 11, 17, 9),
            (2024, 11, 24, 13), (2024, 12, 1, 14), (2024, 12, 8, 10),
            (2024, 12, 15, 11),
            # 2025: Apostle Matthew (Nov 16) and Apostle Andrew (Nov 30)
            # each claim a Sunday outright, dropping "8th" and "13th".
            (2025, 9, 28, 1), (2025, 10, 5, 2), (2025, 10, 12, 4),
            (2025, 10, 19, 3), (2025, 10, 26, 6), (2025, 11, 2, 5),
            (2025, 11, 9, 7), (2025, 11, 16, None), (2025, 11, 23, 9),
            (2025, 11, 30, None), (2025, 12, 7, 10), (2025, 12, 14, 11),
            # 2026: Apostle and Evangelist Luke (Oct 18) claims a Sunday
            # outright, dropping "3rd".
            (2026, 9, 27, 1), (2026, 10, 4, 2), (2026, 10, 11, 4),
            (2026, 10, 18, None), (2026, 10, 25, 6), (2026, 11, 1, 5),
            (2026, 11, 8, 7), (2026, 11, 15, 8), (2026, 11, 22, 9),
            (2026, 11, 29, 13), (2026, 12, 6, 10), (2026, 12, 13, 11),
        ]

        years = {}
        for year, month, day, expected in data:
            if year not in years:
                years[year] = liturgics.GreekYear(year)
            pyear = years[year]
            pdist = pyear.date_to_pdist(month, day, year)
            with self.subTest((year, month, day)):
                self.assertEqual(pyear.lukan_sunday_numbers.get(pdist), expected)

    def test_theophany_interpolation(self):
        # Each confirmed against real antiochian.org harvest data for the
        # specific cycle year named -- see docs/greek-weekday-drift.md for
        # the full derivation. The n=5 case corrects a table entry that had
        # never been checked against a real n=5 year (it was transcribed
        # from a source that only covered n<=5 in the abstract); n=6 and
        # n=7 were previously entirely missing (crashed -- see
        # TestReadingsView.test_greek_extra_sundays_overflow_does_not_500).

        # 2025 cycle (n=3): 12th of Luke. (The following Sunday, Jan 25,
        # would be "15th of Luke" in the old table, but that's the row's
        # trailing/last entry -- always unreachable, since it always lands
        # exactly at pdist -77; see canaanite_woman_applies and the comment
        # on _THEOPHANY_INTERPOLATION for why it's correctly omitted from
        # the table entirely rather than tested here.)
        pyear = liturgics.GreekYear(2025)
        self.assertEqual(pyear.greek_extra_sundays, 3)
        jan18 = pyear.date_to_pdist(1, 18, 2026)
        self.assertEqual(pyear.theophany_interpolation[jan18], (None, 12))
        self.assertEqual(
            pyear.sunday_gospel_override(jan18),
            liturgics.GreekYear._lukan_sunday_target(12),
        )

        # 2018 cycle (n=5): 12th, 15th, 16th of Matthew, 17th of Matthew
        # (Canaanite Woman) -- NOT 12th, 14th, 15th, 17th as the table
        # claimed before this pass.
        pyear = liturgics.GreekYear(2018)
        self.assertEqual(pyear.greek_extra_sundays, 5)
        jan20 = pyear.date_to_pdist(1, 20, 2019)
        jan27 = pyear.date_to_pdist(1, 27, 2019)
        feb3 = pyear.date_to_pdist(2, 3, 2019)
        self.assertEqual(pyear.theophany_interpolation[jan20], (None, 12))
        self.assertEqual(pyear.theophany_interpolation[jan27], (None, 15))
        self.assertEqual(pyear.theophany_interpolation[feb3], ('matthew', 16))

        # 2020 cycle (n=6): 12th, 14th, 15th, 16th of Matthew.
        pyear = liturgics.GreekYear(2020)
        self.assertEqual(pyear.greek_extra_sundays, 6)
        jan17 = pyear.date_to_pdist(1, 17, 2021)
        jan24 = pyear.date_to_pdist(1, 24, 2021)
        jan31 = pyear.date_to_pdist(1, 31, 2021)
        feb7 = pyear.date_to_pdist(2, 7, 2021)
        self.assertEqual(pyear.theophany_interpolation[jan17], (None, 12))
        self.assertEqual(pyear.theophany_interpolation[jan24], (None, 14))
        self.assertEqual(pyear.theophany_interpolation[jan31], (None, 15))
        self.assertEqual(pyear.theophany_interpolation[feb7], ('matthew', 16))

        # 2023 cycle (n=7, and Leavetaking of Theophany -- Jan 14, 2024 --
        # falls on a Sunday that year): Leavetaking special case, then the
        # exact same sequence as 2020's n=6 case.
        pyear = liturgics.GreekYear(2023)
        self.assertEqual(pyear.greek_extra_sundays, 7)
        self.assertEqual(
            datetools.weekday_from_pdist(pyear.theophany + 8),
            datetools.Weekday.Sunday,
        )
        jan14 = pyear.date_to_pdist(1, 14, 2024)
        jan21 = pyear.date_to_pdist(1, 21, 2024)
        jan28 = pyear.date_to_pdist(1, 28, 2024)
        feb4 = pyear.date_to_pdist(2, 4, 2024)
        feb11 = pyear.date_to_pdist(2, 11, 2024)
        self.assertEqual(
            pyear.theophany_interpolation[jan14],
            ('direct', datetools.FloatIndex.SunAfterTheophany),
        )
        self.assertEqual(pyear.theophany_interpolation[jan21], (None, 12))
        self.assertEqual(pyear.theophany_interpolation[jan28], (None, 14))
        self.assertEqual(pyear.theophany_interpolation[feb4], (None, 15))
        self.assertEqual(pyear.theophany_interpolation[feb11], ('matthew', 16))

    def test_canaanite_woman_applies(self):
        # Canaanite Woman (Greek) / Zacchaeus (Slavic) Sunday is the same
        # fixed, Pascha-anchored occasion (11 weeks before Pascha) in both
        # traditions, but Greek only actually shows Canaanite Woman content
        # there once the preceding winter's gap was large enough to exhaust
        # the plain Luke/Matthew numbering (n>=4) -- confirmed via real
        # harvest data for both a small (n=3, no override) and large (n=4+,
        # override) case. This can't be decided from the year whose own
        # theophany_interpolation computed the assignment -- Day always
        # resolves the real calendar date via the *following* GreekYear
        # instance -- see canaanite_woman_applies's docstring for why.
        self.assertFalse(liturgics.GreekYear(2018).canaanite_woman_applies)  # follows 2017, regular n=2
        self.assertFalse(liturgics.GreekYear(2026).canaanite_woman_applies)  # follows 2025, n=3
        self.assertTrue(liturgics.GreekYear(2019).canaanite_woman_applies)  # follows 2018, n=5
        self.assertTrue(liturgics.GreekYear(2021).canaanite_woman_applies)  # follows 2020, n=6
        self.assertEqual(
            liturgics.GreekYear(2019).sunday_gospel_override(-77),
            liturgics.GreekYear._matthew_sunday_target(17),
        )
        self.assertIsNone(liturgics.GreekYear(2026).sunday_gospel_override(-77))

    def test_leavetaking_theophany_weekday_float(self):
        """Leavetaking of Theophany (theophany+8) has a fixed Greek-specific
        reading (Acts 2:38-43 / Luke 4:1-15, confirmed against 5 independent
        years) when it falls on an ordinary weekday. When it falls on
        Saturday or Sunday it's already covered by SatAfterTheophany/
        SunAfterTheophany instead -- the float should not double up."""

        # 2026: Jan 14 is a Wednesday -- ordinary weekday case.
        weekday_year = liturgics.GreekYear(2025)
        leavetaking = weekday_year.theophany + 8
        self.assertEqual(
            weekday_year.floats.get(leavetaking),
            datetools.FloatIndex.LeavetakingTheophanyWeekday,
        )

        # 2023 cycle: Leavetaking falls on a Sunday that year (Jan 14, 2024)
        # -- already handled via theophany_interpolation's 'direct' case,
        # so the weekday float must not also claim that pdist.
        sunday_year = liturgics.GreekYear(2023)
        leavetaking_sunday = sunday_year.theophany + 8
        self.assertEqual(datetools.weekday_from_pdist(leavetaking_sunday), datetools.Weekday.Sunday)
        self.assertNotIn(leavetaking_sunday, sunday_year.floats)


class TestDay(TestCase):
    fixtures = ['calendarium.json', 'commemorations.json']

    async def test_no_memorial(self):
        """Memorial Saturday with no memorial readings should not have John 5.24-30."""

        day = liturgics.Day(2022, 3, 26)
        await day.ainitialize()
        readings = await day.aget_readings()
        short_displays = [r.pericope.sdisplay for r in readings]
        self.assertNotIn('John 5.24-30', short_displays)

    async def test_scriptures(self):
        # Cheesefare Sunday
        day = liturgics.Day(2018, 2, 18)
        await day.ainitialize()
        readings = await day.aget_readings()

        self.assertEqual(len(readings), 3)

        count = await readings[0].pericope.get_passage().acount()
        self.assertEqual(count, 12)
        count = await readings[1].pericope.get_passage().acount()
        self.assertEqual(count, 8)
        count = await readings[2].pericope.get_passage().acount()
        self.assertEqual(count, 8)

    async def test_scriptures_pascha(self):
        day = liturgics.Day(2023, 4, 16)
        await day.ainitialize()
        readings = await day.aget_readings()

        self.assertEqual(len(readings), 2)

        self.assertEqual('Acts 1.1-8', readings[0].pericope.display)
        self.assertEqual('John 1.1-17', readings[1].pericope.display)

        # TODO: This is the Paschal Vespers. There are some missing records in
        # the fixtures that we need to update from
        # https://github.com/paulkachur/orthodox_calendar

        #self.assertEqual('John 20.19-25', readings[2].pericope.display)

    async def test_annunciation(self):
        """Test a sample feast day."""

        day = liturgics.Day(2018, 3, 25)
        await day.ainitialize()

        self.assertIn('Annunciation Most Holy Theotokos', day.feasts)
        self.assertIn('St Mary of Egypt', day.feasts)

        self.assertEqual(day.feast_level, 7)
        self.assertEqual(day.fast_level, 2)
        self.assertEqual(day.fast_exception, 4)
        readings = await day.aget_readings()
        self.assertEqual(len(readings), 12)

    async def test_paremias(self):
        """Paremias should be moved from the subsequent day."""

        day = liturgics.Day(2018, 3, 8)
        await day.ainitialize()
        readings = await day.aget_readings()
        self.assertEqual(len(readings), 6)

    async def test_sebaste(self):
        """Paremias should be moved to the previous day."""

        day = liturgics.Day(2018, 3, 9)
        await day.ainitialize()
        readings = await day.aget_readings()

        self.assertEqual(len(readings), 6)
        self.assertEqual(readings[0].source, 'Matins Gospel')

        short_displays = [r.pericope.sdisplay for r in readings]
        self.assertEqual(len(short_displays), len(set(short_displays)))

    async def test_tone(self):
        data = [
			(2023, 1, 1, 4),   # 29th Sunday after Pentecost
			(2023, 4, 8, 0),   # Lazarus Saturday
			(2023, 4, 17, 2),  # Bright Friday
			(2023, 4, 21, 6),  # Bright Friday
			(2023, 4, 22, 8),  # Bright Saturday
			(2023, 4, 23, 1),  # Thomas Sunday
			(2023, 6, 11, 8),  # 1st Sunday after Pentecost; All Saints
            (2023, 6, 18, 1),  # 2nd Sunday after Pentecost
        ]

        for year, month, day, tone in data:
            day = liturgics.Day(year, month, day)
            await day.ainitialize()
            with self.subTest(tone):
                self.assertEqual(tone, day.tone)

    async def test_fasting_levels(self):
        # Use Apostles Fast as a test case
        data = [
			(2018, 6, 3, 0, 0),
			(2018, 6, 4, 3, 0),
			(2018, 6, 12, 3, 1),
			(2018, 6, 14, 3, 1),
			(2018, 6, 16, 3, 2),
			(2018, 6, 17, 3, 2),
			(2018, 6, 28, 3, 1),
			(2018, 6, 29, 1, 2),
			(2018, 6, 30, 0, 0),
        ]

        for year, month, day, fast, exception in data:
            day = liturgics.Day(year, month, day)
            await day.ainitialize()
            with self.subTest():
                self.assertEqual(day.fast_level, fast)
                self.assertEqual(day.fast_exception, exception)

    async def test_fast_free(self):
        """Test fast free days."""

        data = [
			(2018, 12, 26, 0, "No Fast"),
			(2018, 12, 28, 0, "No Fast"),
			(2019, 1, 2, 0, "No Fast"),
			(2019, 1, 4, 0, "No Fast"),
        ]

        for year, month, day, fast, description in data:
            day = liturgics.Day(year, month, day)
            await day.ainitialize()
            with self.subTest():
                self.assertEqual(day.fast_level, fast)
                self.assertEqual(day.fast_level_desc, description)

    async def test_eothinon(self):
        data = [
            (2018, 3, 11, 7),
            (2023, 1, 1, 7),
            (2023, 1, 8, 8),
        ]

        for year, month, day, gospel in data:
            day = liturgics.Day(year, month, day)
            await day.ainitialize()
            with self.subTest(gospel):
                self.assertEqual(day.eothinon_gospel, gospel)

    async def test_composites(self):
        """Test for composite scripture readings."""

        # The lengths are slightly different than the Go version because they
        # are unicode rather than utf-8.
        data = [
			(2019, 2, 27, 0, 1378), # 2
			(2019, 2, 24, 0, 1486), # 3
			(2019, 2, 24, 1, 1357), # 8
			(2019, 2, 24, 2, 1306), # 9
        ]

        for year, month, day, reading, length in data:
            day = liturgics.Day(year, month, day)
            await day.ainitialize()
            readings = await day.aget_readings()
            with self.subTest(f'{day}: {reading}'):
                passage = readings[reading].pericope.get_passage()
                verse = await passage.afirst()
                self.assertEqual(len(verse.content), length)

    async def test_abbreviated_readings(self):
        data = [
			(2023, 2, 5, 2),    # Sunday of the Publican and Pharisee; 2 NT readings
			(2023, 2, 27, 3),   # first day of Lent + St. Raphael of Brooklyn; 3 OT readings
			(2023, 2, 28, 3),   # second day of Lent; 3 OT readings
			(2023, 3, 9, 2),    # Holy 40 Martyrs of Sebaste during Lent; should be 2 NT readings
			(2023, 3, 24, 3),   # Forefeast of Annunciation; should be 3 OT readings
			(2023, 3, 25, 2),   # Annunciation; should be 2 NT readings
			(2023, 4, 14, 2),   # Holy Thursday; should NOT include passion gospels
			(2071, 3, 26, 3),   # leavetaking of the Annunciation on a non-liturgy day
        ]

        for year, month, day, length in data:
            day = liturgics.Day(year, month, day)
            await day.ainitialize()
            readings = await day.aget_abbreviated_readings()
            with self.subTest(f'{day}'):
                self.assertEqual(length, len(readings))

    async def test_new_martyrs_russia(self):
        data = [
            (2023, 1, 22),
            (2022, 1, 23),
        ]
        for y, m, d in data:
            day = liturgics.Day(y, m, d)
            await day.ainitialize()
            with self.subTest(y):
                self.assertIn('New Martyrs and Confessors of Russia', day.feasts)

    async def test_gospel_pdist(self):
        data = [
            (2022, 12, 4, 252),  # Sunday of the Forefathers of Christ
            (2023, 12, 3, 259),  # Sunday of the Forefathers of Christ
            (2023, 1, 2, -104),
            (2022, 12, 30, 271),
            (2022, 12, 31, 272),
        ]

        for y, m, d, pdist in data:
            day = liturgics.Day(y, m, d)
            await day.ainitialize()
            with self.subTest(day.gregorian_date):
                self.assertEqual(day.gospel_pdist, pdist)

    async def test_greek_theophany_interpolation_pdists(self):
        """End-to-end (Day, not just GreekYear) check that the fixes in
        test_theophany_interpolation/test_canaanite_woman_applies actually
        take effect through Day.gospel_pdist/epistle_pdist -- both need to
        agree, confirming the Epistle-Gospel wiring fix (previously,
        epistle_pdist never consulted the Sunday-of-Luke/Matthew override
        at all, and fell through to an unrelated calendar-relative pdist)."""

        luke_12, luke_14, luke_15 = (
            liturgics.GreekYear._lukan_sunday_target(n) for n in (12, 14, 15)
        )
        matt_16, matt_17 = (
            liturgics.GreekYear._matthew_sunday_target(n) for n in (16, 17)
        )

        data = [
            # 2020 cycle (n=6): previously crashed entirely.
            (2021, 1, 17, luke_12),
            (2021, 1, 24, luke_14),
            (2021, 1, 31, luke_15),
            (2021, 2, 7, matt_16),
            (2021, 2, 14, matt_17),  # Canaanite Woman -- the boundary case
            # 2023 cycle (n=7, Leavetaking-on-Sunday): previously crashed.
            (2024, 1, 14, datetools.FloatIndex.SunAfterTheophany),
            (2024, 1, 21, luke_12),
            (2024, 2, 11, matt_16),
            # 2018 cycle (n=5): the previously-wrong table entry.
            (2019, 1, 27, luke_15),
            (2019, 2, 3, matt_16),
            (2019, 2, 10, matt_17),  # Canaanite Woman
            # 2025 cycle (n=3): Canaanite Woman does NOT apply here, so
            # this falls all the way through to the plain calendar pdist
            # (-77) rather than the numbered target -- confirms the
            # boundary fix doesn't over-fire for small n. The shared
            # common/slavic table's own content at -77 happens to be the
            # same text as "15th Sunday of Luke" (both are Luke 19:1-10,
            # Zacchaeus), just addressed via a different pdist.
            (2026, 1, 25, -77),
            # 2017 cycle (regular_extra_sundays=2, the smallest magnitude
            # confirmed against real data): also correctly falls through to
            # -77 rather than the old table's (now-removed) "25th of Luke"
            # entry, which was never actually reachable either.
            (2018, 1, 21, -77),
        ]

        for y, m, d, expected in data:
            day = liturgics.Day(y, m, d, tradition=Tradition.Greek)
            await day.ainitialize()
            with self.subTest((y, m, d)):
                self.assertEqual(day.gospel_pdist, expected)
                self.assertEqual(day.epistle_pdist, expected)

    async def test_leavetaking_theophany_weekday_reading(self):
        """End-to-end: Leavetaking of Theophany on an ordinary weekday shows
        the Greek-specific Acts 2:38-43 / Luke 4:1-15 reading additively
        alongside the ordinary continuous-cycle content, while Slavic shows
        only the ordinary content -- confirmed against 5 independent years
        (2019, 2021, 2022, 2025, 2026 cycles)."""

        dates = [(2019, 1, 14), (2021, 1, 14), (2022, 1, 14), (2025, 1, 14), (2026, 1, 14)]
        for y, m, d in dates:
            greek = liturgics.Day(y, m, d, tradition=Tradition.Greek)
            slavic = liturgics.Day(y, m, d, tradition=Tradition.Slavic)
            await greek.ainitialize()
            await slavic.ainitialize()
            greek_readings = await greek.aget_readings()
            slavic_readings = await slavic.aget_readings()

            greek_displays = {(r.source, r.pericope.display) for r in greek_readings}
            slavic_displays = {(r.source, r.pericope.display) for r in slavic_readings}

            with self.subTest((y, m, d)):
                self.assertIn(('Epistle', 'Acts 2.38-43'), greek_displays)
                self.assertIn(('Gospel', 'Luke 4.1-15'), greek_displays)
                self.assertNotIn(('Epistle', 'Acts 2.38-43'), slavic_displays)
                self.assertNotIn(('Gospel', 'Luke 4.1-15'), slavic_displays)

    async def test_ordinary_sunday_of_luke_epistle_does_not_follow_gospel(self):
        """On the *ordinary* (non-interpolated) numbered Sundays of Luke,
        the Epistle keeps following its own ordinary continuous-cycle
        position -- unlike the Canaanite Woman/post-Theophany-interpolation
        cases covered by test_greek_theophany_interpolation_pdists above,
        where Epistle and Gospel genuinely share the same numbered target.

        Confirmed against real antiochian.org data across independent
        years: the same numbered Sunday (e.g. "1st Sunday of Luke") shows a
        *different* Epistle in different years, which rules out a fixed
        Gospel-paired target -- it's always exactly the plain, unadjusted
        calendar pdist's own Epistle instead (matching SlavicYear's own
        Epistle for that date exactly, since neither traditions' Epistle
        is affected by the Lukan jump here)."""

        data = [
            # (year, month, day, expected epistle_pdist == plain calendar pdist)
            (2022, 9, 25, 154),   # 1st Sunday of Luke
            (2022, 10, 2, 161),   # 2nd Sunday of Luke
            (2026, 9, 27, 168),   # 1st Sunday of Luke
            (2026, 10, 4, 175),   # 2nd Sunday of Luke
        ]

        for y, m, d, plain_pdist in data:
            greek = liturgics.Day(y, m, d, tradition=Tradition.Greek)
            slavic = liturgics.Day(y, m, d, tradition=Tradition.Slavic)
            await greek.ainitialize()
            await slavic.ainitialize()
            with self.subTest((y, m, d)):
                self.assertEqual(greek.epistle_pdist, plain_pdist)
                self.assertNotEqual(greek.epistle_pdist, greek.gospel_pdist)
                self.assertEqual(greek.epistle_pdist, slavic.epistle_pdist)

    async def test_composite_fields(self):
        """When a reading is a Composite, it should have the same fields as a Verse."""

        year, month, day = 2023, 3, 30
        day = liturgics.Day(year, month, day)
        await day.ainitialize()
        readings = await day.aget_readings()
        passage = await readings[3].pericope.aget_passage()

        for field in Verse._meta.get_fields():
            if field.name != 'id':
                with self.subTest(field.name):
                    self.assertTrue(hasattr(passage[0], field.name))
