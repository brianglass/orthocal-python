from django.db import migrations

from bible.parse import parse_usfx

TRANSLATION = 'douay-rheims'


def load_douay_rheims(apps, schema_editor):
    Verse = apps.get_model('bible', 'Verse')
    Verse.objects.bulk_create(
        Verse(language='en', translation=TRANSLATION, **verse)
        for verse in parse_usfx('data/eng-dra_usfx.xml')
        if verse['chapter'] is not None and verse['verse'] is not None)


def unload_douay_rheims(apps, schema_editor):
    Verse = apps.get_model('bible', 'Verse')
    Verse.objects.filter(translation=TRANSLATION).delete()


class Migration(migrations.Migration):
    dependencies = [('bible', '0004_load_lxx2012_web')]
    operations = [migrations.RunPython(load_douay_rheims, unload_douay_rheims)]
