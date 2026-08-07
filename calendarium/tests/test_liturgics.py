from datetime import date

from django.test import TestCase

from .. import datetools, liturgics, models
from ..datetools import Tradition, Translation
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

    def test_raphael_brooklyn_first_saturday_of_november(self):
        """St. Raphael of Brooklyn -- Greek-only, see docs/greek-fasting.md.
        Confirmed via the Antiochian Archdiocese's own typikon (an editor's
        note citing their observance directly) that he's kept on the first
        Saturday of November, not Feb 27 (his OCA/Slavic date). Checked
        across years where Nov 1 falls on each different weekday, so the
        "roll forward to Saturday" arithmetic is exercised in full."""

        for year, expected in (
            (2025, date(2025, 11, 1)),   # Nov 1 is itself a Saturday
            (2026, date(2026, 11, 7)),   # Nov 1 is a Sunday
            (2024, date(2024, 11, 2)),   # Nov 1 is a Friday
        ):
            with self.subTest(year):
                py = liturgics.GreekYear(year)
                pdist = py.raphael_brooklyn
                actual = datetools.gregorian_to_jdn(expected) - py.pascha
                self.assertEqual(pdist, actual)
                self.assertEqual(py.floats.get(pdist), datetools.FloatIndex.RaphaelBrooklyn)

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

    async def test_day_feast_name_is_tradition_specific(self):
        """Day.feast_name/feast_level (unlike Reading) had no tradition axis
        at all until this was found via a real bug: Greek was showing
        Slavic's Oct 1 Protection-of-the-Theotokos feast/fasting rank even
        after the Reading-level content was fixed, since Greek observes
        Protection on Oct 28 instead. Confirmed via antiochian.org's full
        day description (not just the primary title, to rule out
        Sunday-collision false positives) that Slavic-specific fixed feasts
        like this are genuinely absent from Greek's Menaion, not just
        under a different label."""

        slavic = liturgics.Day(2026, 10, 1, tradition=Tradition.Slavic)
        greek = liturgics.Day(2026, 10, 1, tradition=Tradition.Greek)
        await slavic.ainitialize()
        await greek.ainitialize()

        self.assertIn('Protection (Pokrov) of the Most-Holy Theotokos', slavic.feasts)
        self.assertEqual(slavic.feast_level, 6)

        self.assertNotIn('Protection (Pokrov) of the Most-Holy Theotokos', greek.feasts)
        self.assertEqual(greek.feast_level, 0)

        # Ananias is a genuine Greek commemoration this project's OCA-derived
        # data was simply missing -- both traditions should show him.
        self.assertIn('Holy Apostle Ananias of the Seventy', slavic.saints)
        self.assertIn('Holy Apostle Ananias of the Seventy', greek.saints)

    async def test_raphael_brooklyn_differing_commemoration_date(self):
        """St. Raphael of Brooklyn -- founding bishop of Antiochian
        Orthodoxy in America -- is kept on Feb 27 (his repose date) by
        Slavic/OCA practice, but on the first Saturday of November by the
        Antiochian Archdiocese itself (confirmed via their own typikon).
        Same shape as the Catherine of Alexandria/Theophan the Recluse
        fixes: a genuine differing-date case, implemented via the
        pdist-anchored RaphaelBrooklyn float rather than a fixed month/day,
        since "first Saturday of November" moves every year."""

        slavic_feb27 = liturgics.Day(2025, 2, 27, tradition=Tradition.Slavic)
        greek_feb27 = liturgics.Day(2025, 2, 27, tradition=Tradition.Greek)
        await slavic_feb27.ainitialize()
        await greek_feb27.ainitialize()

        self.assertIn('St Raphael Bishop of Brooklyn', slavic_feb27.feasts)
        self.assertNotIn('St Raphael Bishop of Brooklyn', greek_feb27.feasts)

        # Nov 1, 2025 is itself a Saturday.
        slavic_nov1 = liturgics.Day(2025, 11, 1, tradition=Tradition.Slavic)
        greek_nov1 = liturgics.Day(2025, 11, 1, tradition=Tradition.Greek)
        await slavic_nov1.ainitialize()
        await greek_nov1.ainitialize()

        self.assertNotIn('St Raphael Bishop of Brooklyn', slavic_nov1.feasts)
        self.assertIn('St Raphael Bishop of Brooklyn', greek_nov1.feasts)


