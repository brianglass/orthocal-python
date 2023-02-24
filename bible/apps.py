from django.apps import AppConfig
from django.db.models import Max

from . import books


class BibleConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bible'

    def ready(self):
        from bible.models import Verse

        chapter_max = Verse.objects.values('book').annotate(max=Max('chapter')).filter(max=1)
        books.CHAPTERLESS_BOOKS = [book['book'] for book in chapter_max]
