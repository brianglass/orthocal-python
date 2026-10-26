from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calendarium', '0012_day_fast_cap_exempt'),
    ]

    operations = [
        migrations.AddField(
            model_name='reading',
            name='displaces_sunday',
            field=models.BooleanField(blank=True, null=True),
        ),
    ]
