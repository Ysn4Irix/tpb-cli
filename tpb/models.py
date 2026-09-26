"""Data models for torrents and metadata."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List
import urllib.parse

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
        bytes_val = float(self.size_bytes)
        for unit in ["B", "KiB", "MiB", "GiB", "TiB"]:
            if bytes_val < 1024.0 or unit == "TiB":
                return f"{bytes_val:.2f} {unit}" if unit != "B" else f"{int(bytes_val)} B"
            bytes_val /= 1024.0
        return f"{self.size_bytes} B"

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
