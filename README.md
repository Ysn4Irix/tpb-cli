# tpb-cli 🏴‍☠️

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-24%20Passed-brightgreen.svg)]()
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

Install directly from GitHub with a single command:

```bash
pip install git+https://github.com/Ysn4Irix/tpb-cli.git
```

Or install from a pre-built wheel:
```bash
pip install tpb_cli-0.1.0-py3-none-any.whl
```

### Option 2: Local / Development Install

```bash
# Clone the repository
git clone https://github.com/Ysn4Irix/tpb-cli.git
cd tpb-cli

# Install in editable mode for development
pip install -e .
```

After installation, the `tpb` executable command will be immediately available in your terminal.

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
| | `--api-url` | Custom Apibay backend URL (Default: `https://apibay.org`). |
| | `--proxy` | HTTP or SOCKS5 proxy URL (e.g. `socks5://127.0.0.1:9050`). |
| `-v` | `--version` | Display program version and exit. |
| `-h` | `--help` | Show command line options and help message. |

---

## 📁 Project Architecture

```
tpb-cli/
├── tpb/
│   ├── __init__.py        # Package initialization & version metadata
│   ├── api.py             # ApibayClient, HTTP requests, caching & error handling
│   ├── cli.py             # Argument parsing and headless automation entrypoint
│   ├── exporter.py        # File export, magnet formatters & Rich tables
│   ├── interactive.py     # Interactive TUI, state machine & 0ms back navigation
│   ├── models.py          # Torrent dataclass, properties & model coercion
│   └── parser.py          # Regex parsers for seasons, episodes, quality & codecs
├── tests/
│   ├── test_api.py        # API client and response mocking tests
│   ├── test_exporter.py   # File writer & dict resilience tests
│   ├── test_interactive.py# Navigation, series disambiguation & prompt tests
│   ├── test_models.py     # Dataclass properties & tracker verification
│   └── test_parser.py     # TV metadata extraction & episode grouping tests
├── pyproject.toml         # Build configuration & dependencies
├── requirements.txt       # Direct runtime dependencies
└── README.md              # Project documentation
```

---

## 🧪 Running Tests

The test suite contains 24 automated unit tests covering API queries, metadata parsing, interactive state transitions, and file exports:

```bash
pytest -v
```

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
