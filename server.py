import logging
import os

from unittest.mock import patch

import uvicorn

from uvicorn.supervisors import multiprocess

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Process(multiprocess.Process):
    def start(self):
        super().start()
        logger.info(f"Started process {self.process.pid}.")

    def always_pong(self):
        pid = os.getpid()
        logger.info(f"always_pong thread is starting for process {pid}.")
        super().always_pong()

    def target(self, *args, **kwargs):
        pid = os.getpid()
        logger.info(f"New worker {pid} is starting.")
        return super().target(*args, **kwargs)

    def is_alive(self, timeout: float = 5) -> bool:
        if not self.process.is_alive():
            logger.error(f"Process {self.process.pid} is not alive.")
            return False

        ping = self.ping(timeout)
        if not ping:
            logger.error(f"Failed to ping {self.process.pid}.")

        return ping


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
