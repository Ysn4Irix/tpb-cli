# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
