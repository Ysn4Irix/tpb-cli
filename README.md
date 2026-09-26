# tpb-cli 🏴‍☠️

Interactive Python CLI application for searching movies and TV series and batch-exporting magnet links using the **apibay.org** (The Pirate Bay) API.

---

## ✨ Features

- 📺 **TV Series & Season Batch Scraper**:
  - Automatically identifies complete **Season Packs** or groups individual episodes (`E01`, `E02` ... `E24`).
  - **Quality preference filtering** (`1080p`, `720p`, `2160p/4K`, `480p`, or `Any`).
  - **Multi-Quality Episode Picker**: Displays all available qualities (1080p, 720p, 2160p, x265, etc.) under each episode section header, pre-checking the recommended one while allowing you to manually switch or select alternate qualities.
  - Auto-selects the highest-seeded release per episode with an interactive multi-select checkbox menu to review, toggle, and customize episodes.
- 🎬 **Movie Search & Selection**:
  - Search any movie title, view seeders/leechers, file size, codec, and release group in a colorized table.
- ⚡ **Hybrid Mode**:
  - **Interactive TUI**: Arrow-key menus, fuzzy search, and multi-select checkboxes when run with no arguments.
  - **Scriptable CLI Flags**: Automate batch exports directly from terminal or bash scripts.
- 💾 **Export & Output**:
  - Save to text file (`.txt`) with smart default naming (`<show_name>_S<season>_magnets.txt`) and collision handling (overwrite/append).
  - Print formatted magnet links directly to terminal.
  - Magnet links pre-populated with high-uptime public trackers for instant discovery.
- 🛡️ **Network Resilience**:
  - Custom proxy support (`--proxy HTTP/SOCKS5`) and configurable mirrors (`--api-url`).
  - Native handling for empty results and connection timeouts.

---

## 🚀 Installation

```bash
# Clone the repository
git clone https://github.com/your-username/tpb-cli.git
cd tpb-cli

# Install dependencies
pip install -r requirements.txt

# (Optional) Install in editable mode for the 'tpb' command
pip install -e .
```

---

## 📖 Usage

### 1. Interactive Mode (Default)

Simply launch `tpb`:

```bash
python -m tpb.cli
# or if installed with pip -e:
tpb
```

You will be guided through:
1. Search mode selection (TV Series, Movie, or General Search).
2. Title entry and Season number.
3. Quality preference filter (`1080p`, `720p`, `2160p`, `Any`).
4. Interactive episode selection menu (`[Space]` to toggle, `[a]` to select all, `[Enter]` to confirm).
5. Output destination (Save to file with smart name `<show>_S<season>_magnets.txt` and/or print to terminal).

---

### 2. Scripted / Automation Flags

You can bypass interactive prompts completely by passing flags:

#### Export entire season to a file:
```bash
python -m tpb.cli "Severance" -s 1 -q 1080p -o severance_s1.txt
```

#### Prefer complete season pack if available:
```bash
python -m tpb.cli "Breaking Bad" -s 1 --pack -o bb_s1.txt
```

#### Search movie and print top magnet link to console:
```bash
python -m tpb.cli "Inception" -q 1080p --print
```

#### Use a custom mirror or SOCKS5 proxy:
```bash
python -m tpb.cli "The Matrix" --proxy "socks5://127.0.0.1:9050" --api-url "https://apibay.org"
```

---

## 🛠️ CLI Options Reference

| Flag | Long Flag | Description |
|------|-----------|-------------|
| `query` | | Search query (movie or TV title). If omitted, opens interactive menu. |
| `-s` | `--season` | TV Show season number (e.g. `1`, `2`). |
| `-q` | `--quality` | Resolution filter: `2160p`, `1080p`, `720p`, `480p`, `any`. |
| `-o` | `--output` | Destination path for `.txt` magnet list. |
| `-p` | `--print` | Print magnet links to terminal. |
| | `--pack` | Prefer complete season pack if available. |
| `-i` | `--interactive` | Force interactive menu even if query is passed. |
| | `--api-url` | Custom Apibay API base URL. |
| | `--proxy` | HTTP/SOCKS5 proxy URL. |
| `-v` | `--version` | Show program version. |
| `-h` | `--help` | Display help screen. |

---

## 🧪 Running Tests

```bash
pytest -v
```

---

## 📄 License
MIT
