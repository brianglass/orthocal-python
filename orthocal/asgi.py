"""
ASGI config for orthocal project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/asgi/
"""

import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orthocal.settings')

from asgi_middleware_static_file import ASGIMiddlewareStaticFile
from django.conf import settings
from django.core.asgi import get_asgi_application

application = get_asgi_application()
application = ASGIMiddlewareStaticFile(
    application,
    static_url=settings.STATIC_URL,
    static_root_paths=[settings.STATIC_ROOT],
)
