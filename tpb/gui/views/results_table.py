"""Sortable, filterable results table view for Movies, General search, and Season Packs."""

from typing import Any
from collections.abc import Callable
from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QPersistentModelIndex,
    QSortFilterProxyModel,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QKeyEvent
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from tpb.gui.theme import ThemePalette, get_palette
from tpb.models import Torrent

SORT_ROLE = Qt.ItemDataRole.UserRole + 1
_EMPTY_MODEL_INDEX = QModelIndex()

COLUMNS = [
    "",
    "Title",
    "Quality",
    "Codec",
    "Size",
    "Seeds",
    "Leech",
    "Uploader",
    "Date",
]


class TorrentTableModel(QAbstractTableModel):
    """Table model presenting Torrent records with checkbox selection and numeric sorting."""

    selection_toggled = Signal()

    def __init__(self, theme_name: str = "dark", parent: QWidget | None = None):
        super().__init__(parent)
        self._torrents: list[Torrent] = []
        self._checked_rows: set[int] = set()
        self._palette: ThemePalette = get_palette(theme_name)

    def set_theme(self, theme_name: str) -> None:
        """Update palette colors and notify views to repaint."""
        self._palette = get_palette(theme_name)
        if self._torrents:
            top_left = self.index(0, 0)
            bottom_right = self.index(len(self._torrents) - 1, len(COLUMNS) - 1)
            self.dataChanged.emit(top_left, bottom_right, [Qt.ItemDataRole.ForegroundRole])

    def set_torrents(self, torrents: list[Torrent], precheck_first: bool = False) -> None:
        """Replace displayed torrents and reset checkbox selections."""
        self.beginResetModel()
        self._torrents = list(torrents)
        self._checked_rows = {0} if (precheck_first and self._torrents) else set()
        self.endResetModel()
        self.selection_toggled.emit()

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = _EMPTY_MODEL_INDEX) -> int:
        return 0 if parent.isValid() else len(self._torrents)

    def columnCount(self, parent: QModelIndex | QPersistentModelIndex = _EMPTY_MODEL_INDEX) -> int:
        return 0 if parent.isValid() else len(COLUMNS)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return COLUMNS[section]
        return None

    def flags(self, index: QModelIndex | QPersistentModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        base = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if index.column() == 0:
            return base | Qt.ItemFlag.ItemIsUserCheckable
        return base

    def data(
        self,
        index: QModelIndex | QPersistentModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._torrents)):
            return None

        row = index.row()
        col = index.column()
        t = self._torrents[row]

        if col == 0:
            if role == Qt.ItemDataRole.CheckStateRole:
                return (
                    Qt.CheckState.Checked if row in self._checked_rows else Qt.CheckState.Unchecked
                )
            if role == SORT_ROLE:
                return 1 if row in self._checked_rows else 0
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            return self._display_value(t, col)

        if role == SORT_ROLE:
            return self._sort_value(t, col)

        if role == Qt.ItemDataRole.ToolTipRole:
            if col == 1:
                return f"{t.name}\nUploader: {t.username or 'Anonymous'} | InfoHash: {t.info_hash}"
            if col == 5:
                if t.seeders > 50:
                    return f"Healthy ({t.seeders} seeders)"
                if t.seeders > 5:
                    return f"Moderate ({t.seeders} seeders)"
                return f"Low ({t.seeders} seeders)"

        if role == Qt.ItemDataRole.TextAlignmentRole:
            if col in (4, 5, 6):
                return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if col in (2, 3, 8):
                return int(Qt.AlignmentFlag.AlignCenter)

        if role == Qt.ItemDataRole.ForegroundRole:
            return self._foreground_color(t, col)

        if role == Qt.ItemDataRole.FontRole and col == 5 and t.seeders > 50:
            font = QFont()
            font.setBold(True)
            return font

        return None

    def _display_value(self, t: Torrent, col: int) -> Any:
        if col == 1:
            return t.name
        if col == 2:
            return t.quality
        if col == 3:
            return t.codec
        if col == 4:
            return t.human_size
        if col == 5:
            return t.seeders
        if col == 6:
            return t.leechers
        if col == 7:
            uploader = t.username or "Anonymous"
            if t.is_vip:
                return f"[VIP] {uploader}"
            if t.is_trusted:
                return f"[TRUST] {uploader}"
            return uploader
        if col == 8:
            return t.formatted_date
        return ""

    def _sort_value(self, t: Torrent, col: int) -> Any:
        if col == 4:
            return t.size_bytes
        if col == 5:
            return t.seeders
        if col == 6:
            return t.leechers
        if col == 8:
            return t.added
        return str(self._display_value(t, col)).lower()

    def _foreground_color(self, t: Torrent, col: int) -> QColor | None:
        if col == 5:
            if t.seeders > 50:
                return QColor(self._palette.seed_high)
            if t.seeders > 5:
                return QColor(self._palette.seed_mid)
            return QColor(self._palette.seed_low)
        if col == 7:
            if t.is_vip:
                return QColor(self._palette.seed_high)
            if t.is_trusted:
                return QColor(self._palette.trusted)
        if col == 2 and t.quality in ("2160p", "1080p"):
            return QColor(self._palette.accent)
        return None

    def setData(
        self,
        index: QModelIndex | QPersistentModelIndex,
        value: Any,
        role: int = Qt.ItemDataRole.EditRole,
    ) -> bool:
        if index.isValid() and index.column() == 0 and role == Qt.ItemDataRole.CheckStateRole:
            row = index.row()
            checked = value == Qt.CheckState.Checked or value == Qt.CheckState.Checked.value
            if checked:
                self._checked_rows.add(row)
            else:
                self._checked_rows.discard(row)
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.CheckStateRole])
            self.selection_toggled.emit()
            return True
        return False

    def toggle_row(self, row: int) -> None:
        """Toggle checkbox state for a source model row."""
        if not (0 <= row < len(self._torrents)):
            return
        if row in self._checked_rows:
            self._checked_rows.discard(row)
        else:
            self._checked_rows.add(row)
        idx = self.index(row, 0)
        self.dataChanged.emit(idx, idx, [Qt.ItemDataRole.CheckStateRole])
        self.selection_toggled.emit()

    def set_rows_checked(self, rows: list[int], checked: bool) -> None:
        """Bulk check or uncheck source row indices."""
        changed = False
        for row in rows:
            if 0 <= row < len(self._torrents):
                if checked and row not in self._checked_rows:
                    self._checked_rows.add(row)
                    changed = True
                elif not checked and row in self._checked_rows:
                    self._checked_rows.discard(row)
                    changed = True
        if changed and self._torrents:
            self.dataChanged.emit(
                self.index(0, 0),
                self.index(len(self._torrents) - 1, 0),
                [Qt.ItemDataRole.CheckStateRole],
            )
            self.selection_toggled.emit()

    def torrent_at(self, row: int) -> Torrent | None:
        """Return Torrent at given source row index."""
        if 0 <= row < len(self._torrents):
            return self._torrents[row]
        return None

    def checked_torrents(self) -> list[Torrent]:
        """Return checked torrents in model order."""
        return [self._torrents[r] for r in sorted(self._checked_rows) if r < len(self._torrents)]


