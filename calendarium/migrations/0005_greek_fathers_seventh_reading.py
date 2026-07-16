# Retag the existing FloatIndex.FathersSeventh (pdist=1002) Epistle/Gospel
# rows as Slavic-specific, and add the Antiochian/Greek citation (Titus
# 3.8-15 / Luke 8.5-15) confirmed against four years (2023-2026) of
# antiochian.org official liturgical charts. See GreekYear's docstring in
# calendarium/liturgics/year.py for the full derivation.

from django.db import migrations


def add_greek_reading(apps, schema_editor):
    Reading = apps.get_model('calendarium', 'Reading')
    Pericope = apps.get_model('calendarium', 'Pericope')

    # A no-op against a freshly migrated (fixture-less) database, such as the
    # test database before fixtures are loaded -- this migration only has
    # real data to act on against the production/dev database.
    titus = Pericope.objects.filter(sdisplay='Titus 3.8-15').first()
    luke = Pericope.objects.filter(sdisplay='Luke 8.5-15').first()
    if titus is None or luke is None:
        return

    Reading.objects.filter(pdist=1002, source__in=('Epistle', 'Gospel')).update(tradition='slavic')

    Reading.objects.create(
        pdist=1002, month=0, day=0, source='Epistle', desc='Fathers',
        pericope=titus, ordering=821, flag=0, tradition='greek',
    )
    Reading.objects.create(
        pdist=1002, month=0, day=0, source='Gospel', desc='Fathers',
        pericope=luke, ordering=921, flag=0, tradition='greek',
    )


def remove_greek_reading(apps, schema_editor):
    Reading = apps.get_model('calendarium', 'Reading')
    Reading.objects.filter(pdist=1002, tradition='greek').delete()
    Reading.objects.filter(pdist=1002, source__in=('Epistle', 'Gospel'), tradition='slavic').update(tradition='common')


class Migration(migrations.Migration):

    dependencies = [
        ('calendarium', '0004_reading_tradition'),
    ]

    operations = [
        migrations.RunPython(add_greek_reading, remove_greek_reading),
    ]
