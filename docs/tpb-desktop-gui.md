# TPB Desktop GUI (`tpb-desktop-gui`)

## Overview
Build a native Python desktop GUI (`PySide6` / Qt) on top of the existing `tpb` core modules (`api`, `models`, `parser`, `exporter`) so users can search Apibay, resolve regional TV series variants, browse auto-detected seasons and multi-quality episodes, inspect torrent file trees (`get_files()`), and copy/open/export magnet links with zero browser overhead.

**Confirmed Architecture Decisions (Socratic Gate):**
- **GUI Stack**: Native Python Desktop via `PySide6` (Qt Widgets + QSS styling).
- **Torrent Action Scope**: Search, File Inspection (`ApibayClient.get_files()`), Batch Selection, Clipboard Copy, `.txt` Export (`export_magnets_to_file`), and OS `magnet:` URI launch.
- **Packaging**: Optional extra `pip install tpb-cli[gui]` + `tpb-gui` / `tpb --gui` entrypoints in this repository, plus an optional PyInstaller standalone Windows `.exe` build configuration.
- **v1 Target & Features**: Windows-primary (cross-platform PySide6) with MVP CLI Parity + Torrent File Inspector + Dark/Light Mode + Search History/Bookmarks + Network/Proxy Settings.
- **Git Branch Note**: User requested working directly on the primary branch (`master` per `.git/HEAD`, instead of creating a `feature/*` branch).

## Project Type
**PYTHON DESKTOP GUI** (Native `PySide6` desktop frontend integrated as an optional `[gui]` package extra on `tpb-cli`, reusing the existing headless Python core).

## Success Criteria
- [ ] Headless CLI (`pip install tpb-cli`) installs with zero Qt dependencies and shows a clear install hint if `tpb --gui` is run without `[gui]`.
- [ ] `pip install -e .[gui]` provides `tpb-gui` and `tpb --gui`, launching a responsive desktop window without blocking UI threads during HTTP calls.
- [ ] TV workflow visually exposes regional disambiguation (`US` / `UK` / `All`), auto-detected seasons with episode/pack counts, season pack vs episode picker, and per-episode multi-quality checkboxes (best release pre-checked).
- [ ] Movie & General modes render sortable, filterable release tables with VIP/Trusted uploader badges, resolution/codec chips, seed/leech health coloring, and multi-select actions.
- [ ] File Inspector side drawer loads and displays internal torrent file paths and sizes via `ApibayClient.get_files()`.
- [ ] Action bar supports 1-click Copy Magnet(s), Open Magnet(s) in OS default torrent client, and Export to `.txt` with overwrite/append confirmation.
- [ ] Dark mode (default) and Light mode toggle cleanly; Search History, Bookmarks, and Proxy/API URL settings persist across restarts.
- [ ] All headless CLI tests + new offscreen GUI test suite pass, `python -m build` succeeds, and PyInstaller script builds a working Windows `.exe`.

## Tech Stack
| Layer | Technology | Rationale |
|---|---|---|
| **UI Framework** | `PySide6 >= 6.7.0` (Qt Widgets) | Native OS file dialogs, smooth virtualized `QTableView`/`QTreeWidget` for large torrent lists, Windows high-DPI & Dark theme support, single-process Python imports. |
| **Async / Threading** | `QThreadPool` + `QRunnable` signals | Keeps `ApibayClient` (`httpx`) HTTP I/O off the Qt main thread with stale-request cancellation IDs. |
| **Core Logic** | Existing `tpb.api`, `tpb.models`, `tpb.parser`, `tpb.exporter` | Reuses existing parsing, caching, torrent models, and magnet export directly with zero duplicated business logic. |
| **Persistence** | `QSettings` / JSON in OS user config dir | Persists theme, proxy, API mirror URL, recent searches, and bookmarks without needing a database. |
| **Packaging** | `setuptools` optional extra `[gui]` + `PyInstaller` | Keeps core `tpb-cli` minimal while providing `tpb-gui` and optional standalone Windows `.exe` distribution. |
| **Testing** | `pytest` + `QT_QPA_PLATFORM=offscreen` (+ `pytest-qt` dev extra) | Verifies widgets, state models, workers, and views headlessly in CI/Windows without manual clicks. |

