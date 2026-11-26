"""Apibay API Client for querying torrents and fetching file details."""

import os
import threading
from urllib.parse import urlparse
import httpx

from tpb.models import Torrent, TorrentFile, normalize_torrent_files
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


def validate_http_url(url: str) -> str:
    """Validate and normalize an HTTP/HTTPS base URL for Apibay requests."""
    cleaned = url.strip().rstrip("/")
    parsed = urlparse(cleaned)
    if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
        raise ValueError("API URL must start with http:// or https:// and include a hostname.")
    return cleaned


def validate_proxy_url(proxy: str | None) -> str | None:
    """Validate an optional HTTP or SOCKS proxy URL; empty strings resolve to None."""
    if proxy is None or not proxy.strip():
        return None
    cleaned = proxy.strip()
    parsed = urlparse(cleaned)
    if parsed.scheme.lower() not in ("http", "https", "socks5", "socks5h") or not parsed.netloc:
        raise ValueError(
            "Proxy URL must use http://, https://, socks5://, or socks5h:// and include a host."
        )
    return cleaned


class ApibayClient:
    """Client for the apibay.org JSON API."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 15.0,
        proxy: str | None = None,
    ):
        self.base_url = validate_http_url(base_url)
        self.timeout = timeout
        raw_proxy = proxy or os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY")
        self.proxy = validate_proxy_url(raw_proxy)
        self.headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "application/json, text/plain, */*",
        }
        self._cache_lock = threading.Lock()
        self._cache: dict[tuple[str, str], list[Torrent]] = {}
        self._files_cache: dict[str, list[TorrentFile]] = {}

    def reconfigure(self, base_url: str, proxy: str | None = None) -> None:
        """Validate and update endpoint/proxy settings, clearing cached query state."""
        validated_url = validate_http_url(base_url)
        validated_proxy = validate_proxy_url(proxy)
        self.base_url = validated_url
        self.proxy = validated_proxy
        self.clear_cache()

    def clear_cache(self) -> None:
        """Clear cached search and file-list responses."""
        with self._cache_lock:
            self._cache.clear()
            self._files_cache.clear()

    def _get_client(self) -> httpx.Client:
        return httpx.Client(
            headers=self.headers,
            timeout=self.timeout,
            follow_redirects=True,
            proxy=self.proxy,
        )

    def search(
        self,
        query: str,
        category: str | None = None,
        use_cache: bool = True,
    ) -> list[Torrent]:
        """
        Search apibay for a query string.
        Returns a list of parsed Torrent models sorted by seeders descending.
        """
        clean_query = query.strip()
        if not clean_query:
            return []

        cache_key = (clean_query.lower(), category or "")
        if use_cache:
            with self._cache_lock:
                if cache_key in self._cache:
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
            with self._cache_lock:
                self._cache[cache_key] = []
            return []

        # Check for dummy "No results returned" item
        if len(data) == 1 and (
            data[0].get("id") == "0" or data[0].get("name") == "No results returned"
        ):
            with self._cache_lock:
                self._cache[cache_key] = []
            return []

        torrents: list[Torrent] = []
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
        with self._cache_lock:
            self._cache[cache_key] = torrents
        return list(torrents)

    def get_files(self, torrent_id: str) -> list[dict]:
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

    def get_parsed_files(self, torrent_id: str, use_cache: bool = True) -> list[TorrentFile]:
        """Retrieve and normalize file entries for a given torrent ID, with thread-safe caching."""
        clean_id = str(torrent_id).strip()
        if not clean_id:
            return []

        if use_cache:
            with self._cache_lock:
                if clean_id in self._files_cache:
                    return list(self._files_cache[clean_id])

        raw_files = self.get_files(clean_id)
        parsed = normalize_torrent_files(raw_files)
        with self._cache_lock:
            self._files_cache[clean_id] = parsed
        return list(parsed)
