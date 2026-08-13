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
        ]
        for latin, greek in pairs:
            self.assertEqual(normalize_transliteration(latin), normalize_transliteration(greek))


class SaintSearchTransliterationTestCase(TestCase):
    fixtures = ['calendarium.json', 'commemorations.json']

    def setUp(self):
        # Fixture loading bypasses Saint.save() (same reason `slug` needs
        # its own backfill command, see the model), so normalized_name is
        # blank on freshly test-loaded fixture data unless backfilled here
        # -- mirrors what the Dockerfile does for a real deployment.
        call_command('backfill_saint_normalized_names')

    def test_greek_spelling_finds_latin_spelled_saint(self):
        response = self.client.get(reverse('saint-search'), {'q': 'Athanasios'})

        names = [saint.display_name for saint in response.context['results']]
        self.assertIn('St Athanasius the Great, patriarch of Alexandria', names)
