import logging

from django.apps import AppConfig
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

class OrthocalConfig(AppConfig):
    name = 'orthocal'
    verbose_name = 'Orthodox Calendar'
    orthocal_started = False

    def ready(self, *args, **kwargs):
        # Under ASGI, MiddlewareMixin runs each middleware's process_request
        # and process_response in its own sync_to_async hop. Marking it sync
        # lets Django run the run of Django middleware in one hop instead.
        # Django 6.2 does this itself (ticket #37177); remove it then.
        MiddlewareMixin.async_capable = False

        self.orthocal_started = True
        logger.info('Orthocal is ready.')
