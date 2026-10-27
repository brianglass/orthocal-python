from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .transliteration import normalize_transliteration


class NormalizeTransliterationTestCase(TestCase):
    def test_known_variant_pairs_match(self):
        pairs = [
            ('Athanasius', 'Athanasios'),
            ('Dionysius', 'Dionysios'),
            ('Sergius', 'Sergios'),
            ('Symeon', 'Simeon'),
            ('Cosmas', 'Kosmas'),
            ('Isaac', 'Isaak'),
            ('Maximovich', 'Maximovitch'),
        ]
        for latin, greek in pairs:
            self.assertEqual(normalize_transliteration(latin), normalize_transliteration(greek))


class SaintSearchTransliterationTestCase(TestCase):
    fixtures = ['calendarium.json', 'commemorations.json']

    def setUp(self):
        # Fixture loading bypasses Saint.save() (same reason `slug` needs
        # its own backfill command, see the model), so normalized_name and
        # slug are blank on freshly test-loaded fixture data unless
        # backfilled here -- mirrors what the Dockerfile does for a real
        # deployment.
        call_command('backfill_saint_slugs')
        call_command('backfill_saint_normalized_names')
        call_command('build_saint_search_index')

    def test_greek_spelling_finds_latin_spelled_saint(self):
        response = self.client.get(reverse('saint-search'), {'q': 'Athanasios'})

        names = [saint.display_name for saint in response.context['results']]
        self.assertIn('St Athanasius the Great, patriarch of Alexandria', names)

    def test_vitch_spelling_finds_vich_spelled_saint(self):
        # Two matches -- St John of Shanghai and San Francisco (has a
        # story) and St John Maximovitch, Metr. of Tobolsk (does not) --
        # so this shows a results list rather than redirecting.
        response = self.client.get(reverse('saint-search'), {'q': 'John Maximovitch'})

        results = {saint.display_name: saint.has_story for saint in response.context['results']}
        self.assertEqual(results, {
            'St John (Maximovich), Archbishop of Shanghai and San Francisco (1966) (June 19 OC)': True,
            'St John Maximovitch, Metropolitan of Tobolsk': False,
        })

    def test_transliteration_match_requires_word_boundary(self):
        # normalize_transliteration("Mary") -> "mari", which is a literal
        # prefix of unrelated names like "Marina" -- requiring a full-word
        # regex match (not icontains) on the normalized field avoids
        # matching those too.
        response = self.client.get(reverse('saint-search'), {'q': 'Mary'})

        pks = [saint.pk for saint in response.context['results']]
        self.assertNotIn(5334, pks)  # Greatmartyr Marina

    def test_no_story_result_has_no_link(self):
        response = self.client.get(reverse('saint-search'), {'q': 'John Maximovitch'})

        self.assertContains(response, 'St John Maximovitch, Metropolitan of Tobolsk')
        self.assertNotContains(response, reverse('saint-detail', args=['st-john-maximovitch-metropolitan-of-tobolsk-6-10']))

    def test_single_result_redirects_to_detail_page(self):
        response = self.client.get(reverse('saint-search'), {'q': 'myra Nicholas'})

        self.assertRedirects(response, reverse('saint-detail', args=['our-father-among-the-saints-nicholas-the-wonderworker-archbishop-of-myra-345-5-9']))


class LifeSearchTestCase(TestCase):
    fixtures = ['calendarium.json', 'commemorations.json']

    def setUp(self):
        call_command('backfill_saint_slugs')
        call_command('backfill_saint_normalized_names')
        call_command('build_saint_search_index')

    def _search(self, query, **headers):
        return self.client.get(reverse('saint-search'), {'q': query}, headers=headers)

    def test_description_finds_saints_by_their_lives(self):
        response = self._search('physician')

        # Diomedes has "the Physician" in his name; Panteleimon doesn't.
        names = [saint.display_name for saint in response.context['life_results']]
        self.assertTrue(any('Panteleimon' in name for name in names), names)
        self.assertContains(response, 'Found in their lives')
        self.assertContains(response, '<mark>physician</mark>')

    def test_words_can_span_names_and_life(self):
        # "Cosmas" is in the Unmercenaries' names, "physician" only in their
        # lives.
        names = [saint.display_name for saint in self._search('Cosmas physician').context['life_results']]

        self.assertTrue(names)
        self.assertTrue(all('Cosmas' in name or 'Damian' in name for name in names), names)

    def test_last_word_matches_as_a_prefix(self):
        # The page searches as you type.
        names = [saint.display_name for saint in self._search('physic').context['life_results']]

        self.assertTrue(any('Panteleimon' in name for name in names), names)

    def test_name_matches_are_not_repeated_from_the_lives(self):
        response = self._search('Seraphim Sarov', **{'HX-Request': 'true'})

        named = {saint.pk for saint in response.context['results']}
        self.assertTrue(named)
        self.assertFalse(named & {saint.pk for saint in response.context['life_results']})
        self.assertContains(response, 'By name')

    def test_query_syntax_is_taken_literally(self):
        for query in ('NOT "x', 'Myrrh-gusher', 'title:Nicholas', '*', '"'):
            self.assertEqual(self._search(query, **{'HX-Request': 'true'}).status_code, 200, query)

    def test_excerpts_are_escaped(self):
        from .search import LifeMatch

        match = LifeMatch(1, 'a <b> & \x02c\x03')
        self.assertEqual(match.excerpt_html(), 'a &lt;b&gt; &amp; <mark>c</mark>')
        self.assertEqual(match.excerpt_text(), 'a <b> & c')

    def test_rebuilding_the_index_replaces_it(self):
        from django.db import connection

        from .models import DayCommemoration
        from .search import LIFE_SEARCH_TABLE

        call_command('build_saint_search_index')
        with connection.cursor() as cursor:
            cursor.execute(f'SELECT count(*) FROM {LIFE_SEARCH_TABLE}')
            self.assertEqual(cursor.fetchone()[0], DayCommemoration.objects.count())

    def test_index_holds_text_without_markup(self):
        from django.db import connection

        from .search import LIFE_SEARCH_TABLE

        with connection.cursor() as cursor:
            cursor.execute(f"SELECT count(*) FROM {LIFE_SEARCH_TABLE} WHERE story LIKE '%<p>%'")
            self.assertEqual(cursor.fetchone()[0], 0)


class CanonicalLinkTestCase(TestCase):
    fixtures = ['calendarium.json', 'commemorations.json']

    def setUp(self):
        call_command('backfill_saint_slugs')

    def test_content_pages_name_their_canonical_url(self):
        from commemorations.models import Saint

        saint = Saint.objects.first()
        urls = [
            reverse('saint-detail', args=[saint.slug]),
            reverse('saint-search'),
            reverse('about'),
            reverse('ai-assistant'),
            reverse('alexa'),
            reverse('api'),
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertContains(response, f'<link rel="canonical" href="http://testserver{url}">', msg_prefix=url)

    def test_search_results_point_to_the_plain_search_page(self):
        response = self.client.get(reverse('saint-search'), {'q': 'zzzz'})
        self.assertContains(response, f'<link rel="canonical" href="http://testserver{reverse("saint-search")}">')
