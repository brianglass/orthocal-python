import shutil

from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.test.runner import DiscoverRunner

FIXTURES = [settings.BASE_DIR / 'fixtures' / f'{name}.json' for name in ('calendarium', 'commemorations')]


class FixtureRunner(DiscoverRunner):
    """Start the tests from the database the Docker image already built.

    The image's db.sqlite3 has every migration applied -- including the three
    that load the scriptures, about 40s -- and the calendar and commemoration
    data loaded, with the slugs, normalized names and search index the
    Dockerfile builds. The test database starts as a copy of it. Each test
    still rolls back its own changes, and no test uses TransactionTestCase,
    which would empty the tables.

    Without a current db.sqlite3 (one older than the fixtures, say), the test
    database is built from scratch and the data loaded into it once, which is
    still far cheaper than each test class loading its own fixtures."""

    def setup_databases(self, **kwargs):
        copied = self._copy_built_database()
        if copied:
            self.keepdb = True

        config = super().setup_databases(**kwargs)

        if not copied:
            quiet = {'stdout': StringIO()}
            call_command('loaddata', *(path.stem for path in FIXTURES), verbosity=0)
            call_command('backfill_saint_slugs', **quiet)
            call_command('backfill_saint_normalized_names', **quiet)
            call_command('build_saint_search_index', **quiet)

        return config

    def _copy_built_database(self):
        database = settings.DATABASES['default']
        built, test = Path(database['NAME']), Path(database['TEST']['NAME'])

        if not built.exists() or test.exists():
            return False
        if any(built.stat().st_mtime < path.stat().st_mtime for path in FIXTURES):
            return False

        shutil.copyfile(built, test)
        return True
