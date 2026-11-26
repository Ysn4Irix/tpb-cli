"""Application launcher and QApplication lifecycle entrypoint for tpb-gui."""

import sys
from typing import Optional, Sequence
from PySide6.QtWidgets import QApplication

from tpb.gui.main_window import MainWindow
from tpb.gui.state import AppStateStore
from tpb.gui.theme import build_stylesheet


def create_application(argv: Optional[Sequence[str]] = None) -> QApplication:
    """Create or reuse the singleton QApplication configured for desktop styling."""
    existing = QApplication.instance()
    if isinstance(existing, QApplication):
        return existing
    app = QApplication(list(argv) if argv is not None else sys.argv)
    app.setApplicationName("tpb-cli")
    app.setOrganizationName("Ysn4Irix")
    return app


def main(
    argv: Optional[Sequence[str]] = None,
    api_url: Optional[str] = None,
    proxy: Optional[str] = None,
) -> int:
    """Launch the PySide6 desktop interface."""
    app = create_application(argv)
    store = AppStateStore()
    if api_url:
        store.settings.api_url = api_url.strip().rstrip("/")
    if proxy is not None:
        store.settings.proxy = proxy.strip()

    app.setStyleSheet(build_stylesheet(store.settings.theme))
    window = MainWindow(state_store=store)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
