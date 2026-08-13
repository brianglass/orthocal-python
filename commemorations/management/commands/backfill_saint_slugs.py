from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from commemorations.models import Saint


class Command(BaseCommand):
    help = (
        "Backfill Saint.slug for any row that doesn't have one yet. Slugs "
        "aren't computed at save() time (see the model's own comment) "
        "because they fold in the saint's earliest fixed-calendar "
        "commemoration date as a disambiguator, and that relation doesn't "
        "necessarily exist yet when a Saint row is first saved during "
        "fixture loading. Safe to run repeatedly -- already-slugged rows "
        "are left untouched, so URLs stay stable across reruns."
    )

    def handle(self, *args, **options):
        existing_slugs = set(
            Saint.objects.exclude(slug__isnull=True).values_list('slug', flat=True)
        )

        unslugged = (
            Saint.objects.filter(slug__isnull=True)
            .prefetch_related('daycommemoration_set__day')
            .order_by('pk')
        )

        created = 0
        with transaction.atomic():
            for saint in unslugged:
                base = saint.full_name or saint.name

                fixed_dates = sorted(
                    (dc.day.month, dc.day.day)
                    for dc in saint.daycommemoration_set.all()
                    if dc.day.pdist == 999
                )

                if fixed_dates:
                    month, day = fixed_dates[0]
                    base_slug = slugify(f'{base} {month}-{day}')
                else:
                    base_slug = slugify(base)

                if not base_slug:
                    base_slug = f'saint-{saint.pk}'

                slug = base_slug
                suffix = 2
                while slug in existing_slugs:
                    slug = f'{base_slug}-{suffix}'
                    suffix += 1

                saint.slug = slug
                saint.save(update_fields=['slug'])
                existing_slugs.add(slug)
                created += 1

        self.stdout.write(f'Backfilled {created} slug(s); {len(existing_slugs) - created} already had one.')
