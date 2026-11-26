"""Persistent settings, theme preference, search history, and bookmark store."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path

from tpb.api import DEFAULT_BASE_URL


def get_default_config_path() -> Path:
    """Resolve platform-standard JSON configuration path for tpb-cli GUI."""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config"))
    return base / "tpb-cli" / "gui_state.json"


def get_default_export_dir() -> str:
    """Return user's Downloads folder if it exists, falling back to home directory."""
    downloads = Path.home() / "Downloads"
    return str(downloads if downloads.exists() else Path.home())


@dataclass
class GuiSettings:
    """Persisted user configuration for the desktop interface."""

    theme: str = "dark"
    api_url: str = DEFAULT_BASE_URL
    proxy: str = ""
    default_quality: str = "1080p"
    last_export_dir: str = field(default_factory=get_default_export_dir)
    max_history: int = 25


@dataclass
class HistoryEntry:
    """Recorded search query entry."""

    query: str
    mode: str
    timestamp: str


@dataclass
class BookmarkItem:
    """Saved favorite TV show, movie, or search query."""

    title: str
    mode: str
    added_at: str


class AppStateStore:
    """Loads and persists GUI preferences, search history, and bookmarks."""

    def __init__(self, config_path: Path | None = None):
        self.config_path = config_path or get_default_config_path()
        self.settings = GuiSettings()
        self.history: list[HistoryEntry] = []
        self.bookmarks: list[BookmarkItem] = []
        self.load()

    def load(self) -> None:
        """Load persisted JSON state safely, falling back to defaults if corrupt or absent."""
        if not self.config_path.exists():
            return

        try:
            raw = json.loads(self.config_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return

        if not isinstance(raw, dict):
            return

        raw_settings = raw.get("settings", {})
        if isinstance(raw_settings, dict):
            theme = str(raw_settings.get("theme", "dark")).lower()
            self.settings = GuiSettings(
                theme="light" if theme == "light" else "dark",
                api_url=str(raw_settings.get("api_url") or DEFAULT_BASE_URL).strip()
                or DEFAULT_BASE_URL,
                proxy=str(raw_settings.get("proxy", "")).strip(),
                default_quality=str(raw_settings.get("default_quality", "1080p")) or "1080p",
                last_export_dir=str(
                    raw_settings.get("last_export_dir") or get_default_export_dir()
                ),
                max_history=max(5, int(raw_settings.get("max_history", 25))),
            )

        self.history = [
            HistoryEntry(
                query=str(item.get("query", "")).strip(),
                mode=str(item.get("mode", "tv")),
                timestamp=str(item.get("timestamp", "")),
            )
            for item in raw.get("history", [])
            if isinstance(item, dict) and str(item.get("query", "")).strip()
        ][: self.settings.max_history]

        self.bookmarks = [
            BookmarkItem(
                title=str(item.get("title", "")).strip(),
                mode=str(item.get("mode", "tv")),
                added_at=str(item.get("added_at", "")),
            )
            for item in raw.get("bookmarks", [])
            if isinstance(item, dict) and str(item.get("title", "")).strip()
        ]

    def save(self) -> None:
        """Persist settings, search history, and bookmarks to disk."""
        payload = {
            "settings": asdict(self.settings),
            "history": [asdict(h) for h in self.history[: self.settings.max_history]],
            "bookmarks": [asdict(b) for b in self.bookmarks],
        }
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def add_history(self, query: str, mode: str) -> None:
        """Record a search query at the top of recent history, deduplicating case-insensitively."""
        clean = query.strip()
        if not clean:
            return

        self.history = [
            h for h in self.history if not (h.query.lower() == clean.lower() and h.mode == mode)
        ]
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        self.history.insert(0, HistoryEntry(query=clean, mode=mode, timestamp=now_iso))
        self.history = self.history[: self.settings.max_history]
        self.save()

    def clear_history(self) -> None:
        """Clear all recorded search history."""
        self.history.clear()
        self.save()

    def is_bookmarked(self, title: str, mode: str) -> bool:
        """Check if a title/mode pair is currently bookmarked."""
        clean = title.strip().lower()
        return any(b.title.lower() == clean and b.mode == mode for b in self.bookmarks)

    def toggle_bookmark(self, title: str, mode: str) -> bool:
        """Add or remove a bookmark; returns True when added, False when removed."""
        clean = title.strip()
        if not clean:
            return False

        if self.is_bookmarked(clean, mode):
            self.remove_bookmark(clean, mode)
            return False

        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.bookmarks.insert(0, BookmarkItem(title=clean, mode=mode, added_at=now_iso))
        self.save()
        return True

    def remove_bookmark(self, title: str, mode: str) -> None:
        """Remove a matching bookmark."""
        clean = title.strip().lower()
        self.bookmarks = [
            b for b in self.bookmarks if not (b.title.lower() == clean and b.mode == mode)
        ]
        self.save()
