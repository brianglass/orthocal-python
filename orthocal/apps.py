import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)

class OrthocalConfig(AppConfig):
    name = 'orthocal'
    verbose_name = 'Orthodox Calendar'
    orthocal_started = False

    def ready(self, *args, **kwargs):
        self.orthocal_started = True
        logger.info('Orthocal is ready.')