class TestGreekFasting(TestCase):
    """Day was split into SlavicDay/GreekDay (each with its own
    _apply_fasting_adjustments) after confirming the Nativity Fast's weekly
    pattern genuinely differs from Slavic/OCA practice -- see
    docs/greek-fasting.md. Holy Week, the Apostles' Fast, and the Dormition
    Fast were all checked and found identical to Slavic practice. Great
    Lent's ordinary weekday pattern is also identical, but three specific
    named wine-and-oil exceptions in OCA's rule (Forefeast of the
    Annunciation, and the fifth week's Wednesday/Friday vigil exceptions)
    were empirically confirmed absent from Antiochian practice -- unlike
    the Nativity Fast, that difference is a Day-row data split, not a code
    difference in _apply_fasting_adjustments."""

    fixtures = ['calendarium.json', 'commemorations.json']

    async def test_day_dispatches_to_tradition_specific_subclass(self):
        slavic = liturgics.Day(2026, 11, 20, tradition=Tradition.Slavic)
        greek = liturgics.Day(2026, 11, 20, tradition=Tradition.Greek)

        self.assertIsInstance(slavic, liturgics.Day)
        self.assertIsInstance(greek, liturgics.Day)
        self.assertIsInstance(slavic, liturgics.SlavicDay)
        self.assertIsInstance(greek, liturgics.GreekDay)
        self.assertNotIsInstance(slavic, liturgics.GreekDay)

    async def test_nativity_fast_phase_one_monday_differs(self):
        """Nov 23, 2026 is an ordinary Monday in the Nativity Fast's first
        phase (Nov 15 - Dec 12), with no overriding feast. Slavic groups
        Monday with Wednesday/Friday (strict); Greek treats every day but
        Wednesday/Friday as a fish day during this phase."""

        slavic = liturgics.Day(2026, 11, 23, tradition=Tradition.Slavic)
        greek = liturgics.Day(2026, 11, 23, tradition=Tradition.Greek)
        await slavic.ainitialize()
        await greek.ainitialize()

        self.assertEqual(slavic.fast_exception_desc, '')
        self.assertEqual(greek.fast_exception_desc, 'Fish, Wine and Oil are Allowed')

    async def test_nativity_fast_phase_two_starts_a_week_earlier_for_greek(self):
        """Dec 15, 2026 is an ordinary Tuesday. Slavic's stricter period
        doesn't start until ~Dec 20, so it still gets the ordinary
        Tuesday/Thursday wine-and-oil allowance; Greek's stricter period
        starts Dec 13, a full week earlier, and drops Monday/Tuesday/
        Thursday to full strictness (not just losing fish)."""

        slavic = liturgics.Day(2026, 12, 15, tradition=Tradition.Slavic)
        greek = liturgics.Day(2026, 12, 15, tradition=Tradition.Greek)
        await slavic.ainitialize()
        await greek.ainitialize()

        self.assertEqual(slavic.fast_exception_desc, 'Wine and Oil are Allowed')
        self.assertEqual(greek.fast_exception_desc, '')

    async def test_nativity_fast_phase_two_weekend_loses_fish_earlier_for_greek(self):
        """Dec 13, 2026 is a Sunday -- the first day of Greek's stricter
        period, but still well inside Slavic's ordinary-weekend-gets-fish
        window (Slavic's stricter period doesn't start until ~Dec 20)."""

        slavic = liturgics.Day(2026, 12, 13, tradition=Tradition.Slavic)
        greek = liturgics.Day(2026, 12, 13, tradition=Tradition.Greek)
        await slavic.ainitialize()
        await greek.ainitialize()

        self.assertEqual(slavic.fast_exception_desc, 'Fish, Wine and Oil are Allowed')
        self.assertEqual(greek.fast_exception_desc, 'Wine and Oil are Allowed')

    async def test_nativity_eve_strict_baseline_not_weakened_by_greek_stricter_period(self):
        """Regression test for a bug caught during implementation: Dec 24,
        2026 is a Thursday with a deliberately strict baseline
        (fast_exception index 9, "Strict Fast" -- distinct from the
        generic index-0 strict day). GreekDay's stricter-period logic caps
        lenient baselines (indices 2-6) down to wine-and-oil on Monday/
        Tuesday/Thursday, but must never loosen an already-stricter
        baseline like this one -- confirmed identical to Slavic across
        2023 (Sunday), 2026 (Thursday), and 2027 (Friday), which exercise
        three different weekday branches of the fasting logic."""

        for year in (2023, 2026, 2027):
            with self.subTest(year):
                slavic = liturgics.Day(year, 12, 24, tradition=Tradition.Slavic)
                greek = liturgics.Day(year, 12, 24, tradition=Tradition.Greek)
                await slavic.ainitialize()
                await greek.ainitialize()

                self.assertEqual(slavic.fast_exception_desc, greek.fast_exception_desc)

    async def test_holy_week_apostles_dormition_fasts_are_identical_between_traditions(self):
        """Holy Week, the Apostles' Fast, and the Dormition Fast were all
        confirmed (via dedicated Antiochian sources) to follow the same
        weekly pattern as Slavic practice -- this is a regression guard
        against that accidentally changing. Ordinary weeks of Great Lent
        are NOT covered here -- see the wine-and-oil exception tests below
        for three confirmed exceptions that do differ.

        Aug 9 (St Herman of Alaska's Vigil-rank feast, Slavic tradition)
        needs no exclusion here: see
        test_dormition_fast_grants_no_rank_based_fish_exception below for
        why both traditions correctly agree at plain wine-and-oil despite
        Slavic's Vigil rank."""

        dates = (
            [date(2026, 4, d) for d in range(5, 13)]        # Holy Week
            + [date(2026, 6, d) for d in range(9, 15)]      # Apostles' Fast
            + [date(2026, 8, d) for d in range(1, 15)]      # Dormition Fast
        )

        for d in dates:
            with self.subTest(d):
                slavic = liturgics.Day(d.year, d.month, d.day, tradition=Tradition.Slavic)
                greek = liturgics.Day(d.year, d.month, d.day, tradition=Tradition.Greek)
                await slavic.ainitialize()
                await greek.ainitialize()

                self.assertEqual(slavic.fast_level_desc, greek.fast_level_desc)
                self.assertEqual(slavic.fast_exception_desc, greek.fast_exception_desc)

    async def test_dormition_fast_grants_no_rank_based_fish_exception(self):
        """Regression test for a data bug reported directly against
        production: Aug 9, 2026 (St Herman of Alaska's Vigil-rank feast)
        showed a fish allowance, contradicting antiochian.org and
        goarch.org (both show wine-and-oil only).

        The root cause wasn't bad data on any one row -- Herman's
        Vigil rank (feast_level=5) is itself correct, confirmed against
        OCA's own "Classes of Feasts" page. The bug was a wrong
        *assumption* baked into fast_exception: the Typikon's Vigil-rank
        fish exception (Ch. 32-33) is scoped to the Apostles' and Nativity
        fasts only -- it doesn't exist for the Dormition Fast, which every
        source treats as strict throughout except for one dated exception,
        the Transfiguration itself (Aug 6). So this is fixed in
        _apply_fasting_adjustments (the feast_level < 7 cap below
        Transfiguration's own rank), not by editing any row's stored
        fast_exception -- the same underlying data (Vigil rank included)
        now produces the correct outcome for both traditions.

        Aug 13 (Leavetaking of the Transfiguration, feast_level=4) is
        caught by the same general rule for the same reason: no source
        checked lists it as a second fish day -- every one names only
        Aug 6."""

        cases = [
            (8, 9, 'Herman of Alaska Vigil feast'),
            (8, 13, 'Leavetaking of the Transfiguration'),
        ]

        for month, day, label in cases:
            with self.subTest(label):
                slavic = liturgics.Day(2026, month, day, tradition=Tradition.Slavic)
                greek = liturgics.Day(2026, month, day, tradition=Tradition.Greek)
                await slavic.ainitialize()
                await greek.ainitialize()

                self.assertEqual(slavic.fast_exception_desc, 'Wine and Oil are Allowed')
                self.assertEqual(greek.fast_exception_desc, 'Wine and Oil are Allowed')

        # Transfiguration itself (Aug 6, feast_level=8) is the one dated
        # exception and must be unaffected by the cap.
        transfiguration = liturgics.Day(2026, 8, 6, tradition=Tradition.Slavic)
        await transfiguration.ainitialize()
        self.assertEqual(transfiguration.fast_exception_desc, 'Fish, Wine and Oil are Allowed')

    async def test_lenten_wine_oil_exceptions_greek_stricter_than_slavic(self):
        """OCA's published Lenten rule grants a wine-and-oil exception on
        three specific occasions when they fall on an ordinary weekday: the
        Forefeast of the Annunciation (Mar 24), and Wednesday/Friday of the
        fifth week (the Great Canon and Akathist Hymn vigils,
        respectively). Confirmed empirically against antiochian.org's own
        fastDesignation field (not just parish paraphrases) across 4-5
        independent years each: Antiochian/Greek practice does NOT grant
        this exception for any of the three -- they stay fully strict. This
        is a genuine Day-row split (Mar 24 is a fixed month/day date; the
        fifth-week Wednesday/Friday are pdist-anchored, pdist -18 and -16),
        not a code-level difference -- unlike the Nativity Fast, this one
        needed a data change. See docs/greek-fasting.md."""

        # 2025: Pascha Apr 20, so Mar 24 and the fifth week (Mar 31 - Apr 6)
        # both land on ordinary Lenten weekdays with no overriding feast.
        for dt in (date(2025, 3, 24), date(2025, 4, 2), date(2025, 4, 4)):
            with self.subTest(dt):
                slavic = liturgics.Day(dt.year, dt.month, dt.day, tradition=Tradition.Slavic)
                greek = liturgics.Day(dt.year, dt.month, dt.day, tradition=Tradition.Greek)
                await slavic.ainitialize()
                await greek.ainitialize()

                self.assertEqual(slavic.fast_exception_desc, 'Wine and Oil are Allowed')
                self.assertEqual(greek.fast_exception_desc, '')


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

    def test_fast_abstentions_for_every_fast_exception(self):
        """fast_abstentions_for canonicalizes every legacy fast_exception
        index (0-11) onto a dietary rung -- covers all values actually
        present in the Day fixture data, not just the ones
        test_fasting_levels happens to exercise via the Apostles Fast."""

        data = [
            (0,  ['meat', 'fish', 'dairy', 'eggs', 'wine', 'oil']),  # no annotation -> strict
            (1,  ['meat', 'fish', 'dairy', 'eggs']),                 # wine and oil allowed
            (2,  ['meat', 'dairy', 'eggs']),                         # fish, wine, oil allowed
            (3,  ['meat', 'fish', 'dairy', 'eggs']),                 # duplicate text of 1
            (4,  ['meat', 'dairy', 'eggs']),                         # duplicate text of 2
            (5,  ['meat', 'fish', 'dairy', 'eggs', 'oil']),          # wine only
            (6,  ['meat', 'fish', 'dairy', 'eggs']),                 # wine, oil, caviar (Lazarus Saturday)
            (7,  ['meat']),                                          # meat fast (e.g. Cheesefare week)
            (8,  ['meat', 'fish', 'dairy', 'eggs']),                 # "strict fast (wine and oil)"
            (9,  ['meat', 'fish', 'dairy', 'eggs', 'wine', 'oil']),  # strict fast
            (10, ['meat', 'fish', 'dairy', 'eggs', 'wine', 'oil']),  # no overrides -> strict
            (11, []),                                                 # fast free
        ]

        for fast_exception, expected in data:
            with self.subTest(fast_exception):
                actual = datetools.fast_abstentions_for(datetools.FastLevels.LentenFast, fast_exception)
                self.assertEqual(actual, expected)

    def test_fast_abstentions_for_no_fast_is_always_empty(self):
        for fast_exception in range(12):
            with self.subTest(fast_exception):
                actual = datetools.fast_abstentions_for(datetools.FastLevels.NoFast, fast_exception)
                self.assertEqual(actual, [])

    async def test_day_fast_abstentions_desc_on_real_dates(self):
        """Integration check against real calendar dates, cross-referencing
        each fast_exception's actual meaning rather than trusting the table
        in isolation: Aug 29/Sep 14 carry fast_exception=8, Dec 24 carries 9,
        and ordinary non-Lenten Wed/Fri carry 0."""

        data = [
            (2024, 8, 29, 'Abstain from meat, fish, dairy, and eggs'),   # Beheading of John the Baptist
            (2024, 9, 14, 'Abstain from meat, fish, dairy, and eggs'),   # Exaltation of the Cross
            (2024, 12, 24, 'Abstain from meat, fish, dairy, eggs, wine, and oil'),  # Nativity Eve
            (2024, 10, 2, 'Abstain from meat, fish, dairy, eggs, wine, and oil'),   # ordinary Wednesday
            (2018, 12, 26, ''),  # fast-free (Synaxis of the Theotokos)
        ]

        for year, month, day, expected in data:
            d = liturgics.Day(year, month, day)
            await d.ainitialize()
            with self.subTest((year, month, day)):
                self.assertEqual(d.fast_abstentions_desc, expected)

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

    async def test_translation_selection(self):
        """Passing translation=Translation.LXX2012WEB should change the
        wording of both Old and New Testament passages, while the default
        (translation=None) should keep resolving to KJV, unchanged."""

        # A Lenten weekday with a plain (non-Composite) Old Testament reading.
        # fetch_content=True is required -- it's what actually threads
        # Day.translation through to the passage fetch; calling
        # pericope.aget_passage() directly afterwards would bypass that and
        # re-resolve the default translation instead.
        kjv_day = liturgics.Day(2023, 3, 30)
        await kjv_day.ainitialize()
        kjv_readings = await kjv_day.aget_readings(fetch_content=True)
        self.assertEqual(kjv_readings[1].pericope.sdisplay, 'Gen 18.20-33')
        kjv_genesis = kjv_readings[1].pericope.passage

        lxx_day = liturgics.Day(2023, 3, 30, translation=Translation.LXX2012WEB)
        await lxx_day.ainitialize()
        lxx_readings = await lxx_day.aget_readings(fetch_content=True)
        lxx_genesis = lxx_readings[1].pericope.passage

        self.assertNotEqual(kjv_genesis[0].content, lxx_genesis[0].content)
        self.assertEqual(kjv_genesis[0].translation, 'kjv')
        self.assertEqual(lxx_genesis[0].translation, 'lxx2012-web')

        # A day with a plain Gospel reading, to confirm the New Testament
        # half (WEB) is threaded through too, not just the Old Testament half.
        kjv_day = liturgics.Day(2022, 1, 7)
        await kjv_day.ainitialize()
        kjv_readings = await kjv_day.aget_readings(fetch_content=True)
        self.assertEqual(kjv_readings[2].pericope.sdisplay, 'John 1.29-34')
        kjv_gospel = kjv_readings[2].pericope.passage

        web_day = liturgics.Day(2022, 1, 7, translation=Translation.LXX2012WEB)
        await web_day.ainitialize()
        web_readings = await web_day.aget_readings(fetch_content=True)
        web_gospel = web_readings[2].pericope.passage

        self.assertNotEqual(kjv_gospel[0].content, web_gospel[0].content)

    async def test_new_style_commemoration_on_civil_date_in_julian_mode(self):
        """Issue #146: modern (new_style) commemorations are recorded
        against the civil/Gregorian date and observed there by both Old-
        and New-Calendar jurisdictions alike -- unlike the traditional
        Menaion, whose dates genuinely shift in Julian mode. St Herman of
        Alaska's 1970 Glorification is stored at civil Aug 9; a Julian-mode
        request for that same civil day should surface it."""

        day = liturgics.Day(2026, 8, 9, calendar=datetools.Calendar.Julian)
        await day.ainitialize()
        self.assertTrue(any('Herman of Alaska' in s for s in day.saints))

    async def test_new_style_commemoration_not_shown_on_shifted_julian_label_date(self):
        """The flip side of the above: whichever civil day's Julian-shifted
        label happens to land on 8/9 must NOT show Herman's Glorification --
        that would be the original #146 bug (a modern commemoration bleeding
        onto an unrelated, Julian-recomputed day)."""

        day = liturgics.Day(2026, 8, 22, calendar=datetools.Calendar.Julian)
        await day.ainitialize()
        self.assertEqual((day.month, day.day), (8, 9))
        self.assertFalse(any('Herman of Alaska' in s for s in day.saints))

    async def test_new_style_commemoration_unaffected_in_gregorian_mode(self):
        """In Gregorian mode self.month/self.day already equal the civil
        date, so new_style commemorations should behave exactly as any
        other -- no exclusion, no re-fetch."""

        day = liturgics.Day(2026, 8, 9, calendar=datetools.Calendar.Gregorian)
        await day.ainitialize()
        self.assertTrue(any('Herman of Alaska' in s for s in day.saints))

    async def test_matrona_of_moscow_new_style_civil_date(self):
        day = liturgics.Day(2026, 5, 2, calendar=datetools.Calendar.Julian)
        await day.ainitialize()
        self.assertTrue(any('Matrona' in s for s in day.saints))

    async def test_alexis_toth_new_style_civil_date(self):
        day = liturgics.Day(2026, 5, 7, calendar=datetools.Calendar.Julian, tradition=Tradition.Slavic)
        await day.ainitialize()
        self.assertTrue(any('Alexis Toth' in s for s in day.saints))

    async def test_tradition_specific_commemoration_is_additive_not_a_replacement(self):
        """DayCommemoration.tradition (Stage 6) supplements a day's common
        commemorations rather than replacing the whole day -- Jan 18 lists
        Athanasius/Cyril for everyone, plus Zenia the Martyr only for the
        Greek tradition, on top of the same shared Athanasius/Cyril entry
        (not instead of it)."""

        slavic = liturgics.Day(2026, 1, 18, tradition=Tradition.Slavic)
        await slavic.ainitialize()
        greek = liturgics.Day(2026, 1, 18, tradition=Tradition.Greek)
        await greek.ainitialize()

        self.assertTrue(any('Athanasius' in s for s in slavic.saints))
        self.assertFalse(any('Zenia' in s for s in slavic.saints))

        self.assertTrue(any('Athanasius' in s for s in greek.saints))
        self.assertTrue(any('Zenia' in s for s in greek.saints))

    async def test_greek_gap_dates_share_confirmed_common_saints(self):
        """Stage 9: 6 dates had their only commemorations attached to a Day
        row tagged tradition='slavic' (with an empty parallel greek Day row
        winning _prefer_tradition_days), so Greek users saw nothing at all,
        not even genuinely shared content. Fixed by decoupling
        DayCommemoration lookup from _prefer_tradition_days's single-winner
        Day row (see _add_supplemental_commemorations) and tagging
        individual DayCommemoration rows tradition='slavic' for saints
        confirmed absent from data/antiochian_fixed_saints.json (the
        project's own Antiochian harvest) -- Toth and Nevsky in particular.
        feast_level/fast/fast_exception are untouched by any of this, since
        they still come solely from _prefer_tradition_days's Day-row
        selection -- verified directly against production (all field-level
        values match exactly; the only saints-list difference from
        production is the intentional Herman's-Glorification addition,
        the #146 fix)."""

        cases = [
            (2, 27, ['Procopius'], ['Raphael', 'Titus', 'Leander']),
            (5, 7, ['Apparition', 'Acacius'], ['Toth', 'Georgia', 'Lydia']),
            (8, 9, ['Matthias', 'Anthony', 'Herman of Alaska'], []),
            (10, 31, ['Stachys', 'Nicholas of Chios'], []),
            (11, 23, ['Amphilocus'], ['Nevsky', 'Columban']),
        ]
        for m, d, shared, slavic_only in cases:
            greek = liturgics.Day(2026, m, d, tradition=Tradition.Greek)
            await greek.ainitialize()
            with self.subTest((m, d)):
                for fragment in shared:
                    self.assertTrue(
                        any(fragment in s for s in greek.saints),
                        f'{fragment!r} missing from greek {m}/{d}: {greek.saints}',
                    )
                for fragment in slavic_only:
                    self.assertFalse(
                        any(fragment in s for s in greek.saints),
                        f'{fragment!r} unexpectedly leaked to greek {m}/{d}: {greek.saints}',
                    )

        # July 5 -- Sergius/Athanasius are feast_name-matched (day_native,
        # ordering=-1) on the *slavic* Day row, which loses Greek's
        # feast-level-facts preference to the empty greek placeholder --
        # so their feast_name never surfaces via greek.feasts at all, and
        # they fall back to showing plainly via greek.saints instead (see
        # the winning_day_ids check in _add_supplemental_commemorations).
        slavic_jul5 = liturgics.Day(2026, 7, 5, tradition=Tradition.Slavic)
        await slavic_jul5.ainitialize()
        self.assertIn('Unc. Rel. Ven. Sergius of Radonezh; Ven. Athanasius of Athos', slavic_jul5.feasts)
        self.assertFalse(any('Sergius of Radonezh' in s for s in slavic_jul5.saints))
        self.assertFalse(any('Athanasius of Mt Athos' in s for s in slavic_jul5.saints))

        greek_jul5 = liturgics.Day(2026, 7, 5, tradition=Tradition.Greek)
        await greek_jul5.ainitialize()
        self.assertEqual(greek_jul5.feasts, [])
        self.assertTrue(any('Sergius of Radonezh' in s for s in greek_jul5.saints))
        self.assertTrue(any('Athanasius of Mt Athos' in s for s in greek_jul5.saints))

    async def test_raphael_brooklyn_full_year_check_unaffected(self):
        """Feb 27's feast_name (Raphael-specific) must still never leak to
        Greek even though Procopius, the other saint on that date, is now
        correctly shared (see test_greek_gap_dates_share_confirmed_common_saints)
        -- Raphael needs full exclusion from Greek even at the feast_name
        level (he's on a moveable date instead, see
        test_raphael_brooklyn_differing_commemoration_date). feast_name is
        untouched by DayCommemoration.tradition, since it still comes
        solely from _prefer_tradition_days's Day-row selection."""

        greek = liturgics.Day(2026, 2, 27, tradition=Tradition.Greek)
        await greek.ainitialize()
        self.assertNotIn('St Raphael Bishop of Brooklyn', greek.feasts)
