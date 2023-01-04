import json

from pathlib import Path

from asgiref.sync import async_to_sync
from django.test import TestCase

from .. import liturgics
from .. import serializers

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent


class DaySerializerTestCase(TestCase):
    fixtures = ['calendarium.json']

    def test_theophany(self):
        # Theophany
        day = liturgics.Day(2023, 1, 6)
        day.initialize()

        actual = serializers.DaySerializer(day)

        with open(BASE_DIR / 'data/theophany.json') as f:
            expected = json.loads(f.read())

        self.assertEqual(actual.data, expected)
