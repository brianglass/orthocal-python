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

    async def test_day_speech(self):
        builder = ResponseFactory()

        day = liturgics.Day(2023, 1, 7)
        await day.ainitialize()

        card = speech.day_speech(builder, day)

        self.assertIn('Theophany', builder.response.output_speech.ssml)
        self.assertIn('Theophany', card)

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
