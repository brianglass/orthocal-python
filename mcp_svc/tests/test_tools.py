from django.test import TestCase
from mcp.server.mcpserver.exceptions import ToolError

from calendarium.datetools import Tradition

from ..tools import get_day, get_saint, search_feasts, search_saints


class GetDayTestCase(TestCase):
    async def test_normal_date(self):
        result = await get_day(2026, 7, 31)

        self.assertEqual(result['year'], 2026)
        self.assertEqual(result['month'], 7)
        self.assertEqual(result['day'], 31)
        self.assertIn('readings', result)
        self.assertTrue(result['readings'])
        self.assertIn('saints', result)
        self.assertIn('fast_level_desc', result)

    async def test_out_of_range_date_raises(self):
        with self.assertRaises(ToolError):
            await get_day(2026, 2, 30)

    async def test_translation_changes_passage_content(self):
        kjv_result = await get_day(2022, 1, 7, translation='kjv')
        lxx_result = await get_day(2022, 1, 7, translation='lxx2012-web')

        kjv_gospel = kjv_result['readings'][2]
        lxx_gospel = lxx_result['readings'][2]

        self.assertEqual(kjv_gospel['display'], 'John 1.29-34')
        self.assertEqual(lxx_gospel['display'], 'John 1.29-34')
        self.assertNotEqual(kjv_gospel['passage'][0]['content'], lxx_gospel['passage'][0]['content'])

    async def test_default_translation_is_lxx2012_web(self):
        default_result = await get_day(2022, 1, 7)
        lxx_result = await get_day(2022, 1, 7, translation='lxx2012-web')

        self.assertEqual(
            default_result['readings'][2]['passage'][0]['content'],
            lxx_result['readings'][2]['passage'][0]['content'],
        )


class SearchSaintsTestCase(TestCase):
    async def test_finds_matching_saint(self):
        results = await search_saints('Seraphim of Sarov')

        self.assertTrue(any('Seraphim of Sarov' in r['title'] for r in results))
        for r in results:
            self.assertIn('month', r)
            self.assertIn('day', r)

    async def test_full_name_present_and_occasion_independent(self):
        results = await search_saints('Seraphim of Sarov')

        # Both occasions (repose, relics-uncovering) share one Saint identity
        # since the saint-dedup pass, so full_name should be identical across
        # both results even though title differs per occasion.
        full_names = {r['full_name'] for r in results if r['matched'] == 'name'}
        self.assertEqual(full_names, {'St Seraphim of Sarov (1833)'})

    async def test_no_match_returns_empty_list(self):
        results = await search_saints('Nonexistent Saint Name Xyz')

        self.assertEqual(results, [])

    async def test_full_name_orders_multiple_saints_correctly(self):
        results = await search_saints('Athanasius the Great')

        joint = next(r for r in results if r['month'] == 1 and r['day'] == 18)
        self.assertEqual(
            joint['full_name'],
            'St Athanasius the Great, patriarch of Alexandria and St Cyril, archbishop of Alexandria (444)',
        )

    async def test_searches_every_tradition(self):
        # St Xenia of Rome (spelled Zenia here) is kept only in the Greek
        # tradition, St Seraphim of Sarov in both.
        self.assertEqual({r['tradition'] for r in await search_saints('Zenia')}, {'greek'})
        self.assertIn('common', {r['tradition'] for r in await search_saints('Seraphim of Sarov')})

    async def test_results_flag_stories_without_including_them(self):
        results = await search_saints('Seraphim of Sarov')

        self.assertTrue(any(r['has_story'] for r in results))
        for r in results:
            self.assertNotIn('story', r)
            self.assertTrue(r['saint_slugs'])

        storyless = await search_saints('Anthimos, President of Crete')
        self.assertEqual([r['has_story'] for r in storyless if r['matched'] == 'name'], [False])

    async def test_joint_commemoration_lists_every_saints_slug(self):
        results = await search_saints('Athanasius the Great')

        joint = next(r for r in results if r.get('month') == 1 and r.get('day') == 18)
        self.assertEqual(len(joint['saint_slugs']), 2)

    async def test_name_matches_come_first(self):
        results = await search_saints('Seraphim of Sarov')

        matched = [r['matched'] for r in results]
        self.assertEqual(matched, sorted(matched, key=['name', 'life'].index))
        self.assertEqual(matched[0], 'name')

    async def test_description_finds_saints_by_their_lives(self):
        # Diomedes has "the Physician" in his name; Panteleimon doesn't.
        results = [r for r in await search_saints('physician') if r['matched'] == 'life']

        self.assertTrue(results)
        for r in results:
            self.assertIn('physician', r['excerpt'].lower())
            self.assertNotIn('story', r)
            self.assertTrue(r['saint_slugs'])
            self.assertTrue(r['has_story'])
        self.assertTrue(any('Panteleimon' in r['title'] for r in results))

    async def test_life_matches_are_limited(self):
        from ..tools import LIFE_MATCH_LIMIT

        results = await search_saints('monastery')

        self.assertEqual(sum(r['matched'] == 'life' for r in results), LIFE_MATCH_LIMIT)

    async def test_life_matches_cover_every_tradition(self):
        # Only the Greek-tradition life of St Jacob of Evia mentions Livisi,
        # his birthplace.
        results = await search_saints('Livisi')

        jacob = next(r for r in results if 'Jacob of Evia' in r['title'])
        self.assertEqual((jacob['matched'], jacob['tradition']), ('life', 'greek'))

    async def test_moveable_commemoration_has_no_month_or_day(self):
        results = await search_saints('Mary of Egypt')

        lenten_sunday = next(r for r in results if r.get('moveable'))
        self.assertEqual(lenten_sunday['pascha_distance'], -14)
        self.assertNotIn('month', lenten_sunday)


