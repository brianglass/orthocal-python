from django.test import TestCase

from ..models import Verse


class ParseTest(TestCase):
    def test_gen_9_23(self):
        expected = 'And Shem and Japheth took a garment, and laid it upon both their shoulders, and went backward, and covered the nakedness of their father; and their faces were backward, and they saw not their father’s nakedness.'
        verse = Verse.objects.get(book='GEN', chapter=9, verse=23, language='en')
        self.assertEqual(expected, verse.content)
