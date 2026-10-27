from django.db import migrations


class Migration(migrations.Migration):
    """The full-text index behind search.matching_lives. It is an FTS5
    virtual table, which Django can't model, so it is created here and
    filled by the build_saint_search_index command after the fixtures are
    loaded (see the Dockerfile)."""

    dependencies = [
        ('commemorations', '0017_saint_normalized_name'),
    ]

    operations = [
        migrations.RunSQL(
            '''CREATE VIRTUAL TABLE commemorations_life_search USING fts5(
                title, names, story,
                tokenize = 'porter unicode61 remove_diacritics 2'
            )''',
            'DROP TABLE commemorations_life_search',
        ),
    ]
