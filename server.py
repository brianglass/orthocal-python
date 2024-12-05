import datetime
import logging
import os

from unittest.mock import patch

import uvicorn

from uvicorn.supervisors import multiprocess

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# The multiprocess supervisor does not work correctly in Google Cloud Run.
# See https://github.com/encode/uvicorn/discussions/2399
class Process(multiprocess.Process):
    def ping(self, *args, **kwargs):
        return True


@patch('uvicorn.supervisors.multiprocess.Process', Process)
def main():
    logger.info("Starting Uvicorn.")

    port = int(os.environ.get('PORT', 8000))
    reload = os.environ.get('UVICORN_RELOAD', 'false').lower() == 'true'

    uvicorn.run(
        app='orthocal.asgi:application',
        host='0.0.0.0',
        port=port,
        lifespan='off',
        log_level='debug',
        reload=reload,
    )

if __name__ == '__main__':
    main()
