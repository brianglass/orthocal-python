import functools
import hashlib
import logging
import newrelic.agent

from django.conf import settings
from django.core.cache import cache as default_cache
from django.utils import timezone
from django.utils.cache import get_cache_key, has_vary_header, learn_cache_key, patch_response_headers
from django.views.decorators.cache import cache_page
from django.views.decorators.http import etag as etag_decorator

from calendarium.datetools import Calendar

logger = logging.getLogger(__name__)

# Helper functions

def get_etag(request, *args, **kwargs):
    hash = hashlib.md5()

    hash.update(settings.ORTHOCAL_REVISION.encode('utf8'))

    for header in settings.ORTHOCAL_VARY_HEADERS:
        if value := request.headers.get(header):
            hash.update(f'{header}: {value}'.encode('utf8'))

    return f'"{hash.hexdigest()}"'

def get_date_variable_etag(request, *args, **kwargs):
    hash = hashlib.md5()

    now = timezone.localtime()
    date = f'{now.year}/{now.month}/{now.day}'
    hash.update(date.encode('utf8'))

    hash.update(settings.ORTHOCAL_REVISION.encode('utf8'))

    cal = request.session.get('cal', Calendar.Gregorian)
    hash.update(cal.encode('utf8'))

    for header in settings.ORTHOCAL_VARY_HEADERS:
        if value := request.headers.get(header):
            hash.update(f'{header}: {value}'.encode('utf8'))

    return f'"{hash.hexdigest()}"'

# Decorators

etag = etag_decorator(get_etag)
etag_date = etag_decorator(get_date_variable_etag)
cache = cache_page(settings.ORTHOCAL_MAX_AGE)

def instrument_endpoint(view):
    @functools.wraps(view)
    async def wrapped_view(*args, **kwargs):
        transaction_name = f"{view.__module__}:{view.__name__}"
        newrelic.agent.set_transaction_name(transaction_name)
        return await view(*args, **kwargs)

    return wrapped_view

def acache_page(timeout, cache=None, key_prefix=None):
    """Asynchronous version of Django's cache_page decorator."""

    if not cache:
        cache = default_cache

    def decorator(view):
        @functools.wraps(view)
        async def wrapped_view(request, *args, **kwargs):

            # Fetch from cache if available
            if request.method in ('GET', 'HEAD'):
                if key := get_cache_key(request, key_prefix, request.method, cache=cache):
                    if response := await cache.aget(key):
                        return response

            response = await view(request, *args, **kwargs)

            if request.method not in ('GET', 'HEAD'):
                return response

            # Don't cache responses that set a user-specific (and maybe security
            # sensitive) cookie in response to a cookie-less request.
            if not request.COOKIES and response.cookies and has_vary_header(response, 'Cookie'):
                return response

            if 'private' in response.get('Cache-Control', ()):
                return response

            patch_response_headers(response, timeout)

            # Store the response in the cache.
            if timeout and response.status_code == 200:
                cache_key = learn_cache_key(request, response, timeout, key_prefix=key_prefix, cache=cache)
                if hasattr(response, 'render') and callable(response.render):
                    view_name = f'{view.__module__}:{view.__name__}'
                    logger.warning(f'The acache_page decorator cannot asynchronously '
                                   f'cache a TemplateResponse for view: {view_name}.')
                    response.add_post_render_callback(lambda r: cache.set(cache_key, r, timeout))
                else:
                    await cache.aset(cache_key, response, timeout)

            return response

        return wrapped_view
    return decorator

acache = acache_page(settings.ORTHOCAL_MAX_AGE)
