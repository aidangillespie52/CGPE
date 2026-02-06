# cgpe/http/header_rotator.py

from itertools import cycle
from cgpe.http.headers import build_headers
from cgpe.logging.logger import setup_logger

log = setup_logger(__name__)


class HeaderRotator:
    def __init__(self, n: int = 5):
        log.info("Initializing HeaderRotator with %d header sets", n)

        # pre-build a small pool of realistic headers
        self._pool_size = n
        self._headers = cycle(build_headers() for _ in range(n))

    def next(self) -> dict:
        headers = next(self._headers)

        log.debug(
            "Rotated headers (User-Agent=%s)",
            headers.get("User-Agent"),
        )

        return headers
