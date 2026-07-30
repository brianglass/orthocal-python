from django.db import migrations

from bible.parse import parse_usfx

TRANSLATION = 'lxx2012-web'

# Only these WEB books are used -- the rest of that file is WEB's own OT and
# Deuterocanon, which we don't want here since LXX2012 supplies the OT half
# of this pairing instead.
NT_BOOKS = {
    'MAT', 'MRK', 'LUK', 'JHN', 'ACT', 'ROM', '1CO', '2CO', 'GAL', 'EPH',
    'PHP', 'COL', '1TH', '2TH', '1TI', '2TI', 'TIT', 'PHM', 'HEB', 'JAS',
    '1PE', '2PE', '1JN', '2JN', '3JN', 'JUD', 'REV',
}


def load_lxx2012_web(apps, schema_editor):
    Verse = apps.get_model('bible', 'Verse')

    for verse in parse_usfx('data/eng-lxx2012_usfx.xml'):
        if verse['chapter'] is None or verse['verse'] is None:
            continue
        Verse.objects.create(language='en', translation=TRANSLATION, **verse)

    for verse in parse_usfx('data/eng-web_usfx.xml'):
        if verse['book'] not in NT_BOOKS:
            continue
        if verse['chapter'] is None or verse['verse'] is None:
            continue
        Verse.objects.create(language='en', translation=TRANSLATION, **verse)


def unload_lxx2012_web(apps, schema_editor):
    Verse = apps.get_model('bible', 'Verse')
    Verse.objects.filter(translation=TRANSLATION).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('bible', '0003_add_translation_field'),
    ]

    operations = [
        migrations.RunPython(load_lxx2012_web, unload_lxx2012_web),
    ]
