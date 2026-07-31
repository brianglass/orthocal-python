from django.test import TestCase

from ..models import Verse


class ParseTest(TestCase):
    def test_gen_9_23(self):
        expected = 'And Shem and Japheth took a garment, and laid it upon both their shoulders, and went backward, and covered the nakedness of their father; and their faces were backward, and they saw not their father’s nakedness.'
        verse = Verse.objects.get(book='GEN', chapter=9, verse=23, language='en', translation='kjv')
        self.assertEqual(expected, verse.content)

    def test_web_cross_references_stripped(self):
        """WEB annotates verses with <x> cross-reference elements (e.g.
        pointing Heb 11:33 back to Daniel 6) that aren't part of the verse
        text itself. These must not leak into the stored content the way
        <f> footnotes were already excluded."""
        expected = 'who through faith subdued kingdoms, worked out righteousness, obtained promises, stopped the mouths of lions,'
        verse = Verse.objects.get(book='HEB', chapter=11, verse=33, language='en', translation='lxx2012-web')
        self.assertEqual(expected, verse.content)
        self.assertNotIn('Daniel', verse.content)
