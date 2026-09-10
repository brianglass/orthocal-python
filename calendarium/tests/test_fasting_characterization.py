from datetime import date, timedelta
from pathlib import Path

from django.test import TestCase

from .. import datetools
from ..datetools import Tradition
from ..liturgics import Day

BASE_DIR = Path(__file__).resolve().parent
GOLDEN = BASE_DIR / 'data/fasting-characterization.txt'

# Must match tools/fasting/characterize.py, which regenerates the golden file.
YEARS = (2025, 2026, 2027, 2028, 2029)


class TestFastingCharacterization(TestCase):
    """Pins the fasting output so a refactor can prove it changed nothing.

    There is no spec to assert against here. `Day.fast_exception` is `max()`
    over an integer that encodes a dietary rung, a precedence claim and a
    sentinel at once, and `_apply_fasting_adjustments` patches whatever that
    gets wrong -- a combination rule nobody wrote down. Only current behaviour
    exists to preserve, so it is pinned verbatim and any drift shows up as a
    readable diff naming the date, tradition, rank and contributing rows.

    Regenerate deliberately, never to make a red test green:

        docker compose run --rm local python tools/fasting/characterize.py --write

    See docs/fasting-refactor-scope.md.
    """

    fixtures = ['calendarium.json']

    def render(self):
        lines = []
        for tradition, name in ((Tradition.Slavic, 'slavic'), (Tradition.Greek, 'greek')):
            for year in YEARS:
                day_date = date(year, 1, 1)
                while day_date.year == year:
                    day = Day(day_date.year, day_date.month, day_date.day,
                              tradition=tradition)
                    day.initialize()
                    rows = ','.join(
                        str(e) for e in sorted(d.fast_exception for d in day.days))
                    abstain = ','.join(
                        datetools.fast_abstentions_for(day.fast_level, day.fast_exception))
                    lines.append(
                        f'{day_date.isoformat()} {name} w{day.weekday} '
                        f'feast{day.feast_level} fast{day.fast_level} '
                        f'exc{day.fast_exception} rows={rows} -> {abstain or "-"}'
                    )
                    day_date += timedelta(days=1)
        return lines

    def test_fasting_output_is_unchanged(self):
        expected = GOLDEN.read_text().splitlines()
        actual = self.render()

        self.assertEqual(len(expected), len(actual))

        # Report the first few differing days rather than a wall of diff.
        differences = [(e, a) for e, a in zip(expected, actual) if e != a]
        if differences:
            report = '\n'.join(f'  expected: {e}\n  actual:   {a}' for e, a in differences[:10])
            self.fail(
                f'{len(differences)} of {len(expected)} days changed. First few:\n{report}'
            )
