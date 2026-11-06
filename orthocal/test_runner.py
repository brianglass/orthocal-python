from io import StringIO

from django.core.management import call_command
from django.test.runner import DiscoverRunner


class FixtureRunner(DiscoverRunner):
    """Load the calendar and commemoration data once for the whole run.

    Nearly every test class needs it, and reloading it for each one through
    `TestCase.fixtures` cost half a minute a run. Each test still rolls back
    its own changes. As in the Dockerfile, loading the fixtures bypasses
    Saint.save(), so slugs and normalized names are backfilled and the search
    index built afterwards."""

    def setup_databases(self, **kwargs):
        config = super().setup_databases(**kwargs)

        quiet = {'stdout': StringIO()}
        call_command('loaddata', 'calendarium', 'commemorations', verbosity=0)
        call_command('backfill_saint_slugs', **quiet)
        call_command('backfill_saint_normalized_names', **quiet)
        call_command('build_saint_search_index', **quiet)

        return config
