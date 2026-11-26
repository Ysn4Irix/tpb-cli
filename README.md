# tpb-cli 🏴‍☠️

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-47%20Passed-brightgreen.svg)]()
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A fast, interactive Python CLI and automation tool for searching movies and TV series, selecting episodes/seasons across quality releases, and batch-exporting magnet links via the **apibay.org** (The Pirate Bay) backend.

---

## ✨ Features

- 🔍 **Immediate Search & Discovery**:
  - Automatically queries the backend immediately after you enter a show title.
  - Scans results upfront to determine total releases, codecs, and qualities.
- 📺 **Auto-Detected Season Selector**:
  - Analyzes search results to detect all available seasons.
  - Displays episode counts and complete pack counts for each season (e.g., `Season 1 (10 episodes, 3 packs)`), eliminating guesswork.
- 🌐 **Series Disambiguation**:
  - Automatically identifies regional variants (e.g., *The Office US* vs *The Office UK*) and prompts you to select the exact version you want.
- 🎛️ **Multi-Quality Episode Picker**:
  - Groups results by episode number (`E01`, `E02`, ...).
  - Pre-selects the healthiest release per episode by default.
  - Allows switching or selecting alternate qualities (`1080p`, `720p`, `2160p / 4K`, SD, `x265`, `x264`) directly from an interactive checklist.
- 📦 **Season Packs vs Individual Episodes**:
  - Detects full season packs and lets you grab a complete pack in one click or pick and choose individual episodes.
- 🎬 **Movie Search & High-Quality Filters**:
  - Fast search with rich metadata tables (seeders, leechers, file size, codec, VIP/Trusted uploader tags).
- ⚡ **Zero-Lag Back Navigation**:
  - Press `Esc`, `b`, `q`, or `←` at any step to instantly return to the previous screen (configured with sub-10ms key sequence timeouts).
  - In-memory query caching ensures backing up doesn't repeat slow network requests.
- 💾 **Smart Export Workflows**:
  - Save magnet links to text files (`.txt`) with pre-filled smart filenames (e.g., `breaking_bad_S01_magnets.txt`).
  - File collision resolution: overwrite or append to existing link lists.
  - Print links directly to the terminal or both save and print.
  - High-reliability public trackers are automatically embedded in generated magnet links.
- 🛡️ **Scriptable & Resilient**:
  - Run interactively (TUI) or automate batch exports using CLI flags.
  - Custom proxy support (HTTP / SOCKS5) and custom API base URLs.
  - CP1252-safe console rendering for Windows terminals.

---

## 🚀 Installation

### Prerequisites
- Python 3.10 or higher
- Git

### Option 1: Direct Install via pip (Recommended)

Install the lightweight CLI directly from GitHub:

```bash
pip install git+https://github.com/Ysn4Irix/tpb-cli.git
```

Or include the optional **PySide6 Desktop GUI** (`[gui]` extra):

```bash
pip install "tpb-cli[gui] @ git+https://github.com/Ysn4Irix/tpb-cli.git"
```

Or install from a pre-built wheel:
```bash
pip install tpb_cli-0.4.0-py3-none-any.whl
```

### Option 2: Local / Development Install

```bash
# Clone the repository
git clone https://github.com/Ysn4Irix/tpb-cli.git
cd tpb-cli

# Install CLI + GUI + dev/packaging dependencies in editable mode
pip install -e ".[gui,dev]"
```

After installation, `tpb` (CLI) and `tpb-gui` (Desktop GUI, when `[gui]` is installed) are available in your terminal.

---

## 🖥️ Desktop GUI Mode

Launch the native desktop window (`PySide6`):

```bash
tpb-gui
# or via CLI flag:
tpb --gui
```

### Desktop GUI Highlights
- **TV Series Browser**: Regional disambiguation chips (`US`, `UK`, `All`), auto-detected Season list with episode & pack counts, Season Packs table, and an interactive Episode Quality Matrix (all results start unchecked by default, with a one-click Select Recommended action and automatic single-quality switching per episode).
- **Movies & General Search**: Live-filterable and numerically sortable release table with VIP/Trusted uploader tags and resolution/codec indicators.
- **Torrent File Inspector**: Click any release to asynchronously fetch and inspect internal file paths and sizes (`ApibayClient.get_files`).
- **Batch Magnet Handoff**: Copy selected magnets to clipboard, launch staggered `magnet:` URIs in your default torrent client (with safety confirmation for large batches > 5), or export `.txt` with Overwrite/Append prompt.
- **Library & Settings**: Dark Mode (default) / Light Mode toggle (`Ctrl+T`), persistent search history & bookmarks sidebar, and Apibay mirror / HTTP & SOCKS5 proxy configuration (`Ctrl+,`).

### Building a Standalone Windows `.exe`

```powershell
.\packaging\build_exe.ps1
```

This bundles `dist\tpb-gui.exe` using PyInstaller with console suppression (`--windowed`).

---

## 📖 Usage

### 1. Interactive Mode (Default)

