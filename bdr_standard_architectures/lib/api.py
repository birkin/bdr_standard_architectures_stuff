import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx

from lib.cache import Cache
from lib.config import SCRIPT_VERSION


log = logging.getLogger(__name__)


@dataclass
class ApiClient:
    api_root: str
    sleep_seconds: float
    cache: Cache
    client: httpx.Client

    def close(self) -> None:
        """
        Closes the underlying HTTP client.
        Called by: lib.sampler.run_sampler()
        """
        self.client.close()

    def search(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Runs a Search API request.
        Called by: lib.collections.discover_collections_from_search()
        """
        data = self._request_json('search', 'search/', params)
        return data

    def get_collections(self) -> dict[str, Any]:
        """
        Gets top-level collection API data.
        Called by: lib.collections.discover_collections_from_endpoint()
        """
        data = self._request_json('collections', 'collections/', {})
        return data

    def _request_json(self, cache_prefix: str, path: str, params: dict[str, Any]) -> dict[str, Any]:
        """
        Gets JSON from the API with cache, retries, and rate limiting.
        Called by: ApiClient.search()
        """
        key_data = {
            'script_version': SCRIPT_VERSION,
            'api_root': self.api_root,
            'path': path,
            'params': sorted(params.items()),
        }
        cached_data = self.cache.read(cache_prefix, key_data)
        if cached_data is None:
            data = self._fetch_json(path, params)
            self.cache.write(cache_prefix, key_data, data)
        else:
            data = cached_data
        return data

    def _fetch_json(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        """
        Fetches JSON with conservative retry behavior.
        Called by: ApiClient._request_json()
        """
        url = f'{self.api_root.rstrip("/")}/{path.lstrip("/")}'
        attempts = 4
        data: dict[str, Any] = {}
        for attempt_index in range(attempts):
            if self.sleep_seconds > 0:
                time.sleep(self.sleep_seconds)
            response = self.client.get(url, params=params)
            if response.status_code in {429, 502, 503, 504} and attempt_index < attempts - 1:
                delay = retry_delay(response, attempt_index)
                log.warning('Retrying %s after HTTP %s in %.1fs', url, response.status_code, delay)
                time.sleep(delay)
                continue
            response.raise_for_status()
            data = response.json()
            break
        return data


def retry_delay(response: httpx.Response, attempt_index: int) -> float:
    """
    Computes conservative retry delay.
    Called by: ApiClient._fetch_json()
    """
    retry_after = response.headers.get('Retry-After')
    delay = 2.0**attempt_index
    if retry_after:
        try:
            delay = float(retry_after)
        except ValueError:
            delay = 2.0**attempt_index
    return delay
