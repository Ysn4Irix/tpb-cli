"""Collapsible History and Bookmarks drawer widget."""

from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from tpb.gui.state import AppStateStore

QUERY_DATA_ROLE = Qt.UserRole + 20
MODE_DATA_ROLE = Qt.UserRole + 21


class LibraryDrawer(QFrame):
    """Displays recent search history and saved bookmarks for 1-click re-running."""

    search_requested = Signal(str, str)
    bookmarks_changed = Signal()
    close_requested = Signal()

    def __init__(self, state_store: AppStateStore, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("PanelSurface")
        self.state_store = state_store
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        top_bar = QHBoxLayout()
        self.hide_btn = QPushButton("Hide")
        top_bar.addStretch(1)
        top_bar.addWidget(self.hide_btn)
        layout.addLayout(top_bar)

        self.tabs = QTabWidget()

        # History tab
        history_tab = QWidget()
        h_layout = QVBoxLayout(history_tab)
        h_layout.setContentsMargins(4, 6, 4, 4)
        self.history_list = QListWidget()
        self.clear_history_btn = QPushButton("Clear History")
        h_layout.addWidget(self.history_list, stretch=1)
        h_layout.addWidget(self.clear_history_btn)

        # Bookmarks tab
        bookmarks_tab = QWidget()
        b_layout = QVBoxLayout(bookmarks_tab)
        b_layout.setContentsMargins(4, 6, 4, 4)
        self.bookmarks_list = QListWidget()
        self.remove_bookmark_btn = QPushButton("Remove Selected")
        b_layout.addWidget(self.bookmarks_list, stretch=1)
        b_layout.addWidget(self.remove_bookmark_btn)

        self.tabs.addTab(history_tab, "History")
        self.tabs.addTab(bookmarks_tab, "Bookmarks")
        layout.addWidget(self.tabs, stretch=1)

        self.history_list.itemDoubleClicked.connect(self._on_item_activated)
        self.bookmarks_list.itemDoubleClicked.connect(self._on_item_activated)
        self.clear_history_btn.clicked.connect(self._on_clear_history)
        self.remove_bookmark_btn.clicked.connect(self._on_remove_bookmark)
        self.hide_btn.clicked.connect(self.close_requested.emit)

    def refresh(self) -> None:
        """Reload list items from the backing AppStateStore."""
        self.history_list.clear()
        for entry in self.state_store.history:
            badge = entry.mode.upper()
            item = QListWidgetItem(f"[{badge}] {entry.query}")
            item.setToolTip(entry.timestamp)
            item.setData(QUERY_DATA_ROLE, entry.query)
            item.setData(MODE_DATA_ROLE, entry.mode)
            self.history_list.addItem(item)

        self.bookmarks_list.clear()
        for bm in self.state_store.bookmarks:
            badge = bm.mode.upper()
            item = QListWidgetItem(f"[{badge}] {bm.title}")
            item.setToolTip(f"Added: {bm.added_at}")
            item.setData(QUERY_DATA_ROLE, bm.title)
            item.setData(MODE_DATA_ROLE, bm.mode)
            self.bookmarks_list.addItem(item)

        self.clear_history_btn.setEnabled(bool(self.state_store.history))
        self.remove_bookmark_btn.setEnabled(bool(self.state_store.bookmarks))

    def _on_item_activated(self, item: QListWidgetItem) -> None:
        query = item.data(QUERY_DATA_ROLE)
        mode = item.data(MODE_DATA_ROLE)
        if query and mode:
            self.search_requested.emit(str(query), str(mode))

    def _on_clear_history(self) -> None:
        self.state_store.clear_history()
        self.refresh()

    def _on_remove_bookmark(self) -> None:
        item = self.bookmarks_list.currentItem()
        if item is None:
            return
        title = item.data(QUERY_DATA_ROLE)
        mode = item.data(MODE_DATA_ROLE)
        if title and mode:
            self.state_store.remove_bookmark(str(title), str(mode))
            self.refresh()
            self.bookmarks_changed.emit()
