# Generated by Django 4.1.4 on 2023-01-17 13:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('commemorations', '0003_alter_commemoration_story'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='commemoration',
            options={'ordering': ('ordering',)},
        ),
        migrations.AddField(
            model_name='commemoration',
            name='ordering',
            field=models.SmallIntegerField(default=1),
            preserve_default=False,
        ),
    ]
