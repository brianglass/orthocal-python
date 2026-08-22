from django.test import TestCase

from ..templatetags.scripture_extras import keep_numeral_with_book


class KeepNumeralWithBookTestCase(TestCase):
    def test_joins_leading_numeral_to_book_name(self):
        self.assertEqual(
            '1\N{NO-BREAK SPACE}Corinthians 15.1-11',
            keep_numeral_with_book('1 Corinthians 15.1-11'),
        )

    def test_only_replaces_the_leading_space(self):
        """Only the space right after the numeral is non-breaking --
        everything else in the reference should stay normally wrappable."""
        result = keep_numeral_with_book('2 Thessalonians 1.1-2.2')
        self.assertEqual('2\N{NO-BREAK SPACE}Thessalonians 1.1-2.2', result)
        self.assertIn(' ', result)

    def test_leaves_references_without_a_leading_numeral_unchanged(self):
        self.assertEqual('Mark 3.13-21', keep_numeral_with_book('Mark 3.13-21'))
