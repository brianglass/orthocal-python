# Generated by Django 4.1.4 on 2023-01-24 14:58

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('calendarium', '0001_initial'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='pericope',
            unique_together={('pericope', 'book')},
        ),
    ]
