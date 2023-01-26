import json

from pathlib import Path
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from ask_sdk_core.response_helper import ResponseFactory
from ask_sdk_model import RequestEnvelope

from .. import skills, speech

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent


class IntentTestCase(TestCase):
    fixtures = ['calendarium.json', 'commemorations.json']

    def test_launch_intent(self):
        with open(BASE_DIR / 'data/launch_intent_envelope.json') as f:
            envelope = f.read()

        today = timezone.localtime()

        skill = skills.orthodox_daily_skill

        request_envelope = skill.serializer.deserialize(payload=envelope, obj_type=RequestEnvelope)
        response = skill.invoke(request_envelope=request_envelope, context=None)

        self.assertEqual(['scriptures', 'commemorations'], response.session_attributes['task_queue'])
        self.assertEqual(today.strftime('%Y-%m-%d'), response.session_attributes['date'])
        self.assertIsNone(response.session_attributes['current_task'])
        self.assertIn('Would you like to hear the readings?', response.response.output_speech.ssml)

    def test_scriptures_intent_long(self):
        with open(BASE_DIR / 'data/scriptures_intent_envelope_long.json') as f:
            envelope = f.read()

        skill = skills.orthodox_daily_skill

        request_envelope = skill.serializer.deserialize(payload=envelope, obj_type=RequestEnvelope)
        response = skill.invoke(request_envelope=request_envelope, context=None)

        self.assertLess(len(response.response.output_speech.ssml), speech.MAX_SPEECH_LENGTH)

    def test_next_intent(self):
        with open(BASE_DIR / 'data/next_intent_envelope.json') as f:
            envelope = f.read()

        skill = skills.orthodox_daily_skill

        request_envelope = skill.serializer.deserialize(payload=envelope, obj_type=RequestEnvelope)
        response = skill.invoke(request_envelope=request_envelope, context=None)

        self.assertIn('deceiveth his own heart', response.response.output_speech.ssml)
        self.assertIn('Would you like to hear the next reading?', response.response.output_speech.ssml)
        self.assertEqual(1, response.session_attributes['next_reading'])
        self.assertEqual(['commemorations'], response.session_attributes['task_queue'])
        self.assertEqual('scriptures', response.session_attributes['current_task'])
        self.assertEqual('2023-01-12', response.session_attributes['date'])

    def test_next_intent_followup(self):
        with open(BASE_DIR / 'data/next_intent_envelope_followup.json') as f:
            envelope = f.read()

        skill = skills.orthodox_daily_skill

        request_envelope = skill.serializer.deserialize(payload=envelope, obj_type=RequestEnvelope)
        response = skill.invoke(request_envelope=request_envelope, context=None)

        self.assertIn('Would you like me to continue?', response.response.output_speech.ssml)
        self.assertEqual(0, response.session_attributes['next_reading'])
        self.assertEqual(84, response.session_attributes['next_verse'])
        self.assertEqual('scriptures', response.session_attributes['current_task'])
        self.assertEqual([], response.session_attributes['task_queue'])

    def test_next_intent_commemorations(self):
        with open(BASE_DIR / 'data/next_intent_commemorations_envelope.json') as f:
            envelope = f.read()

        skill = skills.orthodox_daily_skill

        request_envelope = skill.serializer.deserialize(payload=envelope, obj_type=RequestEnvelope)
        response = skill.invoke(request_envelope=request_envelope, context=None)

        self.assertIn('Our Father among the Saints Gregory the Theologian', response.response.output_speech.ssml)
        self.assertNotIn('<it>', response.response.output_speech.ssml)

    def test_next_intent_multiple_commemorations(self):
        with open(BASE_DIR / 'data/next_intent_commemorations_multiple_envelope.json') as f:
            envelope = f.read()

        skill = skills.orthodox_daily_skill

        request_envelope = skill.serializer.deserialize(payload=envelope, obj_type=RequestEnvelope)
        response = skill.invoke(request_envelope=request_envelope, context=None)

        self.assertFalse(response.response.should_end_session)
        self.assertEqual(1, response.session_attributes['next_commemoration'])
        self.assertIn('Xenophon', response.response.output_speech.ssml)

    def test_help_intent(self):
        with open(BASE_DIR / 'data/help_intent_envelope.json') as f:
            envelope = f.read()

        skill = skills.orthodox_daily_skill

        request_envelope = skill.serializer.deserialize(payload=envelope, obj_type=RequestEnvelope)
        response = skill.invoke(request_envelope=request_envelope, context=None)

        self.assertIn('Orthodox Daily makes it easy', response.response.output_speech.ssml)
        self.assertFalse(response.response.should_end_session)

    def test_stop_intent(self):
        with open(BASE_DIR / 'data/no_intent_envelope.json') as f:
            envelope = f.read()

        skill = skills.orthodox_daily_skill

        request_envelope = skill.serializer.deserialize(payload=envelope, obj_type=RequestEnvelope)
        response = skill.invoke(request_envelope=request_envelope, context=None)

        self.assertTrue(response.response.should_end_session)
        self.assertEqual(0, len(response.session_attributes))
