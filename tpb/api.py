"""Apibay API Client for querying torrents and fetching file details."""

import os
from typing import List, Optional
import httpx

from tpb.models import Torrent
from tpb.parser import enrich_torrent_metadata

DEFAULT_BASE_URL = os.environ.get("APIBAY_BASE_URL", "https://apibay.org")
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# TPB Categories
CAT_ALL = "0"
CAT_VIDEO = "200"
CAT_MOVIES = "201"
CAT_MOVIES_HD = "207"
CAT_TV = "205"
CAT_TV_HD = "208"


class ApibayError(Exception):
    """Base exception for Apibay API errors."""
    pass


class ApibayConnectionError(ApibayError):
    """Raised when network connection fails or times out."""
    pass


class ApibayClient:
    """Client for the apibay.org JSON API."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 15.0,
        proxy: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.proxy = proxy or os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY")
        self.headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "application/json, text/plain, */*",
        }
        self._cache = {}

    def _get_client(self) -> httpx.Client:
        kwargs = {
            "headers": self.headers,
            "timeout": self.timeout,
            "follow_redirects": True,
        }
        if self.proxy:
            kwargs["proxy"] = self.proxy
        return httpx.Client(**kwargs)

    def search(
        self,
        query: str,
        category: Optional[str] = None,
        use_cache: bool = True,
    ) -> List[Torrent]:
        """
        Search apibay for a query string.
        Returns a list of parsed Torrent models sorted by seeders descending.
        """
        clean_query = query.strip()
        if not clean_query:
            return []

        cache_key = (clean_query.lower(), category or "")
        if use_cache and cache_key in self._cache:
            return list(self._cache[cache_key])

        url = f"{self.base_url}/q.php"
        params = {"q": clean_query}
        if category:
            params["cat"] = category

        try:
            with self._get_client() as client:
                response = client.get(url, params=params)
                if response.status_code != 200:
                    raise ApibayError(f"Apibay returned HTTP status {response.status_code}")
                data = response.json()
        except httpx.RequestError as exc:
            raise ApibayConnectionError(f"Could not connect to {self.base_url}: {exc}") from exc
        except ValueError as exc:
            raise ApibayError(f"Failed to parse JSON response from Apibay: {exc}") from exc

        if not isinstance(data, list):
            return []

        # Check for dummy "No results returned" item
        if len(data) == 1 and (data[0].get("id") == "0" or data[0].get("name") == "No results returned"):
            return []

        torrents: List[Torrent] = []
        for item in data:
            try:
                torrent = Torrent(
                    id=str(item.get("id", "")),
                    name=str(item.get("name", "")).strip(),
                    info_hash=str(item.get("info_hash", "")).strip(),
                    leechers=int(item.get("leechers", 0)),
                    seeders=int(item.get("seeders", 0)),
                    size_bytes=int(item.get("size", 0)),
                    username=str(item.get("username", "")),
                    added=int(item.get("added", 0)),
                    status=str(item.get("status", "member")),
                    category=str(item.get("category", "0")),
                    imdb=str(item.get("imdb", "")),
                )
                torrent = enrich_torrent_metadata(torrent)
                torrents.append(torrent)
            except (ValueError, TypeError):
                continue

        # Sort by seeders descending
        torrents.sort(key=lambda t: t.seeders, reverse=True)
        self._cache[cache_key] = torrents
        return torrents

    def get_files(self, torrent_id: str) -> List[dict]:
        """Retrieve the list of files and sizes for a given torrent ID."""
        url = f"{self.base_url}/f.php"
        params = {"id": torrent_id}

        try:
            with self._get_client() as client:
                response = client.get(url, params=params)
                if response.status_code != 200:
                    raise ApibayError(f"Apibay returned HTTP status {response.status_code}")
                return response.json()
        except httpx.RequestError as exc:
            raise ApibayConnectionError(f"Could not connect to {self.base_url}: {exc}") from exc
        except ValueError as exc:
            raise ApibayError(f"Failed to parse file list JSON from Apibay: {exc}") from exc
