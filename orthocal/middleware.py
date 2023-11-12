import asyncio
import datetime
import logging

import newrelic.agent
from newrelic.api.transaction import current_transaction

from django.conf import settings
from django.utils import timezone
from django.utils.cache import get_max_age, patch_cache_control, patch_vary_headers
from django.utils.decorators import sync_and_async_middleware

logger = logging.getLogger(__name__)

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

@sync_and_async_middleware
def cache_control(get_response):
    if asyncio.iscoroutinefunction(get_response):
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

def set_request_queueing(request):
    logger.debug(request.headers)

    transaction = newrelic.agent.current_transaction()
    x_timer = request.META.get('HTTP_X_TIMER')

    if x_timer and transaction:
        fields = x_timer.split(',')
        try:
            transaction.queue_start = float(fields[0][1:])
            logger.debug('Setting Newrelic Queue Start to {transaction.queue_start}')
        except ValueError:
            pass

    '''
    try:
        transaction.queue_start = float(fields[0][1:])
        logger.debug('Settings Newrelic Queue Start to {transaction.queue_start}')
    except ValueError:
        return
    '''

@sync_and_async_middleware
def request_queueing(get_response):
    if asyncio.iscoroutinefunction(get_response):
        async def middleware(request):
            set_request_queueing(request)
            response = await get_response(request)
            return response
    else:
        def middleware(request):
            set_request_queueing(request)
            response = get_response(request)
            return response

    return middleware