Simply run `tpb` without arguments:

```bash
tpb
```

Or via Python module:
```bash
python -m tpb.cli
```

#### Step-by-Step Flow:
1. **Choose Category**: Select between **TV Series**, **Movies**, or **General Search**.
2. **Enter Title**: Type in the show or movie title (e.g., `Severance`, `The Office`).
3. **Disambiguation (if applicable)**: If multiple series versions exist (e.g., US vs UK), choose your preferred version.
4. **Select Season**: Pick from auto-detected seasons with release statistics.
5. **Quality Filter**: Filter by `1080p`, `720p`, `2160p`, or `Any`.
6. **Pack or Episodes**: Grab a complete Season Pack or select individual episodes.
7. **Episode Checklist**: Use `[Space]` to toggle, `[a]` to select all, and `[Enter]` to confirm.
8. **Export**: Save to file and/or print magnet links to the terminal.

> 💡 **Navigation Tip**: Press **`Esc`**, **`b`**, **`q`**, or **`←`** anytime to jump back to the previous menu step.

---

### 2. Scriptable CLI Mode

You can automate search and export directly using CLI flags:

#### Download complete season to a text file:
```bash
tpb "Severance" -s 1 -q 1080p -o severance_s1.txt
```

#### Prefer complete season pack if available:
```bash
tpb "Breaking Bad" -s 1 --pack -o bb_s1.txt
```

#### Search movie and print top magnet link to console:
```bash
tpb "Inception" -q 1080p --print
```

#### Append search results to an existing link file:
```bash
tpb "Better Call Saul" -s 1 -q 720p -o series_links.txt
```

#### Use a custom mirror or SOCKS5 proxy:
```bash
tpb "The Matrix" --proxy "socks5://127.0.0.1:9050" --api-url "https://apibay.org"
```

---

## 🛠️ CLI Options Reference

| Flag | Long Flag | Description |
| :--- | :--- | :--- |
| `query` | | Search query string (movie or TV title). Omit to launch interactive mode. |
| `-s` | `--season` | TV Show season number (e.g. `1`, `2`). |
| `-q` | `--quality` | Resolution preference: `2160p`, `1080p`, `720p`, `480p`, or `any`. |
| `-o` | `--output` | Destination file path to save magnet links (`.txt`). |
| `-p` | `--print` | Print magnet links to terminal stdout. |
| | `--pack` | Prefer complete season pack over individual episodes. |
| `-i` | `--interactive` | Force interactive TUI even if a query argument was passed. |
| | `--gui` | Launch the PySide6 desktop GUI (`tpb-cli[gui]`). |
| | `--api-url` | Custom Apibay backend URL (Default: `https://apibay.org`). |
| | `--proxy` | HTTP or SOCKS5 proxy URL (e.g. `socks5://127.0.0.1:9050`). |
| `-v` | `--version` | Display program version and exit. |
| `-h` | `--help` | Show command line options and help message. |

---

## 📁 Project Architecture

```
tpb-cli/
├── .github/workflows/
│   ├── ci.yml             # Python lint, format, typecheck, security, tests & build
│   ├── android-ci.yml     # Android unit tests, lintDebug & debug APK build
│   └── release.yml        # Tagged release automation (.whl, .tar.gz & tpb-gui.exe)
├── android/               # Native Kotlin + Jetpack Compose + Material 3 Android app
│   ├── app/src/main/      # Search/Library/Settings screens, OkHttp client, DataStore
│   ├── app/src/test/      # JVM parser, formatter, theme, MockWebServer & ViewModel tests
│   └── app/src/androidTest/ # Compose UI instrumentation tests
├── docs/
│   ├── android-tpb-app.md # Android client architecture plan & checklist
│   ├── tpb-cli.md         # CLI design notes
│   └── tpb-desktop-gui.md # Desktop GUI implementation plan & checklist
├── tpb/
│   ├── __init__.py        # Package initialization & version metadata
│   ├── api.py             # ApibayClient, URL/proxy validation, cache lock & file normalization
│   ├── cli.py             # Argument parsing, --gui launcher & headless automation
│   ├── exporter.py        # File export, magnet formatters & Rich tables
│   ├── interactive.py     # Interactive TUI, state machine & 0ms back navigation
│   ├── models.py          # Torrent/TorrentFile dataclasses, formatting & coercion
│   ├── parser.py          # Regex parsers for seasons, episodes, quality & codecs
│   └── gui/               # Optional PySide6 desktop interface (pip install tpb-cli[gui])
│       ├── assets/        # Multi-resolution Cyan Vector Magnet PNG/ICO icons & loader
│       ├── app.py         # QApplication bootstrap & tpb-gui entrypoint
│       ├── column_state.py# Persistent interactive table & tree column widths
│       ├── main_window.py # Desktop window shell, search bar, loading & workspace states
│       ├── state.py       # Persistent settings, dark/light theme, history & bookmarks
│       ├── theme.py       # Dark & Light QSS stylesheets and palette tokens
│       ├── workers.py     # QThreadPool async workers with cancellation & stale guards
│       ├── views/         # TV Series browser & Movie/General sortable results table
│       └── widgets/       # File Inspector, Magnet ActionBar, Library drawer & Settings
├── packaging/
│   ├── tpb-gui.spec       # PyInstaller Windows --windowed spec
│   └── build_exe.ps1      # Standalone .exe build script
├── tests/
│   ├── conftest.py        # Headless QT_QPA_PLATFORM=offscreen setup
│   ├── test_api.py        # API client and response mocking tests
│   ├── test_exporter.py   # File writer & dict resilience tests
│   ├── test_gui_state.py  # GUI settings, URL validation, history, bookmarks & CLI --gui tests
│   ├── test_gui_views.py  # Offscreen Qt widget/view/action-bar tests
│   ├── test_gui_workers.py# Async worker fallback, cancellation & stale-request tests
│   ├── test_interactive.py# Navigation, series disambiguation & prompt tests
│   ├── test_models.py     # Dataclass properties & tracker verification
│   └── test_parser.py     # TV metadata extraction & episode grouping tests
├── AGENTS.md              # Project engineering, security, UI & CI/CD rules
├── CHANGELOG.md           # Keep-a-Changelog release history (SemVer)
├── pyproject.toml         # Build configuration, [gui]/[dev] extras & tool settings
├── MANIFEST.in            # Distribution manifest rules
├── requirements.txt       # Direct core runtime dependencies
└── README.md              # Project documentation
```

