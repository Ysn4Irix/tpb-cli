"""Data models for torrents and metadata."""

import re
from dataclasses import dataclass, field, fields
from datetime import datetime, timezone
from typing import Optional, List, Sequence, Any
import urllib.parse


def format_bytes(size_bytes: int | float) -> str:
    """Format a byte count into a human-readable IEC unit string (e.g. 1.45 GiB)."""
    bytes_val = float(max(0, size_bytes))
    for unit in ["B", "KiB", "MiB", "GiB", "TiB"]:
        if bytes_val < 1024.0 or unit == "TiB":
            return f"{bytes_val:.2f} {unit}" if unit != "B" else f"{int(bytes_val)} B"
        bytes_val /= 1024.0
    return f"{int(size_bytes)} B"


def sanitize_filename(name: str) -> str:
    """Convert a show or title string into a filesystem-safe slug."""
    clean = re.sub(r"[^\w\s-]", "", name.lower())
    clean = re.sub(r"[\s_]+", "_", clean).strip("_")
    return clean or "torrents"

# List of high-uptime public trackers
DEFAULT_TRACKERS = [
    "udp://tracker.opentrackr.org:1337/announce",
    "udp://open.stealth.si:80/announce",
    "udp://tracker.torrent.eu.org:451/announce",
    "udp://tracker.bittor.pw:1337/announce",
    "udp://public.popcorn-tracker.org:6969/announce",
    "udp://tracker.dler.org:6969/announce",
    "udp://exodus.desync.com:6969/announce",
    "udp://open.demonii.com:1337/announce",
]


@dataclass
class Torrent:
    id: str
    name: str
    info_hash: str
    leechers: int
    seeders: int
    size_bytes: int
    username: str = ""
    added: int = 0
    status: str = "member"
    category: str = "0"
    imdb: str = ""
    season: Optional[int] = None
    episode: Optional[int] = None
    episodes: List[int] = field(default_factory=list)
    is_season_pack: bool = False
    quality: str = "Unknown"
    codec: str = "Unknown"

    @property
    def magnet_link(self) -> str:
        """Construct a magnet link with standard high-reliability trackers."""
        if not self.info_hash or self.info_hash == "0000000000000000000000000000000000000000":
            return ""
        encoded_name = urllib.parse.quote(self.name)
        params = [f"xt=urn:btih:{self.info_hash}", f"dn={encoded_name}"]
        for tracker in DEFAULT_TRACKERS:
            params.append(f"tr={urllib.parse.quote(tracker)}")
        return "magnet:?" + "&".join(params)

    @property
    def human_size(self) -> str:
        """Return human-readable file size (e.g. 1.45 GiB)."""
        return format_bytes(self.size_bytes)

    @property
    def formatted_date(self) -> str:
        """Return formatted date string from timestamp."""
        if not self.added:
            return "N/A"
        try:
            return datetime.fromtimestamp(self.added, tz=timezone.utc).strftime("%Y-%m-%d")
        except Exception:
            return "N/A"

    @property
    def is_vip(self) -> bool:
        return self.status.lower() == "vip"

    @property
    def is_trusted(self) -> bool:
        return self.status.lower() == "trusted"


def ensure_torrent(item: Any) -> Torrent:
    """
    Ensure an item is a Torrent instance; if it is a dict, reconstruct a Torrent from it.
    Supports dicts from dataclasses.asdict(t) as well as raw Apibay API dictionaries.
    """
    if isinstance(item, Torrent):
        return item
    if isinstance(item, dict):
        field_names = {f.name for f in fields(Torrent)}
        d = dict(item)
        if "size" in d and "size_bytes" not in d:
            try:
                d["size_bytes"] = int(d.pop("size"))
            except (ValueError, TypeError):
                d["size_bytes"] = 0
        if "id" in d:
            d["id"] = str(d["id"])
        if "seeders" in d:
            try:
                d["seeders"] = int(d["seeders"])
            except (ValueError, TypeError):
                d["seeders"] = 0
        if "leechers" in d:
            try:
                d["leechers"] = int(d["leechers"])
            except (ValueError, TypeError):
                d["leechers"] = 0
        filtered = {k: v for k, v in d.items() if k in field_names}
        return Torrent(**filtered)
    raise TypeError(f"Expected Torrent or dict, got {type(item)}")


def ensure_torrents(items: Sequence[Any]) -> List[Torrent]:
    """Ensure all items in sequence are Torrent instances."""
    if not items:
        return []
    return [ensure_torrent(item) for item in items]


@dataclass
class TorrentFile:
    """Normalized file entry inside a torrent payload."""

    name: str
    size_bytes: int

    @property
    def human_size(self) -> str:
        """Return human-readable file size."""
        return format_bytes(self.size_bytes)


def normalize_torrent_files(raw_files: Any) -> List[TorrentFile]:
    """Normalize raw Apibay /f.php file-list payloads into TorrentFile records."""
    if not isinstance(raw_files, list):
        return []

    normalized: List[TorrentFile] = []
    for item in raw_files:
        if isinstance(item, TorrentFile):
            normalized.append(item)
            continue
        if not isinstance(item, dict):
            continue

        raw_name = item.get("name", "")
        if isinstance(raw_name, list):
            name = "/".join(str(part).strip() for part in raw_name if str(part).strip())
        else:
            name = str(raw_name).strip()

        if not name:
            continue

        raw_size = item.get("size", item.get("size_bytes", 0))
        if isinstance(raw_size, list):
            raw_size = raw_size[0] if raw_size else 0
        try:
            size_bytes = max(0, int(raw_size))
        except (ValueError, TypeError):
            size_bytes = 0

        if len(raw_files) == 1 and size_bytes == 0 and "not found" in name.lower():
            return []

        normalized.append(TorrentFile(name=name, size_bytes=size_bytes))

    return normalized
