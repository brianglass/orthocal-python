from datetime import date
from types import SimpleNamespace

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from commemorations.models import DayCommemoration

from ..datetools import Calendar, Tradition
from ..templatetags.commemoration_links import link_commemoration_dates, link_date

GREGORIAN, JULIAN = Calendar.Gregorian, Calendar.Julian


def readings_url(target, cal='gregorian', tradition='slavic'):
    return reverse('readings', kwargs={
        'tradition': tradition, 'cal': cal,
        'year': target.year, 'month': target.month, 'day': target.day,
    })


class LinkDateTestCase(TestCase):
    def test_links_within_the_church_year(self):
        """Jan 2, 2026 is in the Church year that began Sep 1, 2025, so a
        December date links back into 2025 and a July date forward into 2026."""
        today = date(2026, 1, 2)
        self.assertEqual(date(2025, 12, 4), link_date(12, 4, today, GREGORIAN))
        self.assertEqual(date(2026, 7, 19), link_date(7, 19, today, GREGORIAN))

    def test_church_year_turns_on_september_1(self):
        self.assertEqual(date(2026, 9, 1), link_date(9, 1, date(2027, 8, 31), GREGORIAN))
        self.assertEqual(date(2028, 8, 31), link_date(8, 31, date(2027, 9, 1), GREGORIAN))
        self.assertEqual(date(2027, 1, 17), link_date(1, 17, date(2026, 12, 4), GREGORIAN))

    def test_no_link_to_the_day_being_viewed(self):
        self.assertIsNone(link_date(12, 4, date(2026, 12, 4), GREGORIAN))

    def test_julian_links_to_the_civil_date(self):
        """Julian Jan 2, 2026 is civil Jan 15. A story's "July 19" is the
        Julian July 19, which an Old Calendar reader keeps on civil Aug 1."""
        today = date(2026, 1, 2)
        self.assertEqual(date(2026, 8, 1), link_date(7, 19, today, JULIAN))
        self.assertEqual(date(2025, 12, 17), link_date(12, 4, today, JULIAN))

    def test_feb_29_links_to_the_soonest_that_has_not_passed(self):
        self.assertEqual(date(2028, 2, 29), link_date(2, 29, date(2026, 3, 1), GREGORIAN))
        self.assertEqual(date(2028, 2, 29), link_date(2, 29, date(2028, 2, 1), GREGORIAN))
        self.assertEqual(date(2032, 2, 29), link_date(2, 29, date(2028, 3, 1), GREGORIAN))
        self.assertIsNone(link_date(2, 29, date(2028, 2, 29), GREGORIAN))

    def test_julian_feb_29(self):
        # Julian Feb 29, 2028 is civil Mar 13.
        self.assertEqual(date(2028, 3, 13), link_date(2, 29, date(2026, 3, 1), JULIAN))
        # 2100 is a Julian leap year but not a Gregorian one. Its Julian Feb 29
        # can't be a Python date, but the civil date it lands on can.
        self.assertEqual(date(2100, 3, 14), link_date(2, 29, date(2099, 3, 1), JULIAN))


