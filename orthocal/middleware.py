import asyncio

from django.conf import settings
from django.utils.cache import patch_cache_control, patch_vary_headers
from django.utils.decorators import sync_and_async_middleware

@sync_and_async_middleware
def cache_control(get_response):
    if asyncio.iscoroutinefunction(get_response):
        async def middleware(request):
            response = await get_response(request)
            patch_cache_control(response, public=True, max_age=settings.ORTHOCAL_MAX_AGE)
            patch_vary_headers(response, settings.ORTHOCAL_VARY_HEADERS)
            return response
    else:
        def middleware(request):
            response = get_response(request)
            patch_cache_control(response, public=True, max_age=settings.ORTHOCAL_MAX_AGE)
            patch_vary_headers(response, settings.ORTHOCAL_VARY_HEADERS)
            return response

    return middleware
