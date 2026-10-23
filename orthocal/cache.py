import threading

from diskcache import DjangoCache, FanoutCache
from django.core.cache.backends.base import BaseCache


class DiskCache(DjangoCache):
    """diskcache's DjangoCache, sharing one open cache per process.

    Django builds a cache object per async context, so in effect per
    request, and closes every cache when a request finishes. That is cheap
    for FileBasedCache, but diskcache's constructor sets up its SQLite
    schema (a connection, about ten pragmas, nine CREATE ... IF NOT EXISTS
    and a run of settings writes), so a cache hit cost about 80 statements
    instead of a handful, and iCal hits in production took twice as long as
    with FileBasedCache. Here every instance for a location shares one
    FanoutCache, and close() leaves its connections open: they are per
    thread, the thread pool is persistent, and a short-lived thread's
    connection is closed when the thread ends.
    """

    _shared = {}
    _lock = threading.Lock()

    def __init__(self, directory, params):
        BaseCache.__init__(self, params)
        directory = str(directory)

        with self._lock:
            if (cache := self._shared.get(directory)) is None:
                cache = self._shared[directory] = FanoutCache(
                    directory,
                    params.get('SHARDS', 8),
                    params.get('DATABASE_TIMEOUT', 0.010),
                    **params.get('OPTIONS', {}),
                )

        self._cache = cache

    def close(self, **kwargs):
        pass
