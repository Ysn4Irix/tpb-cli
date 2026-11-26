"""Packaged icon and visual asset helpers for tpb-gui."""

from pathlib import Path
import sys
from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon


def _asset_dir() -> Path:
    """Resolve the packaged assets directory in editable, wheel, and PyInstaller builds."""
    local_dir = Path(__file__).resolve().parent
    if (local_dir / "tpb-gui.png").exists():
        return local_dir
    meipass = getattr(sys, "_MEIPASS", None)
    if isinstance(meipass, str) and meipass:
        frozen_dir = Path(meipass) / "tpb" / "gui" / "assets"
        if frozen_dir.exists():
            return frozen_dir
    return local_dir


def get_app_icon_path() -> Path | None:
    """Return path to the primary PNG application icon if available."""
    candidate = _asset_dir() / "tpb-gui.png"
    return candidate if candidate.exists() else None


def load_app_icon() -> QIcon:
    """Load the multi-resolution application icon for Qt windows and dialogs."""
    icon = QIcon()
    assets = _asset_dir()
    for size, filename in (
        (256, "tpb-gui.png"),
        (64, "tpb-gui-64.png"),
        (32, "tpb-gui-32.png"),
    ):
        path = assets / filename
        if path.exists():
            icon.addFile(str(path), QSize(size, size))
    return icon