## File Structure
```text
tpb-cli/
├── pyproject.toml                  # [MOD] Add [project.optional-dependencies] gui/dev & tpb-gui script
├── MANIFEST.in                     # [MOD] Include GUI QSS/assets if any; exclude packaging temp artifacts
├── README.md                       # [MOD] Document [gui] install, tpb-gui, features & .exe build
├── tpb/
│   ├── api.py                      # [MOD] Thread-safe cache lock & normalized TorrentFile model for get_files()
│   ├── cli.py                      # [MOD] Add --gui flag with lazy import + friendly missing-extra message
│   ├── models.py                   # [MOD] Add TorrentFile dataclass & shared sanitize_filename helper
│   ├── interactive.py              # [MOD] Import sanitize_filename from shared utility cleanly
│   └── gui/
│       ├── __init__.py             # [NEW] GUI subpackage init
│       ├── app.py                  # [NEW] QApplication bootstrap, single-instance/high-DPI setup & main()
│       ├── main_window.py          # [NEW] Main shell: search bar, mode switch, sidebar/drawer, status bar
│       ├── state.py                # [NEW] Settings, theme, search history & bookmarks persistence
│       ├── theme.py                # [NEW] Dark & Light QSS stylesheets and status color tokens (no purple/violet)
│       ├── workers.py              # [NEW] QRunnable workers for search & get_files with stale-request guards
│       ├── views/
│       │   ├── __init__.py         # [NEW]
│       │   ├── results_table.py    # [NEW] Movie/General sortable/filterable QTableView + model
│       │   └── tv_browser.py       # [NEW] Series disambiguation, season selector, pack vs episode quality tree
│       └── widgets/
│           ├── __init__.py         # [NEW]
│           ├── file_inspector.py   # [NEW] Torrent internal file tree drawer (uses get_files())
│           ├── action_bar.py       # [NEW] Copy magnet, Open OS magnet URI, Export .txt + collision dialog
│           ├── library_drawer.py   # [NEW] Search history & pinned show/movie bookmarks panel
│           └── settings_dialog.py  # [NEW] Proxy, custom API URL, default quality & theme dialog
├── packaging/
│   ├── tpb-gui.spec                # [NEW] PyInstaller spec for Windows standalone --windowed .exe
│   └── build_exe.ps1               # [NEW] Helper script to build & smoke-check standalone executable
└── tests/
    ├── test_gui_state.py           # [NEW] Settings, history, bookmarks & TorrentFile normalization tests
    ├── test_gui_workers.py         # [NEW] Background search/files worker & stale-request guard tests
    └── test_gui_views.py           # [NEW] Offscreen Qt widget/model tests for TV, Movie & ActionBar flows
```

## Task Breakdown

- [x] **Task 1 (`T1`): Core Preparation & Optional Packaging Setup**
  - **Agent:** `backend-specialist` | **Skills:** `python-patterns`, `clean-code` | **Priority:** P0 | **Deps:** None
  - **INPUT → OUTPUT → VERIFY:** Move `sanitize_filename` to a shared location (`tpb/models.py`), add `TorrentFile` + parser normalization to `tpb/api.py` (`get_parsed_files()`), guard `ApibayClient._cache` with `threading.Lock`, make `tpb/cli.py` lazily load interactive/GUI modules, add `--gui` flag to `tpb/cli.py`, and add `[project.optional-dependencies] gui`/`dev` + `[project.gui-scripts] tpb-gui` in `pyproject.toml` → Updated core modules & packaging config → Verified all existing + new CLI tests pass.

- [x] **Task 2 (`T2`): GUI App Bootstrap, Background Workers & Persistent State**
  - **Agent:** `backend-specialist` | **Skills:** `python-patterns`, `clean-code` | **Priority:** P0 | **Deps:** `T1`
  - **INPUT → OUTPUT → VERIFY:** Created `tpb/gui/app.py`, `tpb/gui/workers.py` (`SearchWorker`, `FilesWorker`, `WorkerManager` via `QThreadPool` with stale-request guards), and `tpb/gui/state.py` (`AppStateStore`) → Verified in `tests/test_gui_workers.py` & `tests/test_gui_state.py`.

- [x] **Task 3 (`T3`): Theme System (Dark / Light) & Main Window Shell**
  - **Agent:** `frontend-specialist` | **Skills:** `python-patterns`, `clean-code` | **Priority:** P1 | **Deps:** `T2`
  - **INPUT → OUTPUT → VERIFY:** Created `tpb/gui/theme.py` (Dark & Light QSS; zero purple/violet hex codes) and `tpb/gui/main_window.py` → Verified under offscreen Qt + `sys.stdout=None` test.

- [x] **Task 4 (`T4`): Movies & General Results Table View**
  - **Agent:** `frontend-specialist` | **Skills:** `python-patterns`, `clean-code` | **Priority:** P1 | **Deps:** `T3`
  - **INPUT → OUTPUT → VERIFY:** Created `tpb/gui/views/results_table.py` (`TorrentTableModel` + `TorrentFilterProxyModel` + `TorrentResultsView`) → Verified sorting/filtering/selection in `tests/test_gui_views.py`.

- [x] **Task 5 (`T5`): TV Series Disambiguation, Auto-Detected Seasons & Episode Quality Matrix**
  - **Agent:** `frontend-specialist` | **Skills:** `python-patterns`, `clean-code` | **Priority:** P1 | **Deps:** `T3`
  - **INPUT → OUTPUT → VERIFY:** Created `tpb/gui/views/tv_browser.py` with regional variant chips, auto-detected Season list, Pack table switcher, and Episode Tree (checking alternate quality auto-unchecks sibling release) → Verified in `tests/test_gui_views.py`.

