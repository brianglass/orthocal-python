import datetime
import re

import newrelic.agent

from asgiref.sync import iscoroutinefunction, markcoroutinefunction
from django.conf import settings
from django.http import HttpResponseNotFound
from django.urls import Resolver404, resolve
from django.utils import timezone
from django.utils.cache import get_max_age, patch_cache_control, patch_vary_headers
from django.utils.decorators import sync_and_async_middleware
from newrelic.api.transaction import current_transaction

@sync_and_async_middleware
def cache_control(get_response):
    if iscoroutinefunction(get_response):
        async def middleware(request):
            response = await get_response(request)
            patch_headers(response)
            return response
    else:
        def middleware(request):
            response = get_response(request)
            patch_headers(response)
            return response

    return middleware

@sync_and_async_middleware
def request_queueing(get_response):
    if iscoroutinefunction(get_response):
        async def middleware(request):
            set_request_queueing(request)
            return await get_response(request)
    else:
        def middleware(request):
            set_request_queueing(request)
            return get_response(request)

    return middleware

@sync_and_async_middleware
def finite_calendar_for_crawlers(get_response):
    """404 crawlers asking for a date outside the indexable window.

    Every date in every year is a valid page, so to a crawler the calendar
    is infinite: in Oct 2026, 78% of peak-hour requests were for dates
    beyond is_indexable's window (Meta's crawler was reading the 2280s).
    The pages' noindex and nofollow don't help, since those crawlers work
    from URL lists, not links. Real visitors and API clients (e.g. the
    mobile app) are untouched -- this matches only self-declared crawlers.
    It has to run before cache_control, which marks responses public:
    Firebase's CDN would otherwise serve the cached 404 to people too."""

    if iscoroutinefunction(get_response):
        async def middleware(request):
            if is_crawler_outside_window(request):
                return out_of_window_response()
            return await get_response(request)
    else:
        def middleware(request):
            if is_crawler_outside_window(request):
                return out_of_window_response()
            return get_response(request)

    return middleware

# Helper functions

def patch_headers(response):
    # We don't let the browser cache as long as the CDN in case we make changes
    # to the site.
    max_age = get_max_age(response) or settings.ORTHOCAL_MAX_AGE

    # We allow the CDN to cache until midnight. We can purge the cache by
    # redeploying to Firebase.
    now = timezone.localtime()
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
    cdn_max_age = int((midnight - now).total_seconds())

    # s-maxage is for Firebase CDN.
    patch_cache_control(response, public=True, max_age=max_age, s_maxage=cdn_max_age)
    patch_vary_headers(response, settings.ORTHOCAL_VARY_HEADERS)

def set_request_queueing(request):
    """Set Newrelic "request queuing" from Fastly X-Timer header."""

    # See https://developer.fastly.com/reference/http/http-headers/X-Timer/
    x_timer = request.META.get('HTTP_X_TIMER')
    transaction = newrelic.agent.current_transaction()

    if x_timer and transaction:
        fields = x_timer.split(',')
        try:
            transaction.queue_start = float(fields[0][1:])
        except (IndexError, ValueError):
            pass

CRAWLER_RE = re.compile(r'bot|crawl|spider|slurp|externalagent|externalhit', re.IGNORECASE)

def is_crawler_outside_window(request):
    if not CRAWLER_RE.search(request.META.get('HTTP_USER_AGENT', '')):
        return False

    try:
        kwargs = resolve(request.path_info).kwargs
    except Resolver404:
        return False

    if 'year' not in kwargs:
        return False

    try:
        dt = datetime.date(kwargs['year'], kwargs.get('month', 1), kwargs.get('day', 1))
    except (TypeError, ValueError):
        return False

    # Imported here: calendarium.views imports far more than middleware
    # should pull in at settings-load time.
    from calendarium.views import is_indexable
    return not is_indexable(dt)

def out_of_window_response():
    response = HttpResponseNotFound()
    response['Cache-Control'] = 'no-store'
    response['X-Robots-Tag'] = 'noindex, nofollow'
    return response
