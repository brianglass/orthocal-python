from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

META_CRAWLER = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/145.0.0.0 Safari/537.36 (compatible; meta-externalagent/1.1 '
    '(+https://developers.facebook.com/docs/sharing/webmasters/crawler))'
)
CLAUDEBOT = 'Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; ClaudeBot/1.0; +claudebot@anthropic.com)'
BROWSER = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36'
MOBILE_APP = 'Expo/1017880 CFNetwork/3860.200.71 Darwin/25.1.0'


class CrawlerWindowTestCase(TestCase):
    """orthocal.middleware.finite_calendar_for_crawlers"""

    fixtures = ['calendarium.json', 'commemorations.json']

    def setUp(self):
        self.this_year = timezone.localdate().year

    def _readings(self, year, **kwargs):
        return reverse('readings', kwargs={'tradition': 'greek', 'cal': 'gregorian', 'year': year, 'month': 11, 'day': 4, **kwargs})

    def test_crawler_outside_window_gets_uncacheable_404(self):
        for user_agent in (META_CRAWLER, CLAUDEBOT):
            response = self.client.get(self._readings(2288), HTTP_USER_AGENT=user_agent)

            self.assertEqual(response.status_code, 404, user_agent)
            self.assertEqual(response['Cache-Control'], 'no-store')
            self.assertIn('noindex', response['X-Robots-Tag'])

    def test_people_and_apps_still_get_any_date(self):
        for user_agent in (BROWSER, MOBILE_APP, ''):
            response = self.client.get(self._readings(2288), HTTP_USER_AGENT=user_agent)
            self.assertEqual(response.status_code, 200, user_agent)

    def test_crawler_inside_window_gets_the_page(self):
        response = self.client.get(self._readings(self.this_year), HTTP_USER_AGENT=META_CRAWLER)
        self.assertEqual(response.status_code, 200)

    def test_covers_calendar_and_api_routes(self):
        urls = (
            reverse('calendar', kwargs={'tradition': 'slavic', 'cal': 'julian', 'year': 1790, 'month': 9}),
            f'/api/greek/gregorian/{self.this_year + 20}/1/7/',
            f'/api/gregorian/{self.this_year - 20}/1/',
        )
        for url in urls:
            response = self.client.get(url, HTTP_USER_AGENT=CLAUDEBOT)
            self.assertEqual(response.status_code, 404, url)

    def test_pages_without_a_date_are_untouched(self):
        for url in (reverse('index'), reverse('calendar-default'), reverse('about')):
            response = self.client.get(url, HTTP_USER_AGENT=META_CRAWLER)
            self.assertEqual(response.status_code, 200, url)