- [x] **Task 6 (`T6`): Torrent File Inspector Drawer & Magnet Action / Export Bar**
  - **Agent:** `frontend-specialist` | **Skills:** `python-patterns`, `clean-code` | **Priority:** P1 | **Deps:** `T2`, `T4`, `T5`
  - **INPUT → OUTPUT → VERIFY:** Created `tpb/gui/widgets/file_inspector.py` and `tpb/gui/widgets/action_bar.py` (clipboard copy, staggered OS `magnet:` launch with >5 batch confirmation, and `.txt` export with Overwrite/Append/Cancel resolution) → Verified in `tests/test_gui_views.py`.

- [x] **Task 7 (`T7`): v1 Extras — Search History, Bookmarks & Network Settings Dialog**
  - **Agent:** `frontend-specialist` | **Skills:** `python-patterns`, `clean-code` | **Priority:** P2 | **Deps:** `T2`, `T3`
  - **INPUT → OUTPUT → VERIFY:** Created `tpb/gui/widgets/library_drawer.py` and `tpb/gui/widgets/settings_dialog.py` → Verified persistence and integration with `MainWindow`.

- [x] **Task 8 (`T8`): Headless GUI & Integration Test Suite**
  - **Agent:** `test-engineer` | **Skills:** `testing-patterns`, `clean-code` | **Priority:** P1 | **Deps:** `T4`, `T5`, `T6`, `T7`
  - **INPUT → OUTPUT → VERIFY:** Added `tests/conftest.py`, `tests/test_gui_state.py`, `tests/test_gui_workers.py`, and `tests/test_gui_views.py` → All 39 tests pass (`39 passed in 2.11s`, 0 warnings).

- [x] **Task 9 (`T9`): Standalone Windows `.exe` Packaging & Documentation**
  - **Agent:** `devops-engineer` | **Skills:** `deployment-procedures`, `documentation-templates` | **Priority:** P2 | **Deps:** `T1`, `T6`, `T8`
  - **INPUT → OUTPUT → VERIFY:** Added `packaging/tpb-gui.spec` and `packaging/build_exe.ps1`, updated `MANIFEST.in` and `README.md`, ran `python -m build` and `.\packaging\build_exe.ps1` producing `dist/tpb-gui.exe` (51.38 MB) and verified headless boot.

## Key Risks & Edge Cases to Guard
1. **Windowed `.exe` `sys.stdout` is `None`**: With `PyInstaller --windowed`, `sys.stdout`/`sys.stderr` can be `None`; avoid importing `InquirerPy`/`prompt_toolkit` in `tpb-gui` and guard Rich `Console()` / `reconfigure()` calls.
2. **Thread Safety on `ApibayClient._cache`**: Concurrent search/tab clicks from background `QRunnable` workers must lock `_cache` reads/writes and tag responses with request IDs so older slow searches never overwrite newer queries.
3. **Apibay `get_files()` Payload Quirks**: `/f.php` may return empty lists, non-list JSON, or varying numeric/string sizes; normalize defensively into `TorrentFile` records.
4. **Heavy `PySide6` Wheel Size**: Keeping `PySide6` inside `[project.optional-dependencies] gui` protects lightweight headless `pip install tpb-cli` users while enabling `pip install tpb-cli[gui]`.

## Phase X: Final Verification
- [x] **Dependencies & Packaging**: `pip install -e ".[gui,dev]"` and `python -m build` succeeded cleanly (`dist/tpb_cli-0.1.0-py3-none-any.whl` & `dist/tpb_cli-0.1.0.tar.gz`).
- [x] **Unit & Offscreen GUI Tests**: `pytest -v` (with `QT_QPA_PLATFORM=offscreen` via `tests/conftest.py`) passed all 39 tests with 0 warnings.
- [ ] **Lint & Type Check**: `type_coverage.py` passed (`ACCEPTABLE`, 72% annotated); `lint_runner.py` reported `ruff` and `mypy` not installed in the Python environment.
- [ ] **Security Scan**: Secrets, dependencies, and config checks passed (0 findings); `pattern_scanner` flagged regex false positives on Qt `.exec()` calls and UI display strings (`Select` / `selected`).
- [x] **Theme & Design Compliance**: Verified zero purple/violet hex codes in `tpb/gui/theme.py` via test assertions; Dark and Light stylesheets generated.
- [x] **Headless Runtime & Build Smoke Test**: Verified `dist/tpb-gui.exe` (51.38 MB) boot survival, `tpb-gui.exe` wrapper install, and `tpb --gui` CLI routing (live desktop window click-through pending user launch).
- [x] **Headless Fallback Test**: Verified CLI tests and missing-PySide6 hint under `tpb --gui`.
