from datetime import timedelta

from ask_sdk_core.response_helper import ResponseFactory
from django.test import TestCase
from django.utils import timezone

from .. import speech
from calendarium import liturgics


class SpeechTestCase(TestCase):
    fixtures = ['calendarium.json', 'commemorations.json']

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
        data = [
            ('Ss Cyril and Athanasius along with Ven. Bede', '<sub alias="Saints">Ss</sub> Cyril and Athanasius along with <sub alias="The Venerable">Ven.</sub> Bede'),
            ('The most Holy Theotokos.', 'The most Holy <phoneme alphabet="ipa" ph="θɛːoʊtˈoʊˌkoʊs">Theotokos</phoneme>.'),
            ('The most Holytheotokos.', 'The most Holytheotokos.')
        ]
        for text, expected in data:
            with self.subTest(text):
                actual = speech.expand_abbreviations(text)
                self.assertEqual(expected, actual)

        #actual = speech.expand_abbreviations(text)
        #self.assertIn('Saints', actual)
        #self.assertIn('Venerable', actual)

    def test_estimate_group_size_long(self):
        day = liturgics.Day(2023, 4, 14)
        day.initialize()
        readings = day.get_readings()
        passage = readings[0].pericope.get_passage()
        size = speech.estimate_group_size(passage)

        # This passage should have 3 groups of 42 verses
        self.assertEqual(42, size)

    def test_estimate_group_size_short(self):
        day = liturgics.Day(2023, 1, 18)
        day.initialize()
        readings = day.get_readings()
        passage = readings[0].pericope.get_passage()

        size = speech.estimate_group_size(passage)
        self.assertIs(size, None)

    def test_reference_speech(self):
        data = [
                (2023, 4, 14, 'The Holy Gospel according to Saint John, chapter 13'),
                (2023, 1, 11, 'Wisdom of Solomon, chapter 3'),
                (2023, 1, 18, 'The Catholic letter of Saint James, chapter 3'),
                (2023, 1, 21, 'Saint Paul\'s <say-as interpret-as="ordinal">1</say-as> letter to the Thessalonians, chapter 5'),
        ]

        for year, month, day, expected in data:
            day = liturgics.Day(year, month, day)
            day.initialize()
            readings = day.get_readings()
            reading = readings[0]

            with self.subTest(day):
                actual = speech.reference_speech(reading)
                self.assertEqual(expected, actual)

    def test_reading_speech(self):
        day = liturgics.Day(2023, 1, 18)
        day.initialize()
        readings = day.get_readings()

        speech_text = speech.reading_speech(readings[0])
        self.assertIn('The spirit that dwelleth in us lusteth to envy', speech_text)
