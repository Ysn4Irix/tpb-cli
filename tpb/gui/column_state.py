"""Shared persistent interactive header column state controller for Qt tables and trees."""

from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QHeaderView

from tpb.gui.state import AppStateStore


class PersistentHeaderController(QObject):
    """Configures interactive header columns and persists user-resized widths."""

    def __init__(
        self,
        header: QHeaderView,
        state_store: AppStateStore | None,
        state_key: str,
        default_widths: list[int],
        fixed_sections: set[int] | None = None,
        stretch_last_section: bool = False,
        minimum_section_size: int = 44,
        save_delay_ms: int = 150,
    ):
        super().__init__(header)
        self._header = header
        self._state_store = state_store
        self._state_key = state_key
        self._default_widths = list(default_widths)
        self._fixed_sections = set(fixed_sections or ())
        self._restoring = False

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(save_delay_ms)
        self._save_timer.timeout.connect(self.flush)

        self._configure_and_restore(stretch_last_section, minimum_section_size)
        self._header.sectionResized.connect(self._on_section_resized)

    def _configure_and_restore(
        self,
        stretch_last_section: bool,
        minimum_section_size: int,
    ) -> None:
        self._restoring = True
        try:
            self._header.setStretchLastSection(stretch_last_section)
            self._header.setMinimumSectionSize(minimum_section_size)
            col_count = self._header.count()

            for col in range(col_count):
                mode = (
                    QHeaderView.ResizeMode.Fixed
                    if col in self._fixed_sections
                    else QHeaderView.ResizeMode.Interactive
                )
                self._header.setSectionResizeMode(col, mode)

            saved = (
                self._state_store.get_column_widths(self._state_key)
                if self._state_store is not None
                else []
            )
            widths = saved if len(saved) == col_count else self._default_widths
            for col, width in enumerate(widths[:col_count]):
                if width > 0:
                    self._header.resizeSection(col, width)
        finally:
            self._restoring = False

    def _on_section_resized(
        self,
        _logical_index: int,
        _old_size: int,
        _new_size: int,
    ) -> None:
        if self._restoring or self._state_store is None:
            return
        widths = [self._header.sectionSize(col) for col in range(self._header.count())]
        self._state_store.set_column_widths(self._state_key, widths, persist=False)
        self._save_timer.start()

    def flush(self) -> None:
        """Persist any queued column width updates immediately."""
        if self._save_timer.isActive():
            self._save_timer.stop()
        if self._state_store is not None:
            self._state_store.save()
