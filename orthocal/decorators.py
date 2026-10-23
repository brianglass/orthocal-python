import functools
import hashlib
import inspect
import newrelic.agent

from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.cache import cache as default_cache
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.cache import cache_page
from django.views.decorators.http import etag as etag_decorator

from calendarium.datetools import Calendar, Tradition, Translation, cal_session_key, translation_session_key

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

    tradition = request.session.get('tradition', Tradition.Slavic)
    hash.update(tradition.encode('utf8'))

    cal = request.session.get(cal_session_key(tradition), Calendar.Gregorian)
    hash.update(cal.encode('utf8'))

    translation = request.session.get(translation_session_key(request.LANGUAGE_CODE), Translation.KJV)
    hash.update(translation.encode('utf8'))

    for header in settings.ORTHOCAL_VARY_HEADERS:
        if value := request.headers.get(header):
            hash.update(f'{header}: {value}'.encode('utf8'))

    return f'"{hash.hexdigest()}"'

# Decorators

etag = etag_decorator(get_etag)
etag_date = etag_decorator(get_date_variable_etag)
cache = cache_page(settings.ORTHOCAL_MAX_AGE)

def in_thread_pool(func):
    """Make a sync function awaitable, run in the event loop's thread pool.

    The app's own work is sync and CPU-bound -- the liturgical day logic
    and the Django ORM over a local, read-only SQLite file -- so the views
    stay async only as a thin shell: each hands its whole computation to
    one of these calls instead of hopping threads for every query.

    It uses the loop's persistent pool (thread_sensitive=False) rather than
    Django's thread-sensitive path, which starts a fresh thread, and so a
    fresh SQLite connection, for every request. That is safe here because
    the database is read-only: there are no transactions to keep on one
    thread. Measured in Oct 2026 against the async ORM, on 2 CPUs: about a
    third more requests per second, and cold iCal and month builds under
    load finished in less than half the time.

    Under test, Django's TestCase loads fixtures in a transaction on the
    main thread's connection, which a pool thread's connection can't see,
    so tests take the thread-sensitive path instead.
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        return await sync_to_async(func, thread_sensitive=settings.TESTING)(*args, **kwargs)

    return wrapper

def cache_content(key, content_type, cache=None, timeout=DEFAULT_TIMEOUT):
    """Cache the bytes a sync function returns, and return them as an HttpResponse.

    key is a format string over the function's arguments, defaults
    included, e.g. 'api-day-{cal}-{year}-{request.LANGUAGE_CODE}'. Only
    the content is cached, not a whole response, so the headers stay
    whatever the view and middleware set; and only the arguments named in
    the key distinguish entries, unlike cache_page, which keys on the URL
    and the Vary headers.
    """

    if cache is None:
        cache = default_cache

    def decorator(func):
        signature = inspect.signature(func)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            arguments = signature.bind(*args, **kwargs)
            arguments.apply_defaults()
            cache_key = key.format(**arguments.arguments)

            if (content := cache.get(cache_key)) is None:
                content = func(*args, **kwargs)
                cache.set(cache_key, content, timeout=timeout)

            return HttpResponse(content, content_type=content_type)

        return wrapper
    return decorator

def instrument_endpoint(view):
    @functools.wraps(view)
    async def wrapped_view(*args, **kwargs):
        transaction_name = f"{view.__module__}:{view.__name__}"
        newrelic.agent.set_transaction_name(transaction_name)
        return await view(*args, **kwargs)

    return wrapped_view
