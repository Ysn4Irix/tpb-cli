"""Network, quality, cache, and appearance settings dialog."""

from typing import Callable, Optional
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from tpb.api import DEFAULT_BASE_URL
from tpb.gui.state import AppStateStore


class SettingsDialog(QDialog):
    """Modal dialog editing Apibay endpoint, proxy URL, default quality, and theme."""

    cache_cleared = Signal()

    def __init__(
        self,
        state_store: AppStateStore,
        clear_cache_cb: Optional[Callable[[], None]] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("tpb-cli Settings")
        self.setMinimumWidth(420)
        self.state_store = state_store
        self._clear_cache_cb = clear_cache_cb
        self._build_ui()
        self._load_values()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

        self.api_url_input = QLineEdit()
        self.api_url_input.setPlaceholderText(DEFAULT_BASE_URL)

        self.proxy_input = QLineEdit()
        self.proxy_input.setPlaceholderText("e.g. socks5://127.0.0.1:9050 or http://127.0.0.1:8080")

        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["1080p", "720p", "2160p", "480p", "Any"])

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])

        form.addRow("Apibay Mirror URL:", self.api_url_input)
        form.addRow("HTTP / SOCKS5 Proxy:", self.proxy_input)
        form.addRow("Default TV Quality:", self.quality_combo)
        form.addRow("Theme:", self.theme_combo)
        root.addLayout(form)

        cache_row = QHBoxLayout()
        self.clear_cache_btn = QPushButton("Clear Search Cache")
        self.cache_status_label = QLabel("")
        self.cache_status_label.setObjectName("MutedLabel")
        cache_row.addWidget(self.clear_cache_btn)
        cache_row.addWidget(self.cache_status_label)
        cache_row.addStretch(1)
        root.addLayout(cache_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self.clear_cache_btn.clicked.connect(self._on_clear_cache)

    def _load_values(self) -> None:
        s = self.state_store.settings
        self.api_url_input.setText(s.api_url)
        self.proxy_input.setText(s.proxy)
        if s.default_quality in ("1080p", "720p", "2160p", "480p", "Any"):
            self.quality_combo.setCurrentText(s.default_quality)
        self.theme_combo.setCurrentText("Light" if s.theme == "light" else "Dark")

    def _on_clear_cache(self) -> None:
        if self._clear_cache_cb is not None:
            self._clear_cache_cb()
        self.cache_status_label.setText("Cache cleared.")
        self.cache_cleared.emit()

    def _on_save(self) -> None:
        s = self.state_store.settings
        s.api_url = self.api_url_input.text().strip() or DEFAULT_BASE_URL
        s.proxy = self.proxy_input.text().strip()
        s.default_quality = self.quality_combo.currentText()
        s.theme = self.theme_combo.currentText().lower()
        self.state_store.save()
        self.accept()
