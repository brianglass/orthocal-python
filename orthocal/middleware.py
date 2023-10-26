import asyncio
import datetime

from django.conf import settings
from django.utils import timezone
from django.utils.cache import patch_cache_control, patch_vary_headers
from django.utils.decorators import sync_and_async_middleware

@sync_and_async_middleware
def cache_control(get_response):
    # Everything expires at midnight
    now = timezone.localtime()
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
    max_age = int((midnight - now).total_seconds())

    if asyncio.iscoroutinefunction(get_response):
        async def middleware(request):
            response = await get_response(request)
            response['Surrogate-Control'] = f'max-age={max_age}'
            patch_cache_control(response, public=True, max_age=settings.ORTHOCAL_MAX_AGE)
            patch_vary_headers(response, settings.ORTHOCAL_VARY_HEADERS)
            return response
    else:
        def middleware(request):
            response = get_response(request)
            response['Surrogate-Control'] = f'max-age={max_age}'
            patch_cache_control(response, public=True, max_age=settings.ORTHOCAL_MAX_AGE)
            patch_vary_headers(response, settings.ORTHOCAL_VARY_HEADERS)
            return response

    return middleware
