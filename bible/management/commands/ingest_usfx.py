from django.core.management.base import BaseCommand, CommandError

from bible import models, parse


class Command(BaseCommand):
    help = 'Ingest a USFX Bible.'

    def add_arguments(self, parser):
        parser.add_argument('path')
        parser.add_argument('-l', '--language')

    def handle(self, *args, **options):
        for verse in parse.parse_usfx(options['path'], language=options['language']):
            models.Verse.objects.create(**verse)
