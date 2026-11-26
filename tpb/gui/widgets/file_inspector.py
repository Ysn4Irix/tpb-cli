"""Side/bottom drawer displaying internal files for a focused torrent."""

from typing import List, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from tpb.models import Torrent, TorrentFile


class FileInspectorDrawer(QFrame):
    """Collapsible inspector showing file names and sizes from ApibayClient.get_parsed_files."""

    retry_requested = Signal(str)
    close_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("PanelSurface")
        self._current_torrent: Optional[Torrent] = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Header row
        header = QHBoxLayout()
        title_label = QLabel("File Inspector")
        bold = QFont()
        bold.setBold(True)
        title_label.setFont(bold)

        self.retry_btn = QPushButton("Retry")
        self.retry_btn.setVisible(False)
        self.close_btn = QPushButton("Hide")

        header.addWidget(title_label)
        header.addStretch(1)
        header.addWidget(self.retry_btn)
        header.addWidget(self.close_btn)
        layout.addLayout(header)

        self.torrent_title_label = QLabel("Select a release to inspect files.")
        self.torrent_title_label.setWordWrap(True)
        layout.addWidget(self.torrent_title_label)

        self.meta_label = QLabel("")
        self.meta_label.setObjectName("MutedLabel")
        self.meta_label.setWordWrap(True)
        layout.addWidget(self.meta_label)

        self.status_label = QLabel("")
        self.status_label.setObjectName("MutedLabel")
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)

        self.files_tree = QTreeWidget()
        self.files_tree.setColumnCount(2)
        self.files_tree.setHeaderLabels(["File Path", "Size"])
        self.files_tree.setRootIsDecorated(False)
        self.files_tree.setAlternatingRowColors(True)
        tree_header = self.files_tree.header()
        tree_header.setSectionResizeMode(0, QHeaderView.Stretch)
        tree_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        layout.addWidget(self.files_tree, stretch=1)

        self.retry_btn.clicked.connect(self._on_retry_clicked)
        self.close_btn.clicked.connect(self.close_requested.emit)

    def clear(self) -> None:
        """Reset inspector back to idle placeholder state."""
        self._current_torrent = None
        self.torrent_title_label.setText("Select a release to inspect files.")
        self.meta_label.setText("")
        self.status_label.setVisible(False)
        self.retry_btn.setVisible(False)
        self.files_tree.clear()

    def show_loading(self, torrent: Torrent) -> None:
        """Display torrent metadata header and loading state."""
        self._current_torrent = torrent
        self.torrent_title_label.setText(torrent.name)
        codec_str = f" | {torrent.codec}" if torrent.codec != "Unknown" else ""
        self.meta_label.setText(
            f"{torrent.quality}{codec_str} · {torrent.human_size} · "
            f"{torrent.seeders} seeds · Uploader: {torrent.username or 'Anonymous'}"
        )
        self.status_label.setText("Loading file list from Apibay...")
        self.status_label.setVisible(True)
        self.retry_btn.setVisible(False)
        self.files_tree.clear()

    def show_files(self, torrent_id: str, files: List[TorrentFile]) -> None:
        """Render normalized TorrentFile rows if they correspond to the focused torrent."""
        if self._current_torrent is None or str(self._current_torrent.id) != str(torrent_id):
            return

        self.files_tree.clear()
        self.retry_btn.setVisible(False)

        if not files:
            self.status_label.setText("No individual file listing available for this torrent.")
            self.status_label.setVisible(True)
            return

        self.status_label.setText(f"{len(files)} file{'s' if len(files) != 1 else ''} in torrent")
        self.status_label.setVisible(True)

        for entry in files:
            item = QTreeWidgetItem([entry.name, entry.human_size])
            item.setTextAlignment(1, Qt.AlignRight | Qt.AlignVCenter)
            item.setToolTip(0, entry.name)
            self.files_tree.addTopLevelItem(item)

    def show_error(self, torrent_id: str, message: str) -> None:
        """Display file-fetch failure message with retry option."""
        if self._current_torrent is None or str(self._current_torrent.id) != str(torrent_id):
            return
        self.files_tree.clear()
        self.status_label.setText(f"Error loading files: {message}")
        self.status_label.setVisible(True)
        self.retry_btn.setVisible(True)

    @property
    def current_torrent_id(self) -> Optional[str]:
        """Return currently inspected torrent ID if any."""
        return str(self._current_torrent.id) if self._current_torrent is not None else None

    def _on_retry_clicked(self) -> None:
        if self._current_torrent is not None and self._current_torrent.id:
            self.show_loading(self._current_torrent)
            self.retry_requested.emit(str(self._current_torrent.id))
