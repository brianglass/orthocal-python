from django.core.management import call_command
from django.test import TestCase
from mcp.server.mcpserver.exceptions import ToolError

from calendarium.datetools import Tradition

from ..tools import get_day, get_saint, search_saints


def _backfill_saints():
    # Fixture loading bypasses Saint.save(), so slug and normalized_name are
    # blank until backfilled -- mirrors the Dockerfile (see
    # commemorations/tests.py).
    call_command('backfill_saint_slugs')
    call_command('backfill_saint_normalized_names')


class GetDayTestCase(TestCase):
    fixtures = ['calendarium.json', 'commemorations.json']

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
    fixtures = ['calendarium.json', 'commemorations.json']

    def setUp(self):
        _backfill_saints()

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
        full_names = {r['full_name'] for r in results}
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

    async def test_tradition_filtering_excludes_other_traditions_saint(self):
        greek_results = await search_saints('Zenia', tradition=Tradition.Greek)
        self.assertTrue(greek_results)

        slavic_results = await search_saints('Zenia', tradition=Tradition.Slavic)
        self.assertEqual(slavic_results, [])

    async def test_results_flag_stories_without_including_them(self):
        results = await search_saints('Seraphim of Sarov')

        self.assertTrue(any(r['has_story'] for r in results))
        for r in results:
            self.assertNotIn('story', r)
            self.assertTrue(r['saint_slugs'])

        storyless = await search_saints('Anthimos, President of Crete', tradition=Tradition.Greek)
        self.assertEqual([r['has_story'] for r in storyless], [False])

    async def test_joint_commemoration_lists_every_saints_slug(self):
        results = await search_saints('Athanasius the Great')

        joint = next(r for r in results if r.get('month') == 1 and r.get('day') == 18)
        self.assertEqual(len(joint['saint_slugs']), 2)

    async def test_moveable_commemoration_has_no_month_or_day(self):
        results = await search_saints('Mary of Egypt')

        lenten_sunday = next(r for r in results if r.get('moveable'))
        self.assertEqual(lenten_sunday['pascha_distance'], -14)
        self.assertNotIn('month', lenten_sunday)


class GetSaintTestCase(TestCase):
    fixtures = ['calendarium.json', 'commemorations.json']

    def setUp(self):
        _backfill_saints()

    async def _slug(self, query, tradition=Tradition.Slavic):
        return (await search_saints(query, tradition=tradition))[0]['saint_slugs'][0]

    async def test_returns_every_occasion_with_its_story(self):
        slug = await self._slug('Seraphim of Sarov')

        saint = await get_saint(slug)

        self.assertEqual(saint['slug'], slug)
        self.assertEqual(saint['name'], 'St Seraphim of Sarov (1833)')
        self.assertTrue(saint['url'].endswith(f'/saints/{slug}/'))
        self.assertGreaterEqual(len(saint['commemorations']), 2)
        self.assertTrue(all(c['story'] for c in saint['commemorations']))

    async def test_story_is_null_when_there_is_none(self):
        slug = await self._slug('Anthimos, President of Crete', Tradition.Greek)

        saint = await get_saint(slug, tradition=Tradition.Greek)

        self.assertEqual([c['story'] for c in saint['commemorations']], [None])

    async def test_tradition_filters_occasions(self):
        slug = await self._slug('Zenia', Tradition.Greek)

        self.assertTrue((await get_saint(slug, tradition=Tradition.Greek))['commemorations'])
        self.assertEqual((await get_saint(slug, tradition=Tradition.Slavic))['commemorations'], [])

    async def test_float_occasion_is_moveable_without_a_pascha_distance(self):
        slug = await self._slug('Raphael Brooklyn', Tradition.Greek)

        saint = await get_saint(slug, tradition=Tradition.Greek)

        floating = [c for c in saint['commemorations'] if c.get('moveable')]
        self.assertTrue(floating)
        for c in floating:
            self.assertNotIn('pascha_distance', c)
            self.assertNotIn('month', c)

    async def test_unknown_slug_raises(self):
        with self.assertRaises(ToolError):
            await get_saint('no-such-saint')
