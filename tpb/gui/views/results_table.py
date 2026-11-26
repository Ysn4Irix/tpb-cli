"""Sortable, filterable results table view for Movies, General search, and Season Packs."""

from typing import Any, List, Optional, Set
from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QSortFilterProxyModel,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QFont
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

SORT_ROLE = Qt.UserRole + 1

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

    def __init__(self, theme_name: str = "dark", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._torrents: List[Torrent] = []
        self._checked_rows: Set[int] = set()
        self._palette: ThemePalette = get_palette(theme_name)

    def set_theme(self, theme_name: str) -> None:
        """Update palette colors and notify views to repaint."""
        self._palette = get_palette(theme_name)
        if self._torrents:
            top_left = self.index(0, 0)
            bottom_right = self.index(len(self._torrents) - 1, len(COLUMNS) - 1)
            self.dataChanged.emit(top_left, bottom_right, [Qt.ForegroundRole])

    def set_torrents(self, torrents: List[Torrent], precheck_first: bool = False) -> None:
        """Replace displayed torrents and reset checkbox selections."""
        self.beginResetModel()
        self._torrents = list(torrents)
        self._checked_rows = {0} if (precheck_first and self._torrents) else set()
        self.endResetModel()
        self.selection_toggled.emit()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._torrents)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(COLUMNS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return COLUMNS[section]
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.NoItemFlags
        base = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if index.column() == 0:
            return base | Qt.ItemIsUserCheckable
        return base

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._torrents)):
            return None

        row = index.row()
        col = index.column()
        t = self._torrents[row]

        if col == 0:
            if role == Qt.CheckStateRole:
                return Qt.Checked if row in self._checked_rows else Qt.Unchecked
            if role == SORT_ROLE:
                return 1 if row in self._checked_rows else 0
            return None

        if role == Qt.DisplayRole:
            return self._display_value(t, col)

        if role == SORT_ROLE:
            return self._sort_value(t, col)

        if role == Qt.ToolTipRole and col == 1:
            return f"{t.name}\nUploader: {t.username or 'Anonymous'} | InfoHash: {t.info_hash}"

        if role == Qt.TextAlignmentRole:
            if col in (4, 5, 6):
                return int(Qt.AlignRight | Qt.AlignVCenter)
            if col in (2, 3, 8):
                return int(Qt.AlignCenter)

        if role == Qt.ForegroundRole:
            return self._foreground_color(t, col)

        if role == Qt.FontRole and col == 5 and t.seeders > 50:
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

    def _foreground_color(self, t: Torrent, col: int) -> Optional[QColor]:
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

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.EditRole) -> bool:
        if index.isValid() and index.column() == 0 and role == Qt.CheckStateRole:
            row = index.row()
            checked = value == Qt.Checked or value == Qt.Checked.value
            if checked:
                self._checked_rows.add(row)
            else:
                self._checked_rows.discard(row)
            self.dataChanged.emit(index, index, [Qt.CheckStateRole])
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
        self.dataChanged.emit(idx, idx, [Qt.CheckStateRole])
        self.selection_toggled.emit()

    def set_rows_checked(self, rows: List[int], checked: bool) -> None:
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
                [Qt.CheckStateRole],
            )
            self.selection_toggled.emit()

    def torrent_at(self, row: int) -> Optional[Torrent]:
        """Return Torrent at given source row index."""
        if 0 <= row < len(self._torrents):
            return self._torrents[row]
        return None

    def checked_torrents(self) -> List[Torrent]:
        """Return checked torrents in model order."""
        return [self._torrents[r] for r in sorted(self._checked_rows) if r < len(self._torrents)]


class TorrentFilterProxyModel(QSortFilterProxyModel):
    """Client-side filter proxy matching text substring and quality tag."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._text_filter = ""
        self._quality_filter = "All"
        self.setSortRole(SORT_ROLE)

    def _apply_filter_change(self, mutator) -> None:
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

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
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
            haystack = f"{torrent.name} {torrent.username} {torrent.codec} {torrent.quality}".lower()
            if self._text_filter not in haystack:
                return False

        return True


class TorrentResultsView(QWidget):
    """Composite view providing live filtering, bulk selection buttons, and sortable QTableView."""

    selection_changed = Signal(list)
    torrent_focused = Signal(object)

    def __init__(self, theme_name: str = "dark", parent: Optional[QWidget] = None):
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
        self.filter_input.setClearButtonEnabled(True)

        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["All", "2160p", "1080p", "720p", "480p"])
        self.quality_combo.setToolTip("Filter displayed releases by resolution")

        self.select_all_btn = QPushButton("Select Visible")
        self.clear_btn = QPushButton("Clear")
        self.count_label = QLabel("0 releases")
        self.count_label.setObjectName("MutedLabel")

        controls.addWidget(self.filter_input, stretch=3)
        controls.addWidget(QLabel("Quality:"))
        controls.addWidget(self.quality_combo)
        controls.addWidget(self.select_all_btn)
        controls.addWidget(self.clear_btn)
        controls.addWidget(self.count_label)
        layout.addLayout(controls)

        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(True)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        for col in (2, 3, 4, 5, 6, 8):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.Interactive)
        self.table.setColumnWidth(7, 130)

        layout.addWidget(self.table, stretch=1)

    def _connect_signals(self) -> None:
        self.filter_input.textChanged.connect(self._on_filter_changed)
        self.quality_combo.currentTextChanged.connect(self._on_quality_changed)
        self.select_all_btn.clicked.connect(self.select_visible)
        self.clear_btn.clicked.connect(self.clear_selection)
        self.model.selection_toggled.connect(self._emit_selection)
        self.table.clicked.connect(self._on_table_clicked)
        if self.table.selectionModel() is not None:
            self.table.selectionModel().currentRowChanged.connect(self._on_current_row_changed)

    def set_theme(self, theme_name: str) -> None:
        """Apply theme palette updates to table cells."""
        self.model.set_theme(theme_name)

    def set_torrents(
        self,
        torrents: List[Torrent],
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
        self.table.sortByColumn(5, Qt.DescendingOrder)
        self._update_count_label()
        if self.proxy.rowCount() > 0:
            self.table.selectRow(0)

    def checked_torrents(self) -> List[Torrent]:
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

    def _on_current_row_changed(self, current: QModelIndex, _previous: QModelIndex) -> None:
        if not current.isValid():
            return
        src_index = self.proxy.mapToSource(current)
        torrent = self.model.torrent_at(src_index.row())
        if torrent is not None:
            self.torrent_focused.emit(torrent)
