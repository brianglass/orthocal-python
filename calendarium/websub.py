from django.conf import settings
from django.contrib.syndication.views import Feed as BaseFeed
from django.utils.feedgenerator import Rss201rev2Feed


class WSRssFeed(Rss201rev2Feed):
    def add_root_elements(self, handler):
        super().add_root_elements(handler)
        handler.addQuickElement('link', '', {
            'rel': 'hub',
            'href': settings.ORTHOCAL_WEBSUB_URL,
        })


class Feed(BaseFeed):
    feed_type = WSRssFeed
