import re

from django.test import TestCase
from django.urls import reverse

from ..datetools import Calendar


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