---

## 📱 Android Client (`android/`)

A native Android companion app built with **Kotlin, Jetpack Compose, Material 3, OkHttp, Kotlinx Serialization, and Jetpack DataStore** (`minSdk 26`, `compileSdk 35`):

- **Feature Parity**: TV Series Browser (`US`/`UK` chips, Season navigator, Packs vs Multi-Quality Episodes, `Select Recommended`), filterable & sortable Movies/General search, `/f.php` File Inspector bottom sheet, `SelectionActionBar` (`Copy`, `ACTION_VIEW` `magnet:` dispatch with batch safe fallback, `.txt` export via SAF), History/Bookmarks, and custom Mirror URL + HTTP/SOCKS5 proxy settings.
- **Build & Test Locally** (from `android/`):
  ```bash
  ./gradlew testDebugUnitTest lintDebug assembleDebug
  ```

---

## 🧪 Running Tests & Quality Checks

The Python test suite covers API queries, metadata parsing, interactive TUI navigation, file exports, and offscreen PySide6 GUI workflows:

```bash
# Run Python test suite
pytest -v

# Linting, formatting, and type checks
ruff check tpb tests
ruff format --check tpb tests
mypy tpb

# Security & dependency vulnerability scans
bandit -r tpb -ll
pip-audit --skip-editable

# Android checks (inside android/)
./gradlew testDebugUnitTest lintDebug assembleDebug
```

---

## 🔄 CI/CD Pipeline & Release Process

This repository includes GitHub Actions workflows in [`.github/workflows/`](.github/workflows):

1. **Continuous Integration ([`ci.yml`](.github/workflows/ci.yml) & [`android-ci.yml`](.github/workflows/android-ci.yml))**:
   - `ci.yml` runs Python checks on pushes/PRs to `master`/`main`: `ruff format --check`, `ruff check`, `mypy`, `bandit -r tpb -ll`, `pip-audit`, cross-OS `pytest -v` (Ubuntu & Windows, Python 3.10–3.14), `python -m build`, and `twine check`.
   - `android-ci.yml` runs on changes touching `android/**`: `testDebugUnitTest`, `lintDebug`, `assembleDebug`, and uploads `app-debug.apk` under `contents: read` permissions.
2. **Release Automation ([`release.yml`](.github/workflows/release.yml))**:
   - Triggered on SemVer tags matching `v*.*.*` (for example `v0.4.0`).
   - Re-runs full lint, formatting, type, security, and cross-platform test verification before building release binaries (`tpb_cli-*.whl`, `tpb_cli-*.tar.gz`, and Windows standalone `tpb-gui.exe`).
   - Extracts matching version notes from [`CHANGELOG.md`](CHANGELOG.md) and publishes the GitHub Release under scoped `contents: write` permission.
   - Local release checklist before tagging:
     1. Bump `version` in `pyproject.toml`, `__version__` in `tpb/__init__.py`, and `versionName` in `android/app/build.gradle.kts` (`MAJOR.MINOR.PATCH`).
     2. Update `CHANGELOG.md` and commit with a Conventional Commit (e.g., `chore(release): prepare v0.4.0`).
     3. Wait for all CI checks to pass before creating and pushing a `vX.Y.Z` tag.

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!
1. Fork the project.
2. Create your feature branch (`git checkout -b feature/amazing-feature`).
3. Commit your changes (`git commit -m "feat: add amazing feature"`).
4. Run tests (`pytest -v`).
5. Push to the branch (`git push origin feature/amazing-feature`).
6. Open a Pull Request.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
