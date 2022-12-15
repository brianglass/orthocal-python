from django.test import TestCase

from .. import liturgics


class TestLiturgics(TestCase):
    def test_compose_liturgical_day(self):
        d = liturgics.LiturgicalDay(2022, 1, 1, use_julian=False)
        print(d)
        print(dir(d))
