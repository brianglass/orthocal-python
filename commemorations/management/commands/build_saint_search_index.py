import html

from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.utils.html import strip_tags

from commemorations.models import DayCommemoration
from commemorations.search import LIFE_SEARCH_TABLE, vocabulary


class Command(BaseCommand):
    help = (
        'Rebuild the full-text index of commemoration titles, saint names '
        'and lives that search.matching_lives reads.'
    )

    def handle(self, *args, **options):
        rows = []
        for dc in DayCommemoration.objects.prefetch_related('daycommemorationsaint_set__saint'):
            names = ' '.join(
                f'{link.saint.name} {link.saint.full_name or ""}'
                for link in dc.daycommemorationsaint_set.all()
            )
            # The lives are simple HTML (paragraphs, italics, a few lists).
            # Index their text only, so markup can't match a query or show
            # up in an excerpt.
            story = html.unescape(strip_tags(dc.story or '')).strip()
            rows.append((dc.pk, dc.title, names, story))

        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute(f'DELETE FROM {LIFE_SEARCH_TABLE}')
            cursor.executemany(
                f'INSERT INTO {LIFE_SEARCH_TABLE} (rowid, title, names, story) VALUES (%s, %s, %s, %s)',
                rows,
            )
        vocabulary.cache_clear()

        self.stdout.write(f'Indexed {len(rows)} commemoration(s) for search.')
