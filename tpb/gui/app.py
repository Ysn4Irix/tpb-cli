"""Application launcher and QApplication lifecycle entrypoint for tpb-gui."""

import sys
from collections.abc import Sequence
from PySide6.QtWidgets import QApplication

from tpb.gui.assets import load_app_icon
from tpb.gui.main_window import MainWindow
from tpb.gui.state import AppStateStore
from tpb.gui.theme import build_stylesheet


def create_application(argv: Sequence[str] | None = None) -> QApplication:
    """Create or reuse the singleton QApplication configured for desktop styling."""
    existing = QApplication.instance()
    if isinstance(existing, QApplication):
        app = existing
    else:
        app = QApplication(list(argv) if argv is not None else sys.argv)
    app.setApplicationName("tpb-cli")
    app.setOrganizationName("Ysn4Irix")
    app_icon = load_app_icon()
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)
    return app


def main(
    argv: Sequence[str] | None = None,
    api_url: str | None = None,
    proxy: str | None = None,
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
