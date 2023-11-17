from django.apps import AppConfig

class OrthocalConfig(AppConfig):
    name = 'orthocal'
    verbose_name = 'Orthodox Calendar'
    orthocal_started = False

    def ready(self, *args, **kwargs):
        self.orthocal_started = True
