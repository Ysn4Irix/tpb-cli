"""Offscreen Qt widget and workflow tests for PySide6 desktop GUI components."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path
import re
import sys
from unittest.mock import MagicMock, patch

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication

from tpb.gui.main_window import MainWindow
from tpb.gui.state import AppStateStore
from tpb.gui.theme import DARK_PALETTE, LIGHT_PALETTE, build_stylesheet
from tpb.gui.views.results_table import TorrentResultsView
from tpb.gui.views.tv_browser import TvBrowserView
from tpb.gui.widgets.action_bar import ActionBar
from tpb.gui.widgets.file_inspector import FileInspectorDrawer
from tpb.models import Torrent, TorrentFile
from tpb.parser import enrich_torrent_metadata


def _torrent(tid: str, name: str, seeders: int = 50, size_bytes: int = 1024 * 1024 * 500) -> Torrent:
    t = Torrent(
        id=tid,
        name=name,
        info_hash=f"{tid:0>40}",
        leechers=5,
        seeders=seeders,
        size_bytes=size_bytes,
        username="UploaderX",
        added=1700000000,
        status="vip" if seeders > 100 else "trusted",
    )
    return enrich_torrent_metadata(t)


def test_themes_contain_zero_purple_or_violet_hex():
    forbidden_purple = re.compile(
        r"#(?:7c3aed|8b5cf6|a855f7|9333ea|6366f1|c084fc|d946ef|ec4899|6d28d9|5b21b6)",
        re.IGNORECASE,
    )
    for mode, palette in (("dark", DARK_PALETTE), ("light", LIGHT_PALETTE)):
        qss = build_stylesheet(mode)
        assert len(qss) > 200
        assert not forbidden_purple.search(qss)
        for val in vars(palette).values():
            if isinstance(val, str) and val.startswith("#"):
                assert not forbidden_purple.search(val)


def test_results_table_filter_sort_and_selection(qtbot):
    view = TorrentResultsView(theme_name="dark")
    qtbot.addWidget(view)

    t1 = _torrent("1", "Inception.2010.1080p.BluRay.x264", seeders=120, size_bytes=2_000_000)
    t2 = _torrent("2", "Inception.2010.720p.WEB.x265", seeders=40, size_bytes=1_000_000)
    t3 = _torrent("3", "Inception.2010.2160p.UHD.x265", seeders=300, size_bytes=8_000_000)

    view.set_torrents([t1, t2, t3], preferred_quality="All", precheck_first=False)
    assert view.proxy.rowCount() == 3

    view.quality_combo.setCurrentText("1080p")
    assert view.proxy.rowCount() == 1
    assert view.proxy.data(view.proxy.index(0, 1)) == t1.name

    view.select_visible()
    checked = view.checked_torrents()
    assert checked == [t1]

    view.clear_selection()
    assert view.checked_torrents() == []


def test_tv_browser_disambiguation_seasons_and_single_quality_per_episode(qtbot):
    view = TvBrowserView(theme_name="dark")
    qtbot.addWidget(view)
    view.show()

    torrents = [
        _torrent("1", "The.Office.US.S01E01.1080p.WEB.x265", seeders=200),
        _torrent("2", "The.Office.US.S01E01.720p.WEB.x264", seeders=80),
        _torrent("3", "The.Office.US.S01E02.1080p.WEB.x264", seeders=150),
        _torrent("4", "The.Office.US.Season.1.Complete.1080p", seeders=500, size_bytes=10_000_000),
        _torrent("5", "The.Office.UK.S01E01.720p.x264", seeders=90),
        _torrent("6", "The.Office.UK.S01E02.720p.x264", seeders=70),
    ]

    view.set_search_results("The Office", torrents, default_quality="1080p")

    # Regional disambiguation chips should be visible (`UK`, `US`, `All / Mixed`)
    assert view.disambig_frame.isVisible() is True
    assert len(view.variant_group.buttons()) == 3

    # Default selects first sorted regional tag ("UK"); switch explicitly to US
    us_btn = next(b for b in view.variant_group.buttons() if "(US)" in b.text())
    us_btn.click()

    # Season 1 should have 2 episodes and 1 pack
    checked = view.checked_torrents()
    assert len(checked) == 2
    assert checked[0].id == "1"  # Recommended 1080p for E01
    assert checked[1].id == "3"  # Recommended 1080p for E02

    # Edge Case 2 validation: checking alternate 720p for E01 auto-unchecks 1080p sibling on E01
    ep1_parent = view.episode_tree.topLevelItem(0)
    assert ep1_parent.childCount() == 2
    alt_child = ep1_parent.child(1)
    alt_child.setCheckState(0, Qt.Checked)

    updated = view.checked_torrents()
    assert len(updated) == 2
    assert updated[0].id == "2"  # Switched cleanly without keeping duplicate E01 release
    assert ep1_parent.child(0).checkState(0) == Qt.Unchecked

    # Switching to Season Packs shows Season 1 pack pre-checked
    view.packs_mode_btn.click()
    pack_checked = view.checked_torrents()
    assert len(pack_checked) == 1
    assert pack_checked[0].id == "4"


def test_file_inspector_states_and_retry(qtbot):
    inspector = FileInspectorDrawer()
    qtbot.addWidget(inspector)
    inspector.show()

    t = _torrent("77", "Severance.S01E01.1080p")
    inspector.show_loading(t)
    assert "Loading" in inspector.status_label.text()

    inspector.show_files("77", [TorrentFile("Severance.S01E01.mkv", 2048), TorrentFile("subs.srt", 1024)])
    assert inspector.files_tree.topLevelItemCount() == 2
    assert "2 files" in inspector.status_label.text()

    inspector.show_error("77", "HTTP 502")
    assert inspector.retry_btn.isVisible() is True
    with qtbot.waitSignal(inspector.retry_requested):
        inspector.retry_btn.click()


def test_action_bar_copy_batch_open_and_export(qtbot, tmp_path: Path):
    store = AppStateStore(config_path=tmp_path / "state.json")
    opened_uris = []
    bar = ActionBar(state_store=store, url_opener=lambda uri: opened_uris.append(uri) or True)
    qtbot.addWidget(bar)

    torrents = [_torrent(str(i), f"Show.S01E{i:02d}.1080p") for i in range(1, 8)]
    bar.set_selected_torrents(torrents)

    # Clipboard copy
    copied = bar.copy_selected_magnets()
    assert copied == 7
    clip_text = QGuiApplication.clipboard().text()
    assert clip_text.count("magnet:?") == 7

    # Batch open > 5 cancelled cleanly when user says No
    launched_cancelled = bar.open_selected_magnets(confirm_batch=lambda _n: False)
    assert launched_cancelled == 0
    assert opened_uris == []

    # Batch open > 5 proceeds with stagger when confirmed
    launched_ok = bar.open_selected_magnets(confirm_batch=lambda _n: True)
    assert launched_ok == 7
    qtbot.waitUntil(lambda: len(opened_uris) == 7, timeout=3000)

    # Export write + overwrite/append/cancel collision handling
    dest = tmp_path / "season1_magnets.txt"
    written_path = bar.export_torrents_to_path(dest)
    assert written_path == dest
    assert dest.exists()

    # Cancel collision preserves existing content
    orig_len = len(dest.read_text(encoding="utf-8"))
    assert bar.export_torrents_to_path(dest, collision_resolver=lambda _p: "cancel") is None
    assert len(dest.read_text(encoding="utf-8")) == orig_len

    # Append increases file size
    assert bar.export_torrents_to_path(dest, collision_resolver=lambda _p: "append") == dest
    assert len(dest.read_text(encoding="utf-8")) > orig_len


def test_main_window_integration_and_windowed_stdout_none(qtbot, tmp_path: Path):
    store = AppStateStore(config_path=tmp_path / "main_state.json")
    client = MagicMock()
    client.base_url = "https://apibay.org"
    client.proxy = None

    # Simulate windowed PyInstaller runtime where sys.stdout is None
    with patch.object(sys, "stdout", None), patch.object(sys, "stderr", None):
        window = MainWindow(client=client, state_store=store)
        qtbot.addWidget(window)
        window.show()

        # Simulate completed Movie search
        movie = _torrent("500", "Dune.Part.Two.2024.1080p.WEB.x265", seeders=450)
        window._on_search_completed("Dune Part Two", "movie", [movie])
        assert window.center_stack.currentIndex() == 2
        assert window.action_bar._selected == [movie]

        # Simulate Theme toggle persistence
        window.toggle_theme()
        assert store.settings.theme == "light"
        assert "Dark Mode" in window.theme_toggle_btn.text()

        # Simulate empty search fallback
        window._on_search_completed("NonExistentShow999", "tv", [])
        assert window.center_stack.currentIndex() == 0
        assert window.empty_message_label.isVisible() is True


def test_main_window_search_loading_cancel_and_error_states(qtbot, tmp_path: Path):
    store = AppStateStore(config_path=tmp_path / "loading_state.json")
    client = MagicMock()
    client.base_url = "https://apibay.org"
    client.proxy = None

    window = MainWindow(client=client, state_store=store)
    window.workers.thread_pool = MagicMock()
    qtbot.addWidget(window)
    window.show()

    # Load an initial movie result so cancel restores index 2 and selection
    movie = _torrent("501", "Arrival.2016.1080p.BluRay.x264", seeders=300)
    window._on_search_completed("Arrival", "movie", [movie])
    assert window.center_stack.currentIndex() == 2
    assert window.action_bar._selected == [movie]

    # Trigger a new search -> enters loading state cleanly
    window.search_input.setText("Severance")
    window.trigger_search()

    assert window.center_stack.currentIndex() == 3
    assert window.search_btn.isEnabled() is False
    assert window.search_btn.text() == "Searching..."
    assert window.tv_btn.isEnabled() is False
    assert window.status_progress.isVisible() is True
    assert window.action_bar._selected == []
    assert "Severance" in window.loading_title_label.text()

    # Verify elapsed indicator updates cleanly
    window._update_loading_elapsed()
    assert "0.2s" in window.loading_elapsed_label.text()

    # Cancel search -> exits loading state and restores prior view & selection
    window.cancel_search_btn.click()
    assert window.workers.is_searching is False
    assert window.center_stack.currentIndex() == 2
    assert window.search_btn.isEnabled() is True
    assert window.search_btn.text() == "Search"
    assert window.tv_btn.isEnabled() is True
    assert window.status_progress.isVisible() is False
    assert window.action_bar._selected == [movie]
    assert "cancelled" in window.status_bar.currentMessage().lower()

    # Failure after loading -> displays error state & Retry button
    window.trigger_search()
    assert window.center_stack.currentIndex() == 3
    window._on_search_failed("Connection timed out")
    assert window.center_stack.currentIndex() == 0
    assert window.search_btn.isEnabled() is True
    assert window.status_progress.isVisible() is False
    assert "Connection timed out" in window.empty_message_label.text()
    assert window.retry_search_btn.isVisible() is True
