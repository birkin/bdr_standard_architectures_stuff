import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lib.utils import atomic_write_json


@dataclass
class Cache:
    cache_dir: Path
    refresh_cache: bool = False

    def read(self, prefix: str, key_data: dict[str, Any]) -> dict[str, Any] | None:
        """
        Reads a cached JSON response if one exists.
        Called by: lib.api.ApiClient._request_json()
        """
        cached_data = None
        path = self.path_for(prefix, key_data)
        if path.exists() and not self.refresh_cache:
            with path.open('r', encoding='utf-8') as file_object:
                cached_data = json.load(file_object)
        return cached_data

    def write(self, prefix: str, key_data: dict[str, Any], data: dict[str, Any]) -> None:
        """
        Writes a JSON response to the cache.
        Called by: lib.api.ApiClient._request_json()
        """
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path = self.path_for(prefix, key_data)
        atomic_write_json(path, data)

    def path_for(self, prefix: str, key_data: dict[str, Any]) -> Path:
        """
        Builds a deterministic cache path for request data.
        Called by: Cache.read()
        """
        payload = json.dumps(key_data, sort_keys=True, separators=(',', ':'))
        digest = hashlib.sha256(payload.encode('utf-8')).hexdigest()
        path = self.cache_dir / f'{prefix}_{digest}.json'
        return path
