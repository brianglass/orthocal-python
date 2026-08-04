import re

from freezegun import freeze_time

from django.test import TestCase
from django.urls import reverse

from ..datetools import Calendar, Tradition


class FeedTest(TestCase):
    fixtures = ['calendarium.json']

    def test_links(self):
        url = reverse('rss-feed-cal', kwargs={'cal': Calendar.Gregorian})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        links = re.findall(r'<link>(.*?)</link>', response.content.decode('utf-8'))
        for link in links[1:]:
            self.assertIn(Calendar.Gregorian, link)

    def test_links_julian(self):
        url = reverse('rss-feed-cal', kwargs={'cal': Calendar.Julian})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        links = re.findall(r'<link>(.*?)</link>', response.content.decode('utf-8'))
        for link in links[1:]:
            self.assertIn(Calendar.Julian, link)

    def test_links_greek(self):
        url = reverse('rss-feed-cal', kwargs={'tradition': Tradition.Greek, 'cal': Calendar.Gregorian})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        links = re.findall(r'<link>(.*?)</link>', response.content.decode('utf-8'))
        for link in links[1:]:
            self.assertIn(Tradition.Greek, link)
            self.assertIn(Calendar.Gregorian, link)

    def test_title_distinguishes_tradition(self):
        """Slavic and Greek feed titles must not be identical, or a reader
        subscribed to both can't tell them apart."""
        slavic_url = reverse('rss-feed-cal', kwargs={'tradition': Tradition.Slavic, 'cal': Calendar.Gregorian})
        greek_url = reverse('rss-feed-cal', kwargs={'tradition': Tradition.Greek, 'cal': Calendar.Gregorian})
        slavic_title = re.search(r'<title>(.*?)</title>', self.client.get(slavic_url).content.decode('utf-8')).group(1)
        greek_title = re.search(r'<title>(.*?)</title>', self.client.get(greek_url).content.decode('utf-8')).group(1)
        self.assertNotEqual(slavic_title, greek_title)

    @freeze_time('2026-07-25 12:00:00')  # noon UTC stays July 25 in America/Los_Angeles too
    def test_translation_changes_passage_content(self):
        """A regression test: the feed's items() didn't pass fetch_content=True
        to get_readings(), and feed_description.html called the get_passage()
        method (fresh query, its own kjv-defaulting args) instead of the
        passage attribute -- so an explicit translation was silently ignored
        and every feed rendered KJV regardless of what was requested."""
        kjv_url = reverse('rss-feed-cal', kwargs={'tradition': Tradition.Slavic, 'cal': Calendar.Gregorian})
        lxx_url = reverse('rss-feed-cal', kwargs={'tradition': Tradition.Slavic, 'cal': Calendar.Gregorian, 'translation': 'lxx2012-web'})

        kjv_body = self.client.get(kjv_url).content.decode('utf-8')
        lxx_body = self.client.get(lxx_url).content.decode('utf-8')

        self.assertIn('subject unto the higher powers', kjv_body)
        self.assertIn('in subjection to the higher authorities', lxx_body)
        self.assertNotIn('subject unto the higher powers', lxx_body)
