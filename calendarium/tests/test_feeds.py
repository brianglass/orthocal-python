import re

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
