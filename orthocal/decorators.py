import functools
import hashlib
import newrelic.agent

from django.conf import settings
from django.utils import timezone
from django.views.decorators.cache import cache_page
from django.views.decorators.http import etag as etag_decorator

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

    for header in settings.ORTHOCAL_VARY_HEADERS:
        if value := request.headers.get(header):
            hash.update(f'{header}: {value}'.encode('utf8'))

    return f'"{hash.hexdigest()}"'

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
