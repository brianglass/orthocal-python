from datetime import timedelta

from ask_sdk_core.response_helper import ResponseFactory
from django.test import TestCase
from django.utils import timezone

from .. import liturgics, speech


class SpeechTestCase(TestCase):
    fixtures = ['calendarium.json']

    def test_human_join(self):
        items = 'Anthony', 'Athanasius', 'Cyril'
        expected = 'Anthony, Athanasius and Cyril'
        actual = speech.human_join(items)
        self.assertEqual(expected, actual)

    async def test_when_speech_tomorrow(self):
        now = timezone.localtime()
        tomorrow = now + timedelta(days=1)

        day = liturgics.Day(tomorrow.year, tomorrow.month, tomorrow.day)
        await day.ainitialize()
        actual = speech.when_speech(day)

        self.assertIn('Tomorrow', actual)
        self.assertNotIn('Today', actual)

    async def test_when_speech_today(self):
        now = timezone.localtime()
        later = now + timedelta(hours=2)

        day = liturgics.Day(later.year, later.month, later.day)
        await day.ainitialize()
        actual = speech.when_speech(day)

        self.assertIn('Today', actual)
        self.assertNotIn('Tomorrow', actual)

    def test_day_speech(self):
        builder = ResponseFactory()

        day = liturgics.Day(2023, 1, 7)
        day.initialize()

        speech_text, card_text = speech.day_speech(day)

        self.assertIn('Theophany', speech_text)
        self.assertIn('Theophany', card_text)

    def test_fasting_speech(self):
        day = liturgics.Day(2023, 1, 5)
        day.initialize()

        actual = speech.fasting_speech(day)
        self.assertIn('On this day there is a fast', actual)

    def test_fasting_speech_great(self):
        day = liturgics.Day(2023, 2, 28)
        day.initialize()

        actual = speech.fasting_speech(day)
        self.assertIn('This day is during', actual)

    def test_fasting_speech_no(self):
        day = liturgics.Day(2023, 1, 10)
        day.initialize()

        actual = speech.fasting_speech(day)
        self.assertIn('no fast', actual)

    def test_expand_abbreviations(self):
        text = 'Ss Cyril and Athanasius along with Ven. Bede'
        actual = speech.expand_abbreviations(text)
        self.assertIn('Saints', actual)
        self.assertIn('Venerable', actual)

    def test_estimate_group_size_long(self):
        day = liturgics.Day(2023, 4, 14)
        day.initialize()
        readings = day.get_readings()
        passage = readings[0].get_passage()
        size = speech.estimate_group_size(passage)

        # This passage should have 3 groups of 42 verses
        self.assertEqual(42, size)

    def test_estimate_group_size_short(self):
        day = liturgics.Day(2023, 1, 18)
        day.initialize()
        readings = day.get_readings()
        passage = readings[0].get_passage()

        size = speech.estimate_group_size(passage)
        self.assertIs(size, None)
