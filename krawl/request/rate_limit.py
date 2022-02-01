from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from time import sleep

log = logging.getLogger("rate-limit")


class RateLimitNumRequests():

    def __init__(
            self,
            num_requests: int = 100,
            reset_time: datetime = datetime(1, 1, 1, 0, 0, tzinfo=timezone.utc),
    ) -> None:
        self._num_requests = num_requests
        self._reset_time = reset_time

    def apply(self) -> None:
        if self._num_requests <= 0:
            wait = (self._reset_time - datetime.now(timezone.utc)) / timedelta(seconds=1)
            if wait > 0.0:
                log.info("hit rate limit, now waiting %.3f seconds...", wait)
                sleep(wait)

    def update(self, num_requests: int, reset_time: datetime) -> None:
        self._num_requests = num_requests
        self._reset_time = reset_time


class RateLimitFixedTimedelta():

    def __init__(self, milliseconds: int = 0, seconds: int = 0, minutes: int = 0, hours: int = 0) -> None:
        self._timedelta = timedelta(milliseconds=milliseconds, seconds=seconds, minutes=minutes, hours=hours)
        self._last = datetime.now(timezone.utc)

    def apply(self) -> None:
        wait = (self._timedelta - (datetime.now(timezone.utc) - self._last)) / timedelta(seconds=1)
        if wait > 0.0:
            log.debug("limit request rate by waiting %.3f seconds...", wait)
            sleep(wait)

    def update(self) -> None:
        self._last = datetime.now(timezone.utc)