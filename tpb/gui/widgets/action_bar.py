"""Bottom magnet handoff & batch export action bar."""

from pathlib import Path
from collections.abc import Callable
from PySide6.QtCore import QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QWidget,
)

from tpb.exporter import export_magnets_to_file
from tpb.gui.state import AppStateStore
from tpb.models import Torrent, format_bytes

BATCH_OPEN_CONFIRM_THRESHOLD = 5
BATCH_OPEN_INTERVAL_MS = 150


class ActionBar(QFrame):
    """Action toolbar for copying, launching OS magnet URIs, and exporting .txt files."""

    status_message = Signal(str)

    def __init__(
        self,
        state_store: AppStateStore,
        url_opener: Callable[[str], bool] | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setObjectName("ActionBar")
        self.state_store = state_store
        self._url_opener = url_opener or (lambda uri: QDesktopServices.openUrl(QUrl(uri)))
        self._selected: list[Torrent] = []
        self._default_filename: str = "torrents_magnets.txt"
        self._pending_open_queue: list[str] = []

        self._open_timer = QTimer(self)
        self._open_timer.setInterval(BATCH_OPEN_INTERVAL_MS)
        self._open_timer.timeout.connect(self._dispatch_next_magnet)

        self._build_ui()
        self._connect_signals()
        self._refresh_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        self.summary_label = QLabel("0 releases selected")
        layout.addWidget(self.summary_label)
        layout.addStretch(1)

        self.copy_btn = QPushButton("Copy Magnet(s)")
        self.copy_btn.setAccessibleName("Copy selected magnet links")
        self.open_btn = QPushButton("Open in Client")
        self.open_btn.setAccessibleName("Open selected magnets in torrent client")
        self.export_btn = QPushButton("Export .txt...")
        self.export_btn.setObjectName("PrimaryButton")
        self.export_btn.setAccessibleName("Export selected magnet links to file")

        layout.addWidget(self.copy_btn)
        layout.addWidget(self.open_btn)
        layout.addWidget(self.export_btn)

    def _connect_signals(self) -> None:
        self.copy_btn.clicked.connect(self.copy_selected_magnets)
        self.open_btn.clicked.connect(self.open_selected_magnets)
        self.export_btn.clicked.connect(self.export_selected_to_file_dialog)

    def set_selected_torrents(self, torrents: list[Torrent]) -> None:
        """Update current selection list and action button availability."""
        self._selected = list(torrents)
        self._refresh_ui()

    def set_default_filename(self, filename: str) -> None:
        """Update suggested export filename for the active search/season."""
        clean = filename.strip()
        if clean:
            self._default_filename = clean

    def _refresh_ui(self) -> None:
        count = len(self._selected)
        total_size = sum(max(0, t.size_bytes) for t in self._selected)
        has_valid_magnets = any(bool(t.magnet_link) for t in self._selected)

        if count == 0:
            self.summary_label.setText("0 releases selected")
        else:
            self.summary_label.setText(
                f"{count} release{'s' if count != 1 else ''} selected · {format_bytes(total_size)} total"
            )

        self.copy_btn.setEnabled(has_valid_magnets)
        self.open_btn.setEnabled(has_valid_magnets)
        self.export_btn.setEnabled(has_valid_magnets)

    def _valid_magnets(self) -> list[str]:
        return [t.magnet_link for t in self._selected if t.magnet_link]

    def copy_selected_magnets(self) -> int:
        """Copy selected magnet URIs to system clipboard; returns number copied."""
        magnets = self._valid_magnets()
        if not magnets:
            self.status_message.emit("No valid magnet links selected.")
            return 0

        QGuiApplication.clipboard().setText("\n".join(magnets))
        self.status_message.emit(
            f"Copied {len(magnets)} magnet link{'s' if len(magnets) != 1 else ''} to clipboard."
        )
        return len(magnets)

    def open_selected_magnets(self, confirm_batch: Callable[[int], bool] | None = None) -> int:
        """
        Launch selected magnet links in the OS torrent client.
        Prompts confirmation for batches above BATCH_OPEN_CONFIRM_THRESHOLD and throttles URIs.
        """
        magnets = self._valid_magnets()
        if not magnets:
            self.status_message.emit("No valid magnet links selected.")
            return 0

        if len(magnets) > BATCH_OPEN_CONFIRM_THRESHOLD:
            if confirm_batch is not None:
                proceed = confirm_batch(len(magnets))
            else:
                proceed = self._confirm_large_batch(len(magnets))
            if not proceed:
                self.status_message.emit("Batch client launch cancelled.")
                return 0

        if len(magnets) == 1:
            self._url_opener(magnets[0])
            self.status_message.emit("Opened magnet link in default torrent client.")
            return 1

        self._pending_open_queue.extend(magnets)
        # Dispatch first link right away, then stagger remaining links to protect OS handler.
        self._dispatch_next_magnet()
        if self._pending_open_queue and not self._open_timer.isActive():
            self._open_timer.start()
        self.status_message.emit(
            f"Opening {len(magnets)} magnet links in torrent client (staggered)..."
        )
        return len(magnets)

    def _confirm_large_batch(self, count: int) -> bool:
        reply = QMessageBox.question(
            self,
            "Open Multiple Magnets?",
            (
                f"You selected {count} magnet links.\n\n"
                "Opening many magnet URIs simultaneously may trigger multiple client prompts "
                "or drop links depending on your torrent client.\n\n"
                "Tip: Copy Magnet(s) or Export .txt is instant for large seasons.\n"
                "Continue opening all links one by one?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

    def _dispatch_next_magnet(self) -> None:
        if not self._pending_open_queue:
            self._open_timer.stop()
            return
        uri = self._pending_open_queue.pop(0)
        self._url_opener(uri)
        if not self._pending_open_queue:
            self._open_timer.stop()
            self.status_message.emit("Finished dispatching magnet links to client.")

    def export_selected_to_file_dialog(self) -> Path | None:
        """Prompt user for a destination .txt path and export selected magnet links."""
        if not self._valid_magnets():
            return None

        start_dir = Path(self.state_store.settings.last_export_dir)
        suggested_path = str(start_dir / self._default_filename)

        chosen_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Magnet Links",
            suggested_path,
            "Text Files (*.txt);;All Files (*)",
            options=QFileDialog.Option.DontConfirmOverwrite,
        )
        if not chosen_path:
            return None

        dest_path = Path(chosen_path)
        return self.export_torrents_to_path(dest_path)

    def export_torrents_to_path(
        self,
        dest_path: Path,
        collision_resolver: Callable[[Path], str] | None = None,
    ) -> Path | None:
        """
        Write selected magnets to dest_path with Overwrite / Append / Cancel collision resolution.
        Returns destination Path when written, or None if cancelled.
        """
        if not self._valid_magnets():
            return None

        append_mode = False
        if dest_path.exists():
            if collision_resolver is not None:
                choice = collision_resolver(dest_path)
            else:
                choice = self._ask_file_collision(dest_path)
            if choice == "cancel":
                self.status_message.emit("File export cancelled.")
                return None
            append_mode = choice == "append"

        valid_torrents = [t for t in self._selected if t.magnet_link]
        count = export_magnets_to_file(valid_torrents, dest_path, append=append_mode)
        self.state_store.settings.last_export_dir = str(dest_path.parent)
        self.state_store.save()

        action_word = "Appended" if append_mode else "Exported"
        self.status_message.emit(f"{action_word} {count} magnet link(s) to '{dest_path}'.")
        return dest_path

    def _ask_file_collision(self, dest_path: Path) -> str:
        box = QMessageBox(self)
        box.setWindowTitle("File Already Exists")
        box.setText(f"'{dest_path.name}' already exists.\nWhat would you like to do?")
        overwrite_btn = box.addButton("Overwrite", QMessageBox.ButtonRole.AcceptRole)
        append_btn = box.addButton("Append", QMessageBox.ButtonRole.ActionRole)
        cancel_btn = box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(overwrite_btn)
        box.exec()

        clicked = box.clickedButton()
        if clicked == overwrite_btn:
            return "overwrite"
        if clicked == append_btn:
            return "append"
        if clicked == cancel_btn:
            return "cancel"
        return "cancel"
