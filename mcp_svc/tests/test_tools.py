from django.test import TestCase

from calendarium.datetools import Tradition

from ..tools import get_day, search_saints


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
        with self.assertRaises(ValueError):
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

    async def test_tradition_filtering_excludes_other_traditions_saint(self):
        greek_results = await search_saints('Zenia', tradition=Tradition.Greek)
        self.assertTrue(greek_results)

        slavic_results = await search_saints('Zenia', tradition=Tradition.Slavic)
        self.assertEqual(slavic_results, [])
