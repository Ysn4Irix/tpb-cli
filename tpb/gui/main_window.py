"""Main application window coordinating search modes, results views, drawers, and actions."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from tpb import __version__
from tpb.api import ApibayClient
from tpb.gui.assets import load_app_icon
from tpb.gui.state import AppStateStore
from tpb.gui.theme import build_stylesheet
from tpb.gui.views.results_table import TorrentResultsView
from tpb.gui.views.tv_browser import TvBrowserView
from tpb.gui.widgets.action_bar import ActionBar
from tpb.gui.widgets.file_inspector import FileInspectorDrawer
from tpb.gui.widgets.library_drawer import LibraryDrawer
from tpb.gui.widgets.settings_dialog import SettingsDialog
from tpb.gui.workers import WorkerManager
from tpb.models import Torrent, sanitize_filename


class MainWindow(QMainWindow):
    """Desktop GUI shell for searching movies, TV series, and inspecting/exporting magnets."""

    def __init__(
        self,
        client: ApibayClient | None = None,
        state_store: AppStateStore | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.state_store = state_store or AppStateStore()
        self.client = client or self._build_client_from_settings()
        self.workers = WorkerManager(self.client)
        self._current_mode = "tv"
        self._last_query = ""
        self._previous_center_index = 0
        self._search_elapsed_ms = 0

        self._loading_timer = QTimer(self)
        self._loading_timer.setInterval(200)
        self._loading_timer.timeout.connect(self._update_loading_elapsed)

        self.setWindowTitle(f"tpb-cli v{__version__} — Magnet Search & Batch Export")
        app_icon = load_app_icon()
        if not app_icon.isNull():
            self.setWindowIcon(app_icon)
        self.resize(1460, 780)
        self.setMinimumSize(1080, 620)

        self._build_ui()
        self._connect_signals()
        self._setup_shortcuts()
        self.apply_theme(self.state_store.settings.theme)
        self._refresh_mode_ui()

    def _build_client_from_settings(self) -> ApibayClient:
        s = self.state_store.settings
        return ApibayClient(base_url=s.api_url, proxy=s.proxy or None)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        # Header Search & Controls Bar
        header_frame = QFrame()
        header_frame.setObjectName("HeaderBar")
        header = QHBoxLayout(header_frame)
        header.setContentsMargins(10, 8, 10, 8)
        header.setSpacing(8)

        self.tv_btn = QPushButton("TV Series")
        self.tv_btn.setCheckable(True)
        self.tv_btn.setChecked(True)
        self.movie_btn = QPushButton("Movies")
        self.movie_btn.setCheckable(True)
        self.general_btn = QPushButton("General")
        self.general_btn.setCheckable(True)

        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        self.mode_group.addButton(self.tv_btn)
        self.mode_group.addButton(self.movie_btn)
        self.mode_group.addButton(self.general_btn)

        self.search_input = QLineEdit()
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setAccessibleName("Search query")

        self.bookmark_btn = QPushButton("☆ Bookmark")
        self.bookmark_btn.setToolTip("Bookmark current search query")
        self.bookmark_btn.setAccessibleName("Bookmark query")

        self.search_btn = QPushButton("Search")
        self.search_btn.setObjectName("PrimaryButton")
        self.search_btn.setAccessibleName("Run search")

        self.library_toggle_btn = QPushButton("Library")
        self.library_toggle_btn.setCheckable(True)
        self.library_toggle_btn.setAccessibleName("Toggle history and bookmarks drawer")
        self.inspector_toggle_btn = QPushButton("Files")
        self.inspector_toggle_btn.setCheckable(True)
        self.inspector_toggle_btn.setChecked(True)
        self.inspector_toggle_btn.setAccessibleName("Toggle torrent file inspector")
        self.theme_toggle_btn = QPushButton("Light Mode")
        self.theme_toggle_btn.setAccessibleName("Toggle color theme")
        self.settings_btn = QPushButton("Settings")
        self.settings_btn.setAccessibleName("Open settings")

        header.addWidget(self.tv_btn)
        header.addWidget(self.movie_btn)
        header.addWidget(self.general_btn)
        header.addSpacing(6)
        header.addWidget(self.search_input, stretch=1)
        header.addWidget(self.bookmark_btn)
        header.addWidget(self.search_btn)
        header.addSpacing(6)
        header.addWidget(self.library_toggle_btn)
        header.addWidget(self.inspector_toggle_btn)
        header.addWidget(self.theme_toggle_btn)
        header.addWidget(self.settings_btn)

        root.addWidget(header_frame)

        # Workspace Splitter: [Library Drawer] | [Main Workspace] | [File Inspector]
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)

        self.library_drawer = LibraryDrawer(self.state_store)
        self.library_drawer.setVisible(False)
        self.library_drawer.setMinimumWidth(220)

        self.center_stack = QStackedWidget()
        self.welcome_panel = self._build_welcome_panel()
        self.tv_view = TvBrowserView(theme_name=self.state_store.settings.theme)
        self.table_view = TorrentResultsView(theme_name=self.state_store.settings.theme)
        self.loading_panel = self._build_loading_panel()

        self.center_stack.addWidget(self.welcome_panel)  # 0
        self.center_stack.addWidget(self.tv_view)  # 1
        self.center_stack.addWidget(self.table_view)  # 2
        self.center_stack.addWidget(self.loading_panel)  # 3

        self.file_inspector = FileInspectorDrawer()
        self.file_inspector.setMinimumWidth(280)

        self.main_splitter.addWidget(self.library_drawer)
        self.main_splitter.addWidget(self.center_stack)
        self.main_splitter.addWidget(self.file_inspector)
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)
        self.main_splitter.setStretchFactor(2, 0)
        self.main_splitter.setSizes([240, 900, 320])

        root.addWidget(self.main_splitter, stretch=1)

        # Bottom Action Bar
        self.action_bar = ActionBar(self.state_store)
        root.addWidget(self.action_bar)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_progress = QProgressBar()
        self.status_progress.setRange(0, 0)
        self.status_progress.setFixedSize(120, 12)
        self.status_progress.setTextVisible(False)
        self.status_progress.setAccessibleName("Search activity indicator")
        self.status_progress.setVisible(False)
        self.endpoint_label = QLabel(f"API: {self.client.base_url}")
        self.status_bar.addPermanentWidget(self.status_progress)
        self.status_bar.addPermanentWidget(self.endpoint_label)
        self.status_bar.showMessage("Ready. Enter a title to search Apibay.")

    def _build_welcome_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("PanelSurface")
        layout = QVBoxLayout(panel)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)

        title = QLabel("TPB / Apibay Desktop")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel(
            "Select TV Series, Movies, or General above, enter a title, and hit Enter.\n"
            "• TV Series auto-detects regional versions, seasons, full packs, and multi-quality episodes.\n"
            "• Click any release row to inspect internal files or batch export magnet links."
        )
        subtitle.setObjectName("MutedLabel")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.empty_message_label = QLabel("")
        self.empty_message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_message_label.setWordWrap(True)
        self.empty_message_label.setVisible(False)

        self.retry_search_btn = QPushButton("Retry Search")
        self.retry_search_btn.setObjectName("PrimaryButton")
        self.retry_search_btn.setAccessibleName("Retry search")
        self.retry_search_btn.setVisible(False)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.empty_message_label)
        layout.addWidget(self.retry_search_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        return panel

    def _build_loading_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("PanelSurface")
        layout = QVBoxLayout(panel)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)

        self.loading_title_label = QLabel("Searching Apibay...")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        self.loading_title_label.setFont(title_font)
        self.loading_title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.loading_detail_label = QLabel("")
        self.loading_detail_label.setObjectName("MutedLabel")
        self.loading_detail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.loading_progress_bar = QProgressBar()
        self.loading_progress_bar.setRange(0, 0)
        self.loading_progress_bar.setFixedWidth(340)
        self.loading_progress_bar.setFixedHeight(10)
        self.loading_progress_bar.setTextVisible(False)

        self.loading_elapsed_label = QLabel("Connecting... (0.0s)")
        self.loading_elapsed_label.setObjectName("MutedLabel")
        self.loading_elapsed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.cancel_search_btn = QPushButton("Cancel Search")
        self.cancel_search_btn.setAccessibleName("Cancel active search")

        layout.addWidget(self.loading_title_label)
        layout.addWidget(self.loading_detail_label)
        layout.addWidget(self.loading_progress_bar, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.loading_elapsed_label)
        layout.addWidget(self.cancel_search_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        return panel

    def _connect_signals(self) -> None:
        self.tv_btn.clicked.connect(lambda: self._set_mode("tv"))
        self.movie_btn.clicked.connect(lambda: self._set_mode("movie"))
        self.general_btn.clicked.connect(lambda: self._set_mode("general"))

        self.search_input.returnPressed.connect(self.trigger_search)
        self.search_input.textChanged.connect(lambda _t: self._update_bookmark_button())
        self.search_btn.clicked.connect(self.trigger_search)
        self.bookmark_btn.clicked.connect(self._toggle_current_bookmark)

        self.library_toggle_btn.toggled.connect(self.library_drawer.setVisible)
        self.library_drawer.close_requested.connect(
            lambda: self.library_toggle_btn.setChecked(False)
        )
        self.library_drawer.search_requested.connect(self.run_query)
        self.library_drawer.bookmarks_changed.connect(self._update_bookmark_button)

        self.inspector_toggle_btn.toggled.connect(self.file_inspector.setVisible)
        self.file_inspector.close_requested.connect(
            lambda: self.inspector_toggle_btn.setChecked(False)
        )
        self.file_inspector.retry_requested.connect(self.workers.start_files_lookup)

        self.theme_toggle_btn.clicked.connect(self.toggle_theme)
        self.settings_btn.clicked.connect(self.open_settings_dialog)

        # Workers
        self.workers.search_started.connect(self._on_search_started)
        self.workers.search_completed.connect(self._on_search_completed)
        self.workers.search_failed.connect(self._on_search_failed)
        self.workers.search_cancelled.connect(self._on_search_cancelled)
        self.workers.files_completed.connect(self.file_inspector.show_files)
        self.workers.files_failed.connect(self.file_inspector.show_error)

        self.cancel_search_btn.clicked.connect(self.workers.cancel_search)
        self.retry_search_btn.clicked.connect(self.trigger_search)

        # Views -> Selection & File Inspection
        self.tv_view.selection_changed.connect(self.action_bar.set_selected_torrents)
        self.tv_view.torrent_focused.connect(self._on_torrent_focused)
        self.tv_view.export_hint_changed.connect(self.action_bar.set_default_filename)

        self.table_view.selection_changed.connect(self.action_bar.set_selected_torrents)
        self.table_view.torrent_focused.connect(self._on_torrent_focused)

        self.action_bar.status_message.connect(self.status_bar.showMessage)

    def _setup_shortcuts(self) -> None:
        focus_search = QShortcut(QKeySequence("Ctrl+F"), self)
        focus_search.activated.connect(self.search_input.setFocus)

        toggle_theme = QShortcut(QKeySequence("Ctrl+T"), self)
        toggle_theme.activated.connect(self.toggle_theme)

        open_settings = QShortcut(QKeySequence("Ctrl+,"), self)
        open_settings.activated.connect(self.open_settings_dialog)

        cancel_shortcut = QShortcut(QKeySequence("Escape"), self)
        cancel_shortcut.activated.connect(self.workers.cancel_search)

    def _set_mode(self, mode: str) -> None:
        self._current_mode = mode
        self._refresh_mode_ui()
        self._update_bookmark_button()

    def _refresh_mode_ui(self) -> None:
        if self._current_mode == "tv":
            self.tv_btn.setChecked(True)
            self.search_input.setPlaceholderText(
                "Enter TV show title (e.g. Severance, Breaking Bad, The Office)..."
            )
        elif self._current_mode == "movie":
            self.movie_btn.setChecked(True)
            self.search_input.setPlaceholderText(
                "Enter movie title (e.g. Inception, Dune Part Two)..."
            )
        else:
            self.general_btn.setChecked(True)
            self.search_input.setPlaceholderText(
                "Enter general search query across all categories..."
            )

    def _update_bookmark_button(self) -> None:
        query = self.search_input.text().strip() or self._last_query
        if query and self.state_store.is_bookmarked(query, self._current_mode):
            self.bookmark_btn.setText("★ Bookmarked")
        else:
            self.bookmark_btn.setText("☆ Bookmark")

    def _toggle_current_bookmark(self) -> None:
        query = self.search_input.text().strip() or self._last_query
        if not query:
            self.status_bar.showMessage("Enter a search query first to bookmark it.")
            return
        added = self.state_store.toggle_bookmark(query, self._current_mode)
        self._update_bookmark_button()
        self.library_drawer.refresh()
        self.status_bar.showMessage(
            f"Added '{query}' to bookmarks." if added else f"Removed '{query}' from bookmarks."
        )

    def run_query(self, query: str, mode: str) -> None:
        """Set mode and input text and execute search immediately (used by Library drawer)."""
        self._set_mode(mode)
        self.search_input.setText(query)
        self.trigger_search()

    def trigger_search(self) -> None:
        """Start an asynchronous Apibay search for the current input."""
        query = self.search_input.text().strip()
        if not query:
            self.status_bar.showMessage("Please enter a search title first.")
            return

        self._last_query = query
        self.state_store.add_history(query, self._current_mode)
        self.library_drawer.refresh()
        self._update_bookmark_button()
        self.workers.start_search(query, self._current_mode)

    def _on_search_started(self, query: str, mode: str) -> None:
        if self.center_stack.currentIndex() != 3:
            self._previous_center_index = self.center_stack.currentIndex()

        self._search_elapsed_ms = 0
        self._set_search_controls_busy(True)
        self.retry_search_btn.setVisible(False)
        self.empty_message_label.setVisible(False)
        self.loading_title_label.setText(f"Searching Apibay for '{query}'...")
        mode_label = (
            "TV Series" if mode == "tv" else ("Movies" if mode == "movie" else "All Categories")
        )
        self.loading_detail_label.setText(f"Mode: {mode_label} · Endpoint: {self.client.base_url}")
        self.loading_elapsed_label.setText("Fetching releases... (0.0s)")
        self.center_stack.setCurrentIndex(3)
        self.action_bar.set_selected_torrents([])
        self.file_inspector.clear()
        self._loading_timer.start()
        self.status_bar.showMessage(f"Searching Apibay ({mode.upper()}) for '{query}'...")

    def _on_search_completed(self, query: str, mode: str, torrents: list) -> None:
        self._stop_loading_state()

        if not torrents:
            self.center_stack.setCurrentIndex(0)
            self.empty_message_label.setText(f"No results found on Apibay for '{query}'.")
            self.empty_message_label.setVisible(True)
            self.retry_search_btn.setVisible(False)
            self.action_bar.set_selected_torrents([])
            self.file_inspector.clear()
            self.status_bar.showMessage(f"No results found for '{query}'.")
            return

        self.empty_message_label.setVisible(False)
        self.retry_search_btn.setVisible(False)
        self.status_bar.showMessage(f"Found {len(torrents)} release(s) for '{query}'.")

        if mode == "tv":
            self.tv_view.set_search_results(
                query, torrents, default_quality=self.state_store.settings.default_quality
            )
            self.center_stack.setCurrentIndex(1)
            self.action_bar.set_selected_torrents(self.tv_view.checked_torrents())
        else:
            self.table_view.set_torrents(
                torrents,
                preferred_quality=self.state_store.settings.default_quality,
                precheck_first=False,
            )
            self.action_bar.set_default_filename(f"{sanitize_filename(query)}_magnets.txt")
            self.center_stack.setCurrentIndex(2)
            self.action_bar.set_selected_torrents(self.table_view.checked_torrents())

    def _on_search_failed(self, message: str) -> None:
        self._stop_loading_state()
        self.center_stack.setCurrentIndex(0)
        self.empty_message_label.setText(f"Search failed: {message}")
        self.empty_message_label.setVisible(True)
        self.retry_search_btn.setVisible(True)
        self.action_bar.set_selected_torrents([])
        self.status_bar.showMessage(f"Search Error: {message}")

    def _on_search_cancelled(self) -> None:
        self._stop_loading_state()
        restore_idx = self._previous_center_index if self._previous_center_index in (0, 1, 2) else 0
        self.center_stack.setCurrentIndex(restore_idx)
        if restore_idx == 1:
            self.action_bar.set_selected_torrents(self.tv_view.checked_torrents())
        elif restore_idx == 2:
            self.action_bar.set_selected_torrents(self.table_view.checked_torrents())
        else:
            self.action_bar.set_selected_torrents([])
        self.status_bar.showMessage("Search cancelled.")

    def _set_search_controls_busy(self, busy: bool) -> None:
        self.search_btn.setEnabled(not busy)
        self.search_btn.setText("Searching..." if busy else "Search")
        self.tv_btn.setEnabled(not busy)
        self.movie_btn.setEnabled(not busy)
        self.general_btn.setEnabled(not busy)
        self.status_progress.setVisible(busy)

    def _stop_loading_state(self) -> None:
        self._loading_timer.stop()
        self._set_search_controls_busy(False)

    def _update_loading_elapsed(self) -> None:
        self._search_elapsed_ms += self._loading_timer.interval()
        secs = self._search_elapsed_ms / 1000.0
        self.loading_elapsed_label.setText(f"Fetching releases... ({secs:.1f}s)")

    def _on_torrent_focused(self, torrent: object) -> None:
        if not isinstance(torrent, Torrent):
            return
        if not self.inspector_toggle_btn.isChecked():
            return
        if not torrent.id or torrent.id == "0":
            self.file_inspector.show_files(torrent.id, [])
            return
        self.file_inspector.show_loading(torrent)
        self.workers.start_files_lookup(str(torrent.id))

    def apply_theme(self, theme_name: str) -> None:
        """Apply Dark or Light stylesheet to the application and refresh views."""
        clean_theme = "light" if str(theme_name).lower() == "light" else "dark"
        self.state_store.settings.theme = clean_theme
        app = QApplication.instance()
        if isinstance(app, QApplication):
            app.setStyleSheet(build_stylesheet(clean_theme))
        else:  # pragma: no cover - defensive fallback
            self.setStyleSheet(build_stylesheet(clean_theme))

        self.theme_toggle_btn.setText("Dark Mode" if clean_theme == "light" else "Light Mode")
        self.tv_view.set_theme(clean_theme)
        self.table_view.set_theme(clean_theme)

    def toggle_theme(self) -> None:
        """Switch between Dark and Light mode and persist preference."""
        next_theme = "light" if self.state_store.settings.theme == "dark" else "dark"
        self.apply_theme(next_theme)
        self.state_store.save()

    def open_settings_dialog(self) -> None:
        """Open Settings modal dialog and reconfigure ApibayClient on save."""
        dlg = SettingsDialog(
            self.state_store,
            clear_cache_cb=self.client.clear_cache,
            parent=self,
        )
        if dlg.exec():
            s = self.state_store.settings
            self.client.reconfigure(s.api_url, s.proxy or None)
            self.endpoint_label.setText(f"API: {self.client.base_url}")
            self.apply_theme(s.theme)
            self.status_bar.showMessage("Settings saved.")
