import logging

import requests

from urllib.parse import urljoin

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.urls import reverse

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Publish RSS Feeds to a Websub hub.'

    def handle(self, *args, **options):
        feed_paths = [
            reverse('rss-feed'),
            reverse('rss-feed-cal', kwargs={'cal': 'gregorian'}),
            reverse('rss-feed-cal', kwargs={'cal': 'julian'}),
        ]

        response = requests.post(settings.ORTHOCAL_WEBSUB_URL, data={
            'hub.mode': 'publish',
            'hub.url': [urljoin(settings.ORTHOCAL_PUBLIC_URL, p) for p in feed_paths]
        })

        if not response.ok:
            raise CommandError(f'WEBSUB Publish error ({response.status_code}): {response.text}')