class GetSaintTestCase(TestCase):
    async def _slug(self, query):
        return (await search_saints(query))[0]['saint_slugs'][0]

    async def test_returns_every_occasion_with_its_story(self):
        slug = await self._slug('Seraphim of Sarov')

        saint = await get_saint(slug)

        self.assertEqual(saint['slug'], slug)
        self.assertEqual(saint['name'], 'St Seraphim of Sarov (1833)')
        self.assertTrue(saint['url'].endswith(f'/saints/{slug}/'))
        self.assertGreaterEqual(len(saint['commemorations']), 2)
        self.assertTrue(all(c['story'] for c in saint['commemorations']))

    async def test_story_is_null_when_there_is_none(self):
        slug = await self._slug('Anthimos, President of Crete')

        saint = await get_saint(slug, tradition=Tradition.Greek)

        self.assertEqual([c['story'] for c in saint['commemorations']], [None])

    async def test_tradition_filters_occasions(self):
        slug = await self._slug('Zenia')

        self.assertTrue((await get_saint(slug, tradition=Tradition.Greek))['commemorations'])
        self.assertEqual((await get_saint(slug, tradition=Tradition.Slavic))['commemorations'], [])

    async def test_float_occasion_is_moveable_without_a_pascha_distance(self):
        slug = await self._slug('Raphael Brooklyn')

        saint = await get_saint(slug, tradition=Tradition.Greek)

        floating = [c for c in saint['commemorations'] if c.get('moveable')]
        self.assertTrue(floating)
        for c in floating:
            self.assertNotIn('pascha_distance', c)
            self.assertNotIn('month', c)

    async def test_unknown_slug_raises(self):
        with self.assertRaises(ToolError):
            await get_saint('no-such-saint')


