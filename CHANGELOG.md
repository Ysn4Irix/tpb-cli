# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-11-26

### Added
- Native **Android Application** under `android/` built with Kotlin, Jetpack Compose, Material 3, OkHttp, Kotlinx Serialization, and Jetpack DataStore (`minSdk 26`, `compileSdk 35`):
  - Full Apibay search parity (`TV Series`, `Movies`, `General`) with regional disambiguation chips, auto-detected seasons, Season Packs vs Multi-Quality Episodes, `Select Recommended`, unchecked-by-default selection, loading/cancel/retry states, and live filters/sorting.
  - `/f.php` File Inspector bottom sheet, bottom thumb-zone `SelectionActionBar` (`Copy`, single/stepped `ACTION_VIEW` `magnet:` dispatch with no-client fallback, and Storage Access Framework `.txt` export).
  - Persistent OLED Dark (`#0D1117` / `#0EA5E9`) & Light Material 3 theme, Cyan Vector Magnet adaptive launcher icon, Library History/Bookmarks tab, and Custom Mirror + HTTP/SOCKS5 proxy validation in Settings.
  - Added JVM unit + OkHttp MockWebServer tests, Compose UI `androidTest` coverage, and `.github/workflows/android-ci.yml`.

## [0.3.0] - 2026-11-26

### Added
- Multi-resolution **Cyan Vector Magnet** desktop application icon (`tpb/gui/assets/`: `tpb-gui.png`, `tpb-gui-64.png`, `tpb-gui-32.png`, `tpb-gui.ico`) wired into `QApplication`, `MainWindow`, Python package data, and `tpb-gui.exe` icon resources.
- Shared `PersistentHeaderController` (`tpb/gui/column_state.py`) and validated `GuiSettings.column_widths` persistence in `gui_state.json`.

### Changed
- Made columns across TV Episode Tree (`Episode / Quality Variant`, `Badge`, `Size`, `Seeds`, `Uploader`), Results Table (content columns `1–8`), and File Inspector interactively resizable (`Interactive` mode) with persisted widths restored across searches and restarts.
- Widened default `MainWindow` workspace dimensions (`1460 × 780`, minimum `1080 × 620`, splitter `[240, 900, 320]`).

## [0.2.0] - 2026-11-26

### Added
- Native **PySide6 Desktop GUI** (`tpb-gui` and `tpb --gui`) distributed as optional extra `pip install tpb-cli[gui]`.
- Async `QThreadPool` workers (`SearchWorker`, `FilesWorker`, `WorkerManager`) with request-ID stale-response guarding and search cancellation.
- Dedicated search loading state with indeterminate progress bars, elapsed timer, Cancel button (`Escape`), and inline Retry error recovery.
- **TV Series Browser** featuring regional disambiguation chips (`US`, `UK`, `All`), auto-detected season navigator, Season Packs view, and multi-quality Episode Tree with single-active-quality toggle per episode.
- **Movies & General Results Table** with live text/resolution filtering, numeric size/seed/date sorting, keyboard Space toggling, and VIP/Trusted uploader tags.
- **Torrent File Inspector Drawer** rendering normalized internal file paths and sizes via `ApibayClient.get_parsed_files`.
- **Magnet Action Bar** supporting clipboard copy, throttled OS `magnet:` client launching with batch safety confirmation (> 5 links), and `.txt` export with Overwrite/Append/Cancel handling.
- **Library & Settings**: Persistent Dark/Light theme switching (`Ctrl+T`), search history, pinned bookmarks, and Apibay mirror / HTTP & SOCKS5 proxy configuration (`Ctrl+,`) with URL boundary validation.
- Standalone Windows `.exe` packaging specification (`packaging/tpb-gui.spec` and `packaging/build_exe.ps1`).
- Production GitHub Actions workflows for CI (lint, format, typecheck, security, cross-platform tests, build) and tagged releases (`.github/workflows/ci.yml`, `.github/workflows/release.yml`).
- Offscreen Qt GUI unit and integration tests (`tests/test_gui_state.py`, `tests/test_gui_workers.py`, `tests/test_gui_views.py`).

### Changed
- Defaulted all desktop GUI search views (TV episodes, season packs, movies, general) to unchecked rows on initial load.
- Extracted shared `format_bytes`, `sanitize_filename`, `TorrentFile`, and `normalize_torrent_files` utilities into `tpb/models.py`.
- Added thread-safe `_cache_lock` and URL/proxy validation (`validate_http_url`, `validate_proxy_url`, `reconfigure`) to `tpb/api.py`.
- Organized internal technical documentation into `docs/`.

## [0.1.0] - 2026-09-26

### Added
- Initial `tpb-cli` release supporting `apibay.org` torrent search via interactive TUI (`InquirerPy` + `Rich`) and scripted CLI flags.
- TV metadata regex parser (`S01E01`, `1x01`, multi-episode spans, season packs, quality/codec extraction).
- Immediate search discovery with auto-detected season counts, regional series disambiguation, and instant `Esc`/`b`/`←` back navigation.
- Tracker-enriched magnet URI generator and `.txt` batch exporter with `Torrent` dataclass coercion fix (`ensure_torrents`).
