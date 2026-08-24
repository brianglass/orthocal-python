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

    def test_douay_rheims_strongs_tags_stripped(self):
        """Douay-Rheims verses are word-tagged with Strong's numbers
        (<w s="G3056">Word</w>), unlike the other translations already
        ingested. parse_usfx() has no explicit case for <w>, so this
        confirms the tags don't leak into the content and word spacing
        still comes out correct."""
        expected = 'In the beginning was the Word, and the Word was with God, and the Word was God.'
        verse = Verse.objects.get(book='JHN', chapter=1, verse=1, language='en', translation='douay-rheims')
        self.assertEqual(expected, verse.content)
        self.assertNotIn('G3056', verse.content)

    def test_lxx2012_plural_you_marker_preserved(self):
        """LXX2012's source file documents (in its own front matter) that
        U+2303 (UP ARROWHEAD) glued onto "you"/"You" is a deliberate mark
        for 2nd-person *plural* ("ye"), not a stray artifact -- modern
        English has no distinct plural "you". parse_usfx() must preserve
        it in stored content; rendering it legibly is a template-layer
        concern (see scripture_extras.mark_plural_you)."""
        expected = 'And if you⌃ be willing, and listen to me, you⌃ shall eat the good of the land:'
        verse = Verse.objects.get(book='ISA', chapter=1, verse=19, language='en', translation='lxx2012-web')
        self.assertEqual(expected, verse.content)