class TorrentFilterProxyModel(QSortFilterProxyModel):
    """Client-side filter proxy matching text substring and quality tag."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._text_filter = ""
        self._quality_filter = "All"
        self.setSortRole(SORT_ROLE)

    def _apply_filter_change(self, mutator: Callable[[], None]) -> None:
        if hasattr(self, "beginFilterChange") and hasattr(self, "endFilterChange"):
            self.beginFilterChange()
            mutator()
            self.endFilterChange(QSortFilterProxyModel.Direction.Rows)
        else:  # pragma: no cover - PySide6 < 6.10 compatibility
            mutator()
            self.invalidateFilter()

    def set_text_filter(self, text: str) -> None:
        clean = text.strip().lower()
        self._apply_filter_change(lambda: setattr(self, "_text_filter", clean))

    def set_quality_filter(self, quality: str) -> None:
        clean = quality or "All"
        self._apply_filter_change(lambda: setattr(self, "_quality_filter", clean))

    def filterAcceptsRow(
        self,
        source_row: int,
        source_parent: QModelIndex | QPersistentModelIndex,
    ) -> bool:
        model = self.sourceModel()
        if not isinstance(model, TorrentTableModel):
            return True
        torrent = model.torrent_at(source_row)
        if torrent is None:
            return False

        if self._quality_filter != "All":
            if self._quality_filter.lower() not in torrent.quality.lower():
                return False

        if self._text_filter:
            haystack = (
                f"{torrent.name} {torrent.username} {torrent.codec} {torrent.quality}".lower()
            )
            if self._text_filter not in haystack:
                return False

        return True


class _CheckableTableView(QTableView):
    """QTableView supporting Space key to toggle row selection checkboxes."""

    space_pressed = Signal()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Space:
            self.space_pressed.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class TorrentResultsView(QWidget):
    """Composite view providing live filtering, bulk selection buttons, and sortable QTableView."""

    selection_changed = Signal(list)
    torrent_focused = Signal(object)

    def __init__(self, theme_name: str = "dark", parent: QWidget | None = None):
        super().__init__(parent)
        self.model = TorrentTableModel(theme_name=theme_name, parent=self)
        self.proxy = TorrentFilterProxyModel(self)
        self.proxy.setSourceModel(self.model)

        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        controls = QHBoxLayout()
        controls.setSpacing(8)

        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter results by title, codec, or uploader...")
        self.filter_input.setAccessibleName("Filter displayed releases")
        self.filter_input.setClearButtonEnabled(True)

        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["All", "2160p", "1080p", "720p", "480p"])
        self.quality_combo.setToolTip("Filter displayed releases by resolution")
        self.quality_combo.setAccessibleName("Filter by resolution")

        self.select_all_btn = QPushButton("Select Visible")
        self.select_all_btn.setAccessibleName("Select all visible releases")
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setAccessibleName("Clear selected releases")
        self.count_label = QLabel("0 releases")
        self.count_label.setObjectName("MutedLabel")

        controls.addWidget(self.filter_input, stretch=3)
        controls.addWidget(QLabel("Quality:"))
        controls.addWidget(self.quality_combo)
        controls.addWidget(self.select_all_btn)
        controls.addWidget(self.clear_btn)
        controls.addWidget(self.count_label)
        layout.addLayout(controls)

        self.table = _CheckableTableView()
        self.table.setAccessibleName("Search results table")
        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(True)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for col in (2, 3, 4, 5, 6, 8):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(7, 130)

        layout.addWidget(self.table, stretch=1)

    def _connect_signals(self) -> None:
        self.filter_input.textChanged.connect(self._on_filter_changed)
        self.quality_combo.currentTextChanged.connect(self._on_quality_changed)
        self.select_all_btn.clicked.connect(self.select_visible)
        self.clear_btn.clicked.connect(self.clear_selection)
        self.model.selection_toggled.connect(self._emit_selection)
        self.table.space_pressed.connect(self._toggle_current_row)
        self.table.clicked.connect(self._on_table_clicked)
        if self.table.selectionModel() is not None:
            self.table.selectionModel().currentRowChanged.connect(self._on_current_row_changed)

    def set_theme(self, theme_name: str) -> None:
        """Apply theme palette updates to table cells."""
        self.model.set_theme(theme_name)

    def set_torrents(
        self,
        torrents: list[Torrent],
        preferred_quality: str = "All",
        precheck_first: bool = False,
    ) -> None:
        """Populate table with torrent results and apply optional initial quality filter."""
        self.model.set_torrents(torrents, precheck_first=precheck_first)
        if preferred_quality in ("2160p", "1080p", "720p", "480p"):
            # Only pre-filter if matching releases actually exist; otherwise show all.
            has_match = any(preferred_quality.lower() in t.quality.lower() for t in torrents)
            self.quality_combo.setCurrentText(preferred_quality if has_match else "All")
        else:
            self.quality_combo.setCurrentText("All")
        self.table.sortByColumn(5, Qt.SortOrder.DescendingOrder)
        self._update_count_label()
        if self.proxy.rowCount() > 0:
            self.table.selectRow(0)

    def checked_torrents(self) -> list[Torrent]:
        """Return currently checked Torrent items."""
        return self.model.checked_torrents()

    def select_visible(self) -> None:
        """Check all currently filtered/visible rows."""
        visible_rows = [
            self.proxy.mapToSource(self.proxy.index(r, 0)).row()
            for r in range(self.proxy.rowCount())
        ]
        self.model.set_rows_checked(visible_rows, True)

    def clear_selection(self) -> None:
        """Uncheck all rows."""
        all_rows = list(range(self.model.rowCount()))
        self.model.set_rows_checked(all_rows, False)

    def _on_filter_changed(self, text: str) -> None:
        self.proxy.set_text_filter(text)
        self._update_count_label()

    def _on_quality_changed(self, quality: str) -> None:
        self.proxy.set_quality_filter(quality)
        self._update_count_label()

    def _update_count_label(self) -> None:
        shown = self.proxy.rowCount()
        total = self.model.rowCount()
        if shown == total:
            self.count_label.setText(f"{total} release{'s' if total != 1 else ''}")
        else:
            self.count_label.setText(f"{shown} of {total} releases")

    def _emit_selection(self) -> None:
        self.selection_changed.emit(self.checked_torrents())

    def _on_table_clicked(self, proxy_index: QModelIndex) -> None:
        if not proxy_index.isValid():
            return
        src_index = self.proxy.mapToSource(proxy_index)
        torrent = self.model.torrent_at(src_index.row())
        if torrent is not None:
            self.torrent_focused.emit(torrent)

    def _toggle_current_row(self) -> None:
        current = self.table.currentIndex()
        if not current.isValid():
            return
        src_index = self.proxy.mapToSource(current)
        self.model.toggle_row(src_index.row())

    def _on_current_row_changed(self, current: QModelIndex, _previous: QModelIndex) -> None:
        if not current.isValid():
            return
        src_index = self.proxy.mapToSource(current)
        torrent = self.model.torrent_at(src_index.row())
        if torrent is not None:
            self.torrent_focused.emit(torrent)