class LinkCommemorationDatesTestCase(TestCase):
    today = date(2026, 1, 2)

    def render(self, html, cal=GREGORIAN):
        context = SimpleNamespace(date=self.today, calendar=cal, tradition=Tradition.Slavic)
        return link_commemoration_dates(html, context)

    def test_links_a_parenthetical_reference(self):
        html = self.render('<p>Saint Seraphim, Bishop of Phanarion (Dec. 4), was ordained.</p>')
        self.assertIn(f'<a class="commemoration-date" href="{readings_url(date(2025, 12, 4))}">Dec. 4</a>', html)

    def test_links_day_first_dates_and_ordinals(self):
        html = self.render('<p>Saint Oswald (5 August) is also kept on July 19th.</p>')
        self.assertIn(f'<a class="commemoration-date" href="{readings_url(date(2026, 8, 5))}">5 August</a>', html)
        self.assertIn(f'<a class="commemoration-date" href="{readings_url(date(2026, 7, 19))}">July 19th</a>', html)

    def test_leaves_historical_dates_alone(self):
        for text in ('falling asleep in peace on January 2, 1833, chanting',
                     'was consecrated on December 25 784.',
                     'died in peace on 22 September 1323.'):
            with self.subTest(text):
                self.assertNotIn('<a ', self.render(f'<p>{text}</p>'))

    def test_leaves_date_ranges_alone(self):
        for text in ('On the night of 21-22 November he had a revelation.',
                     'From November 21-22 he kept vigil.'):
            with self.subTest(text):
                self.assertNotIn('<a ', self.render(f'<p>{text}</p>'))

    def test_leaves_calendar_marked_dates_alone(self):
        html = self.render('<p>His feast is kept on this day (March 5 OC, March 18 NC).</p>')
        self.assertNotIn('<a ', html)

    def test_ignores_impossible_dates(self):
        self.assertNotIn('<a ', self.render('<p>not February 30, nor April 31</p>'))

    def test_leaves_markup_and_existing_links_alone(self):
        html = self.render('<p title="March 5">See <a href="/x">March 6</a> and <i>March 7</i>.</p>')
        self.assertIn('<p title="March 5">', html)
        self.assertIn('<a href="/x">March 6</a>', html)
        self.assertIn(f'<i><a class="commemoration-date" href="{readings_url(date(2026, 3, 7))}">March 7</a></i>', html)

    def test_links_keep_the_calendar(self):
        html = self.render('<p>(see July 19)</p>', JULIAN)
        self.assertIn(f'<a class="commemoration-date" href="{readings_url(date(2026, 8, 1), cal="julian")}">July 19</a>', html)

    def test_passes_empty_stories_through(self):
        self.assertEqual('', self.render(''))
        self.assertIsNone(self.render(None))


class StoryLinksOnPagesTestCase(TestCase):
    fixtures = ['calendarium.json', 'commemorations.json']

    # The Jan 2 story of St Seraphim of Sarov mentions the saint he was named
    # for: "Hieromartyr Seraphim, Bishop of Phanarion (Dec. 4)".
    SERAPHIM = 5209

    def setUp(self):
        # Slugs aren't in the fixture; the Dockerfile backfills them after
        # loading it, and so does this, mirroring commemorations.tests.
        call_command('backfill_saint_slugs')

    def test_readings_page_links_story_dates(self):
        response = self.client.get(readings_url(date(2026, 1, 2)))
        self.assertContains(response, f'<a class="commemoration-date" href="{readings_url(date(2025, 12, 4))}">Dec. 4</a>')

    def test_julian_readings_page_links_to_the_civil_date(self):
        # Civil Jan 15, 2026 is Julian Jan 2; Julian Dec 4, 2025 is civil Dec 17.
        response = self.client.get(readings_url(date(2026, 1, 15), cal='julian'))
        self.assertContains(response, f'<a class="commemoration-date" href="{readings_url(date(2025, 12, 17), cal="julian")}">Dec. 4</a>')

    def test_saint_page_links_story_dates(self):
        saint = DayCommemoration.objects.get(pk=self.SERAPHIM).saints.first()
        response = self.client.get(reverse('saint-detail', args=[saint.slug]))
        self.assertContains(response, '/readings/slavic/gregorian/')
        self.assertContains(response, '>Dec. 4</a>')
        # The links depend on the reader's remembered calendar, so the page
        # must not be cached across readers. Reading the session is what
        # makes Django send this; keep it that way.
        self.assertIn('Cookie', response['Vary'])

    def test_saint_page_keeps_an_old_calendar_reader_on_the_old_calendar(self):
        # What a reader does: visiting a Julian page remembers the calendar.
        # (Editing client.session directly doesn't reach the request with
        # signed-cookie sessions, since the cookie *is* the session.)
        self.client.get(readings_url(date(2026, 1, 15), cal='julian'))
        saint = DayCommemoration.objects.get(pk=self.SERAPHIM).saints.first()
        response = self.client.get(reverse('saint-detail', args=[saint.slug]))
        self.assertContains(response, '/readings/slavic/julian/')
        self.assertNotContains(response, '/readings/slavic/gregorian/')
