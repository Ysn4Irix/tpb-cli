"""TV Series browser view with regional disambiguation, auto-detected seasons, and episode matrix."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from tpb.gui.column_state import PersistentHeaderController
from tpb.gui.state import AppStateStore
from tpb.gui.theme import ThemePalette, get_palette
from tpb.gui.views.results_table import TorrentResultsView
from tpb.models import Torrent, sanitize_filename
from tpb.parser import (
    detect_series_variants,
    filter_and_group_episodes,
    get_detected_seasons_summary,
    get_episode_quality_variants,
    get_season_packs,
)

TORRENT_ROLE = Qt.ItemDataRole.UserRole + 10
EPISODE_NUM_ROLE = Qt.ItemDataRole.UserRole + 11


class TvBrowserView(QWidget):
    """Interactive TV workspace exposing regional variants, seasons, packs, and multi-quality episodes."""

    selection_changed = Signal(list)
    torrent_focused = Signal(object)
    export_hint_changed = Signal(str)

    def __init__(
        self,
        theme_name: str = "dark",
        parent: QWidget | None = None,
        state_store: AppStateStore | None = None,
    ):
        super().__init__(parent)
        self._theme_name = theme_name
        self._state_store = state_store
        self._palette: ThemePalette = get_palette(theme_name)
        self._show_name = ""
        self._all_torrents: list[Torrent] = []
        self._filtered_torrents: list[Torrent] = []
        self._series_variants: dict[str, list[Torrent]] = {}
        self._seasons_summary: dict[int, dict] = {}
        self._current_season: int | None = None
        self._current_submode: str = "episodes"  # "episodes" | "packs" | "all"
        self._updating_tree = False

        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        # Series Disambiguation strip (shown when US/UK/etc. regional variants exist)
        self.disambig_frame = QFrame()
        self.disambig_frame.setObjectName("PanelSurface")
        disambig_layout = QHBoxLayout(self.disambig_frame)
        disambig_layout.setContentsMargins(10, 6, 10, 6)
        disambig_layout.setSpacing(8)

        self.disambig_label = QLabel("Multiple series versions detected:")
        disambig_font = QFont()
        disambig_font.setBold(True)
        self.disambig_label.setFont(disambig_font)
        disambig_layout.addWidget(self.disambig_label)

        self.variant_chips_layout = QHBoxLayout()
        self.variant_chips_layout.setSpacing(6)
        disambig_layout.addLayout(self.variant_chips_layout)
        disambig_layout.addStretch(1)

        self.variant_group = QButtonGroup(self)
        self.variant_group.setExclusive(True)
        self.disambig_frame.setVisible(False)
        root.addWidget(self.disambig_frame)

        # Main TV Splitter: Seasons list (left) | Content tabs (right)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left Season Navigator
        left_panel = QFrame()
        left_panel.setObjectName("PanelSurface")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(6)

        self.season_header = QLabel("Detected Seasons")
        header_font = QFont()
        header_font.setBold(True)
        self.season_header.setFont(header_font)
        left_layout.addWidget(self.season_header)

        self.season_list = QListWidget()
        self.season_list.setAccessibleName("Detected seasons")
        self.season_list.setMinimumWidth(190)
        left_layout.addWidget(self.season_list, stretch=1)
        splitter.addWidget(left_panel)

        # Right Season Workspace
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        # Controls Bar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.episodes_mode_btn = QPushButton("Episodes")
        self.episodes_mode_btn.setCheckable(True)
        self.episodes_mode_btn.setAccessibleName("Show individual episodes")
        self.packs_mode_btn = QPushButton("Season Packs")
        self.packs_mode_btn.setCheckable(True)
        self.packs_mode_btn.setAccessibleName("Show complete season packs")
        self.all_mode_btn = QPushButton("All Releases")
        self.all_mode_btn.setCheckable(True)
        self.all_mode_btn.setAccessibleName("Show all matching releases")

        self.submode_group = QButtonGroup(self)
        self.submode_group.setExclusive(True)
        self.submode_group.addButton(self.episodes_mode_btn)
        self.submode_group.addButton(self.packs_mode_btn)
        self.submode_group.addButton(self.all_mode_btn)

        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["1080p", "720p", "2160p", "480p", "Any"])
        self.quality_combo.setAccessibleName("Preferred TV resolution")

        self.select_recommended_btn = QPushButton("Select Recommended")
        self.select_recommended_btn.setAccessibleName("Select top release for every episode")
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setAccessibleName("Clear selected TV releases")

        toolbar.addWidget(self.episodes_mode_btn)
        toolbar.addWidget(self.packs_mode_btn)
        toolbar.addWidget(self.all_mode_btn)
        toolbar.addStretch(1)
        toolbar.addWidget(QLabel("Preferred Quality:"))
        toolbar.addWidget(self.quality_combo)
        toolbar.addWidget(self.select_recommended_btn)
        toolbar.addWidget(self.clear_btn)
        right_layout.addLayout(toolbar)

        # Stacked content: Episode Tree vs Table (Packs / All)
        self.content_stack = QStackedWidget()

        self.episode_tree = QTreeWidget()
        self.episode_tree.setAccessibleName("TV episodes and quality variants")
        self.episode_tree.setColumnCount(5)
        self.episode_tree.setHeaderLabels(
            ["Episode / Quality Variant", "Badge", "Size", "Seeds", "Uploader"]
        )
        self.episode_tree.setAlternatingRowColors(True)
        self._episode_header_ctrl = PersistentHeaderController(
            header=self.episode_tree.header(),
            state_store=self._state_store,
            state_key="tv_episodes",
            default_widths=[460, 115, 95, 75, 135],
            stretch_last_section=False,
            minimum_section_size=48,
        )

        self.fallback_table = TorrentResultsView(
            theme_name=self._theme_name,
            parent=self,
            state_store=self._state_store,
            columns_state_key="tv_results_table",
        )

        self.content_stack.addWidget(self.episode_tree)  # index 0
        self.content_stack.addWidget(self.fallback_table)  # index 1
        right_layout.addWidget(self.content_stack, stretch=1)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([220, 780])

        root.addWidget(splitter, stretch=1)

    def _connect_signals(self) -> None:
        self.season_list.currentRowChanged.connect(self._on_season_row_changed)
        self.episodes_mode_btn.clicked.connect(lambda: self._switch_submode("episodes"))
        self.packs_mode_btn.clicked.connect(lambda: self._switch_submode("packs"))
        self.all_mode_btn.clicked.connect(lambda: self._switch_submode("all"))
        self.quality_combo.currentTextChanged.connect(self._on_quality_changed)
        self.select_recommended_btn.clicked.connect(self.select_recommended_episodes)
        self.clear_btn.clicked.connect(self.clear_selection)
        self.episode_tree.itemChanged.connect(self._on_episode_item_changed)
        self.episode_tree.itemClicked.connect(self._on_episode_item_focused)
        self.episode_tree.currentItemChanged.connect(
            lambda cur, _prev: self._on_episode_item_focused(cur, 0)
        )
        self.fallback_table.selection_changed.connect(self._on_table_selection_changed)
        self.fallback_table.torrent_focused.connect(self.torrent_focused.emit)

    def set_theme(self, theme_name: str) -> None:
        """Apply theme palette updates to both episode tree and pack/all table."""
        self._theme_name = theme_name
        self._palette = get_palette(theme_name)
        self.fallback_table.set_theme(theme_name)
        if self._current_season is not None and self._current_submode == "episodes":
            self._populate_season_content()

    def set_search_results(
        self, show_name: str, torrents: list[Torrent], default_quality: str = "1080p"
    ) -> None:
        """Load fresh search results, detect regional variants and seasons, and render UI."""
        self._show_name = show_name.strip()
        self._all_torrents = list(torrents)
        self.quality_combo.blockSignals(True)
        if default_quality in ("1080p", "720p", "2160p", "480p", "Any"):
            self.quality_combo.setCurrentText(default_quality)
        self.quality_combo.blockSignals(False)

        self._series_variants = detect_series_variants(self._all_torrents)
        self._rebuild_variant_chips()

        if self._series_variants:
            first_tag = sorted(self._series_variants.keys())[0]
            self._apply_variant_filter(first_tag)
        else:
            self._apply_variant_filter("all")

    def _rebuild_variant_chips(self) -> None:
        for btn in list(self.variant_group.buttons()):
            self.variant_group.removeButton(btn)
            self.variant_chips_layout.removeWidget(btn)
            btn.deleteLater()

        if not self._series_variants:
            self.disambig_frame.setVisible(False)
            return

        self.disambig_label.setText(f"Multiple series versions detected for '{self._show_name}':")
        sorted_tags = sorted(self._series_variants.keys())
        for idx, tag in enumerate(sorted_tags):
            count = len(self._series_variants[tag])
            btn = QPushButton(f"{self._show_name} ({tag}) [{count}]")
            btn.setCheckable(True)
            btn.setChecked(idx == 0)
            btn.clicked.connect(lambda _checked=False, t=tag: self._apply_variant_filter(t))
            self.variant_group.addButton(btn)
            self.variant_chips_layout.addWidget(btn)

        all_btn = QPushButton(f"All / Mixed [{len(self._all_torrents)}]")
        all_btn.setCheckable(True)
        all_btn.clicked.connect(lambda _checked=False: self._apply_variant_filter("all"))
        self.variant_group.addButton(all_btn)
        self.variant_chips_layout.addWidget(all_btn)

        self.disambig_frame.setVisible(True)

    def _apply_variant_filter(self, variant_key: str) -> None:
        if variant_key != "all" and variant_key in self._series_variants:
            self._filtered_torrents = list(self._series_variants[variant_key])
        else:
            self._filtered_torrents = list(self._all_torrents)

        self._seasons_summary = get_detected_seasons_summary(self._filtered_torrents)
        self._populate_season_list()

    def _populate_season_list(self) -> None:
        self.season_list.blockSignals(True)
        self.season_list.clear()

        if self._seasons_summary:
            self.season_header.setText(f"Detected Seasons ({len(self._seasons_summary)})")
            for s_num, info in self._seasons_summary.items():
                eps_n = len(info["episodes"])
                packs_n = len(info["packs"])
                parts = []
                if eps_n:
                    parts.append(f"{eps_n} ep{'s' if eps_n != 1 else ''}")
                if packs_n:
                    parts.append(f"{packs_n} pack{'s' if packs_n != 1 else ''}")
                if not parts:
                    tot = info["total_torrents"]
                    parts.append(f"{tot} release{'s' if tot != 1 else ''}")
                item = QListWidgetItem(f"Season {s_num}  ({', '.join(parts)})")
                item.setData(Qt.ItemDataRole.UserRole, s_num)
                self.season_list.addItem(item)
        else:
            self.season_header.setText("Detected Seasons (None)")

        all_item = QListWidgetItem(f"All Releases ({len(self._filtered_torrents)})")
        all_item.setData(Qt.ItemDataRole.UserRole, None)
        self.season_list.addItem(all_item)
        self.season_list.blockSignals(False)

        if self.season_list.count() > 0:
            self.season_list.setCurrentRow(0)

    def _on_season_row_changed(self, row: int) -> None:
        if row < 0:
            return
        item = self.season_list.item(row)
        self._current_season = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        self._update_export_hint()
        self._populate_season_content()

    def _update_export_hint(self) -> None:
        slug = sanitize_filename(self._show_name or "torrents")
        if self._current_season is not None:
            self.export_hint_changed.emit(f"{slug}_S{self._current_season:02d}_magnets.txt")
        else:
            self.export_hint_changed.emit(f"{slug}_magnets.txt")

    def _on_quality_changed(self, _quality: str) -> None:
        self._populate_season_content()

    def _switch_submode(self, mode: str) -> None:
        self._current_submode = mode
        if mode == "episodes":
            self.content_stack.setCurrentIndex(0)
            self.select_recommended_btn.setEnabled(True)
            self.clear_btn.setEnabled(True)
            self._emit_tree_selection()
        elif mode == "packs":
            season = self._current_season
            packs = get_season_packs(self._filtered_torrents, season) if season is not None else []
            self.content_stack.setCurrentIndex(1)
            self.select_recommended_btn.setEnabled(False)
            self.clear_btn.setEnabled(False)
            self.fallback_table.set_torrents(
                packs, preferred_quality=self.quality_combo.currentText(), precheck_first=False
            )
        else:
            pool = (
                self._seasons_summary[self._current_season]["torrents"]
                if self._current_season in self._seasons_summary
                else self._filtered_torrents
            )
            self.content_stack.setCurrentIndex(1)
            self.select_recommended_btn.setEnabled(False)
            self.clear_btn.setEnabled(False)
            self.fallback_table.set_torrents(
                pool, preferred_quality=self.quality_combo.currentText()
            )

    def _populate_season_content(self) -> None:
        season = self._current_season
        pref_q = self.quality_combo.currentText()
        quality_arg = None if pref_q == "Any" else pref_q

        if season is None:
            self.episodes_mode_btn.setEnabled(False)
            self.packs_mode_btn.setEnabled(False)
            self.all_mode_btn.setEnabled(True)
            self.all_mode_btn.setChecked(True)
            self._switch_submode("all")
            return

        packs = get_season_packs(self._filtered_torrents, season)
        episodes_map = filter_and_group_episodes(
            self._filtered_torrents, target_season=season, preferred_quality=quality_arg
        )

        self.episodes_mode_btn.setText(f"Episodes ({len(episodes_map)})")
        self.packs_mode_btn.setText(f"Season Packs ({len(packs)})")
        self.episodes_mode_btn.setEnabled(bool(episodes_map))
        self.packs_mode_btn.setEnabled(bool(packs))
        self.all_mode_btn.setEnabled(True)

        self._build_episode_tree(episodes_map)

        if episodes_map:
            self.episodes_mode_btn.setChecked(True)
            self._switch_submode("episodes")
        elif packs:
            self.packs_mode_btn.setChecked(True)
            self._switch_submode("packs")
        else:
            self.all_mode_btn.setChecked(True)
            self._switch_submode("all")

    def _build_episode_tree(self, episodes_map: dict[int, list[Torrent]]) -> None:
        self._updating_tree = True
        try:
            self.episode_tree.clear()
            bold_font = QFont()
            bold_font.setBold(True)

            for ep_num in sorted(episodes_map.keys()):
                variants = get_episode_quality_variants(episodes_map[ep_num])
                opt_label = f"{len(variants)} option{'s' if len(variants) != 1 else ''}"
                parent = QTreeWidgetItem([f"Episode {ep_num:02d} ({opt_label})", "", "", "", ""])
                parent.setFont(0, bold_font)
                parent.setFlags(Qt.ItemFlag.ItemIsEnabled)
                parent.setData(0, EPISODE_NUM_ROLE, ep_num)
                self.episode_tree.addTopLevelItem(parent)

                for idx, variant in enumerate(variants):
                    is_default = idx == 0
                    codec_str = f" | {variant.codec}" if variant.codec != "Unknown" else ""
                    title_text = f"[{variant.quality}{codec_str}] {variant.name}"
                    badge = "Recommended" if is_default else ""
                    uploader = variant.username or "Anonymous"
                    if variant.is_vip:
                        uploader = f"[VIP] {uploader}"
                    elif variant.is_trusted:
                        uploader = f"[TRUST] {uploader}"

                    child = QTreeWidgetItem(
                        [
                            title_text,
                            badge,
                            variant.human_size,
                            str(variant.seeders),
                            uploader,
                        ]
                    )
                    child.setFlags(
                        Qt.ItemFlag.ItemIsEnabled
                        | Qt.ItemFlag.ItemIsSelectable
                        | Qt.ItemFlag.ItemIsUserCheckable
                    )
                    child.setCheckState(0, Qt.CheckState.Unchecked)
                    child.setData(0, TORRENT_ROLE, variant)
                    child.setData(0, EPISODE_NUM_ROLE, ep_num)
                    child.setTextAlignment(
                        2, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                    child.setTextAlignment(
                        3, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )

                    if variant.seeders > 50:
                        child.setForeground(3, QColor(self._palette.seed_high))
                        child.setToolTip(3, "Healthy (>50 seeders)")
                    elif variant.seeders > 5:
                        child.setForeground(3, QColor(self._palette.seed_mid))
                        child.setToolTip(3, "Moderate (6-50 seeders)")
                    else:
                        child.setForeground(3, QColor(self._palette.seed_low))
                        child.setToolTip(3, "Low (<=5 seeders)")

                    if is_default:
                        child.setForeground(1, QColor(self._palette.accent))
                    parent.addChild(child)

                parent.setExpanded(True)
        finally:
            self._updating_tree = False

    def _on_episode_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        """Auto-uncheck sibling qualities for the same episode when an alternate quality is checked."""
        if self._updating_tree or column != 0:
            return
        parent = item.parent()
        if parent is None:
            return

        if item.checkState(0) == Qt.CheckState.Checked:
            self._updating_tree = True
            try:
                for i in range(parent.childCount()):
                    sibling = parent.child(i)
                    if (
                        sibling is not None
                        and sibling is not item
                        and sibling.checkState(0) == Qt.CheckState.Checked
                    ):
                        sibling.setCheckState(0, Qt.CheckState.Unchecked)
            finally:
                self._updating_tree = False

        self._emit_tree_selection()

    def _on_episode_item_focused(self, item: QTreeWidgetItem | None, _col: int) -> None:
        if item is None:
            return
        torrent = item.data(0, TORRENT_ROLE)
        if isinstance(torrent, Torrent):
            self.torrent_focused.emit(torrent)

    def _on_table_selection_changed(self, torrents: list) -> None:
        if self._current_submode != "episodes":
            self.selection_changed.emit(torrents)

    def select_recommended_episodes(self) -> None:
        """Check only the first (top-seeded preferred quality) release for each episode."""
        self._updating_tree = True
        try:
            for i in range(self.episode_tree.topLevelItemCount()):
                parent = self.episode_tree.topLevelItem(i)
                if parent is None:
                    continue
                for j in range(parent.childCount()):
                    child = parent.child(j)
                    if child is not None:
                        child.setCheckState(
                            0, Qt.CheckState.Checked if j == 0 else Qt.CheckState.Unchecked
                        )
        finally:
            self._updating_tree = False
        self._emit_tree_selection()

    def clear_selection(self) -> None:
        """Uncheck all episode releases in the tree."""
        self._updating_tree = True
        try:
            for i in range(self.episode_tree.topLevelItemCount()):
                parent = self.episode_tree.topLevelItem(i)
                if parent is None:
                    continue
                for j in range(parent.childCount()):
                    child = parent.child(j)
                    if child is not None:
                        child.setCheckState(0, Qt.CheckState.Unchecked)
        finally:
            self._updating_tree = False
        self._emit_tree_selection()

    def checked_torrents(self) -> list[Torrent]:
        """Return currently selected torrents from the active TV sub-view."""
        if self._current_submode != "episodes":
            return self.fallback_table.checked_torrents()

        selected: list[Torrent] = []
        for i in range(self.episode_tree.topLevelItemCount()):
            parent = self.episode_tree.topLevelItem(i)
            if parent is None:
                continue
            for j in range(parent.childCount()):
                child = parent.child(j)
                if child is not None and child.checkState(0) == Qt.CheckState.Checked:
                    t = child.data(0, TORRENT_ROLE)
                    if isinstance(t, Torrent):
                        selected.append(t)
        return selected

    def _emit_tree_selection(self) -> None:
        if self._current_submode == "episodes":
            self.selection_changed.emit(self.checked_torrents())
