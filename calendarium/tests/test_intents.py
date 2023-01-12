import json

from pathlib import Path
from unittest import mock

from django.test import TestCase

from ask_sdk_core.response_helper import ResponseFactory
from ask_sdk_model import RequestEnvelope

from .. import skills

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent


class IntentTestCase(TestCase):
    fixtures = ['calendarium.json']

    def test_next_intent(self):
        with open(BASE_DIR / 'data/next_intent_envelope.json') as f:
            envelope = f.read()

        skill = skills.orthodox_daily_skill

        request_envelope = skill.serializer.deserialize(payload=envelope, obj_type=RequestEnvelope)
        response = skill.invoke(request_envelope=request_envelope, context=None)

        print(response)

    def test_launch_intent(self):
        with open(BASE_DIR / 'data/launch_intent_envelope.json') as f:
            envelope = f.read()

        skill = skills.orthodox_daily_skill

        request_envelope = skill.serializer.deserialize(payload=envelope, obj_type=RequestEnvelope)
        response = skill.invoke(request_envelope=request_envelope, context=None)

        print(response)
