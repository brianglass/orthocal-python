from django.core.management.base import BaseCommand

from commemorations.models import Saint
from commemorations.transliteration import normalize_transliteration


class Command(BaseCommand):
    help = (
        'Backfill Saint.normalized_name from name/full_name, so search can '
        'match across Greek/Latin transliteration spelling variants.'
    )

    def handle(self, *args, **options):
        updated = 0
        for saint in Saint.objects.all():
            normalized = normalize_transliteration(f'{saint.name} {saint.full_name or ""}')
            if normalized != saint.normalized_name:
                saint.normalized_name = normalized
                saint.save(update_fields=['normalized_name'])
                updated += 1
        self.stdout.write(f'Updated normalized_name on {updated} saint(s).')
