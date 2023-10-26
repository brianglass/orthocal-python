import asyncio
import datetime

from django.conf import settings
from django.utils import timezone
from django.utils.cache import patch_cache_control, patch_vary_headers
from django.utils.decorators import sync_and_async_middleware

def get_cdn_max_age():
    # Everything expires at midnight for the CDN.    now = timezone.localtime()
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
    return int((midnight - now).total_seconds())

@sync_and_async_middleware
def cache_control(get_response):
    # s-maxage is for Firebase CDN.
    if asyncio.iscoroutinefunction(get_response):
        async def middleware(request):
            cdn_max_age = get_cdn_max_age()
            response = await get_response(request)
            patch_cache_control(response, public=True, max_age=settings.ORTHOCAL_MAX_AGE, s_maxage=cdn_max_age)
            patch_vary_headers(response, settings.ORTHOCAL_VARY_HEADERS)
            return response
    else:
        def middleware(request):
            cdn_max_age = get_cdn_max_age()
            response = get_response(request)
            patch_cache_control(response, public=True, max_age=settings.ORTHOCAL_MAX_AGE, s_maxage=cdn_max_age)
            patch_vary_headers(response, settings.ORTHOCAL_VARY_HEADERS)
            return response

    return middleware
