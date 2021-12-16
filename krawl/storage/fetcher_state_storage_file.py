from __future__ import annotations

import json
import logging
from pathlib import Path

from krawl.storage import FetcherStateStorage

log = logging.getLogger("fetcher-state-storage")


class FetcherStateStorageFile(FetcherStateStorage):
    """Storing and loading the state of a fetcher."""

    def __init__(self, base_path: Path):
        self._base_path = base_path / "__fetcher__"

    def load(self, fetcher: str) -> dict:
        path = self._get_path(fetcher)
        if not path.exists():
            log.debug("state storage for fetcher '%s' doesn't exist, returning empty default", fetcher)
            return {}
        serialized = path.read_text()
        deserialized = json.loads(serialized)
        return deserialized

    def store(self, fetcher: str, state: dict) -> None:
        path = self._get_path(fetcher)
        log.debug("saving state of fetcher '%s' (%s)", fetcher, str(path))
        path.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(state, indent=4)
        path.write_text(serialized)

    def delete(self, fetcher: str) -> bool:
        path = self._get_path(fetcher)
        if not path.exists():
            return False
        log.debug("deleting state storage of fetcher '%s' (%s)", fetcher, str(path))
        path.unlink()
        return True

    def _get_path(self, fetcher: str) -> Path:
        return self._base_path / (fetcher + ".json")