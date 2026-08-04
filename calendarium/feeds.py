from datetime import datetime, timedelta

from dateutil.rrule import rrule, DAILY
from django.conf import settings
from django.contrib.syndication.views import Feed
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.feedgenerator import Rss201rev2Feed

from . import liturgics
from .datetools import Calendar, Tradition, TRANSLATION_LABELS


class WSRssFeed(Rss201rev2Feed):
    def add_root_elements(self, handler):
        super().add_root_elements(handler)
        handler.addQuickElement('atom:link', '', {
            'rel': 'hub',
            'href': settings.ORTHOCAL_WEBSUB_URL,
        })


class ReadingsFeed(Feed):
    feed_type = WSRssFeed
    link = '/'
    description_template = 'feed_description.html'
    item_categories = categories = 'orthodox', 'christian', 'religion'

    def get_object(self, request, cal=Calendar.Gregorian, tradition=Tradition.Slavic, translation=None):
        return {'cal': cal, 'tradition': tradition, 'translation': translation}

    def title(self, obj):
        title = f'Orthodox Daily Readings ({obj["tradition"].title()}, {obj["cal"].title()})'
        if obj['translation']:
            title += f' [{TRANSLATION_LABELS[obj["translation"]]}]'
        return title

    def description(self, obj):
        description = (f'Daily readings from scripture and the lives of the saints according to the '
                        f'{obj["tradition"].title()} tradition, {obj["cal"].title()} calendar.')
        if obj['translation']:
            description += f' Scripture from the {TRANSLATION_LABELS[obj["translation"]]}.'
        return description

    def items(self, obj):
        now = timezone.localtime()
        start_dt = now - timedelta(days=10)
        for dt in rrule(DAILY, dtstart=start_dt, until=now):
            day = liturgics.Day(dt.year, dt.month, dt.day, calendar=obj['cal'], tradition=obj['tradition'], translation=obj['translation'])
            day.initialize()
            day.get_readings(fetch_content=True)
            yield day

    def item_pubdate(self, day):
        dt = day.gregorian_date
        tzinfo = timezone.get_current_timezone()
        return datetime(dt.year, dt.month, dt.day, tzinfo=tzinfo)

    def item_title(self, day):
        return day.summary_title

    def item_link(self, day):
        dt = day.gregorian_date
        return reverse('readings', kwargs={
            'cal': day.pyear.calendar,
            'tradition': day.tradition,
            'year': dt.year,
            'month': dt.month,
            'day': dt.day
        })
