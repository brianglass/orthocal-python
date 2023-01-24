# Generated by Django 4.1.4 on 2023-01-24 00:43

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

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
                'index_together': {('month', 'day')},
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
                'index_together': {('month', 'day')},
            },
        ),
    ]