class SearchFeastsTestCase(TestCase):
    async def test_moveable_feast_has_this_years_date(self):
        result = await search_feasts('Palm Sunday', year=2027)

        palm_sunday = result['feasts'][0]
        self.assertEqual(palm_sunday['name'], 'Palm Sunday')
        self.assertEqual(palm_sunday['date'], '2027-04-25')
        self.assertEqual(palm_sunday['weekday'], 'Sunday')
        self.assertEqual(palm_sunday['pascha_distance'], -7)
        self.assertTrue(palm_sunday['moveable'])
        self.assertEqual(palm_sunday['url'], 'https://orthocal.info/readings/slavic/gregorian/2027/4/25/')

    async def test_words_match_the_starts_of_words(self):
        result = await search_feasts('Mid-Pentecost', year=2027)

        self.assertIn(('Midfeast of Pentecost', '2027-05-26'), [(f['name'], f['date']) for f in result['feasts']])

    async def test_feast_ranks_above_its_forefeasts_and_leavetaking(self):
        result = await search_feasts('Pascha', year=2026)

        self.assertEqual(result['feasts'][0]['date'], '2026-04-12')
        self.assertEqual(result['feasts'][0]['level'], 8)

    async def test_query_can_leave_out_words_the_name_lacks(self):
        result = await search_feasts('the Feast of the Ascension', year=2026)

        self.assertEqual(result['feasts'][0]['name'], 'Ascension of the Lord')
        self.assertEqual(result['feasts'][0]['date'], '2026-05-21')

    async def test_saint_may_be_spelled_out(self):
        for query in ('Nicholas', 'Saint Nicholas', 'St Nicholas Day'):
            with self.subTest(query=query):
                result = await search_feasts(query, year=2026)
                self.assertEqual(result['feasts'][0]['date'], '2026-12-06')

    async def test_julian_dates_are_civil_dates(self):
        result = await search_feasts('Theophany', year=2027, calendar='julian')

        theophany = result['feasts'][0]
        self.assertEqual(theophany['date'], '2027-01-19')
        self.assertEqual((theophany['month'], theophany['day']), (1, 6))

    async def test_tradition_chooses_the_feast(self):
        slavic = await search_feasts('Protection', year=2026)
        greek = await search_feasts('Protection', year=2026, tradition='greek')

        self.assertEqual([(f['date'], f['level']) for f in slavic['feasts']], [('2026-10-01', 6)])
        self.assertEqual([(f['date'], f['level']) for f in greek['feasts']], [('2026-10-28', 3)])

    async def test_counted_weekday_titles_are_not_searched(self):
        result = await search_feasts('Pentecost', year=2026)

        self.assertTrue(result['feasts'])
        for feast in result['feasts']:
            self.assertNotRegex(feast['name'], r'week after Pentecost')

    async def test_fasting_seasons_match_by_name(self):
        result = await search_feasts('Nativity Fast', year=2026, calendar='julian')

        self.assertEqual(
            [(s['start'], s['end']) for s in result['fasting_seasons']],
            [('2025-11-28', '2026-01-06'), ('2026-11-28', '2027-01-06')],
        )

    async def test_no_query_lists_the_years_great_feasts_and_fasts(self):
        result = await search_feasts(year=2026)

        names = [f['name'] for f in result['feasts']]
        self.assertIn('Palm Sunday', names)
        self.assertTrue(all(f['level'] >= 6 for f in result['feasts']))
        self.assertEqual([f['date'] for f in result['feasts']], sorted(f['date'] for f in result['feasts']))
        self.assertEqual(
            [s['name'] for s in result['fasting_seasons']],
            ['Lenten Fast', 'Apostles Fast', 'Dormition Fast', 'Nativity Fast'],
        )

    async def test_unknown_feast_returns_nothing(self):
        result = await search_feasts('Zzyzx')

        self.assertEqual(result['feasts'], [])
        self.assertEqual(result['fasting_seasons'], [])

    async def test_year_outside_the_supported_range_raises(self):
        with self.assertRaises(ToolError):
            await search_feasts('Pascha', year=1500)
