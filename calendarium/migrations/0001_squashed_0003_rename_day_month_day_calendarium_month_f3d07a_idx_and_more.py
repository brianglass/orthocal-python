# Generated by Django 5.0.7 on 2024-08-08 13:32

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    replaces = [('calendarium', '0001_initial'), ('calendarium', '0002_alter_pericope_unique_together'), ('calendarium', '0003_rename_day_month_day_calendarium_month_f3d07a_idx_and_more')]

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Composite',
            fields=[
                ('composite_num', models.SmallIntegerField(primary_key=True, serialize=False)),
                ('content', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='Pericope',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pericope', models.CharField(max_length=8)),
                ('book', models.CharField(max_length=16)),
                ('display', models.CharField(max_length=128)),
                ('sdisplay', models.CharField(max_length=64)),
                ('desc', models.CharField(max_length=128)),
                ('preverse', models.CharField(max_length=8)),
                ('prefix', models.CharField(max_length=255)),
                ('prefixb', models.CharField(max_length=128)),
                ('verses', models.CharField(max_length=128)),
                ('suffix', models.CharField(max_length=255)),
                ('flag', models.SmallIntegerField()),
            ],
            options={
                'unique_together': {('pericope', 'book')},
            },
        ),
        migrations.CreateModel(
            name='Day',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pdist', models.SmallIntegerField(db_index=True)),
                ('month', models.SmallIntegerField()),
                ('day', models.SmallIntegerField()),
                ('title', models.CharField(max_length=255)),
                ('subtitle', models.CharField(max_length=128)),
                ('feast_name', models.CharField(max_length=255)),
                ('feast_level', models.SmallIntegerField()),
                ('service', models.SmallIntegerField()),
                ('service_note', models.CharField(max_length=64)),
                ('saint', models.CharField(max_length=128)),
                ('fast', models.SmallIntegerField()),
                ('fast_exception', models.SmallIntegerField()),
                ('flag', models.SmallIntegerField()),
            ],
            options={
                'indexes': [models.Index(fields=['month', 'day'], name='calendarium_month_f3d07a_idx')],
            },
        ),
        migrations.CreateModel(
            name='Reading',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('month', models.SmallIntegerField()),
                ('day', models.SmallIntegerField()),
                ('pdist', models.SmallIntegerField(db_index=True)),
                ('source', models.CharField(max_length=64)),
                ('desc', models.CharField(max_length=64)),
                ('ordering', models.SmallIntegerField()),
                ('flag', models.SmallIntegerField()),
                ('pericope', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='calendarium.pericope')),
            ],
            options={
                'indexes': [models.Index(fields=['month', 'day'], name='calendarium_month_f02834_idx')],
            },
        ),
    ]
