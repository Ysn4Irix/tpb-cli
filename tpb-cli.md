# TPB / Apibay CLI (`tpb-cli`)

## Goal
Build a hybrid interactive Python CLI application to search movies and TV series via the `apibay.org` API, interactively select and batch-export magnet links (especially entire seasons) to text files or terminal output.

## Tech Stack & Architecture
- **Language**: Python 3.10+
- **CLI & TUI**: `rich` (tables, progress spinners, colorized output) + `InquirerPy` (fuzzy search, arrow-key navigation, multi-select checkboxes for episodes) + `argparse` (flag-based scripting)
- **HTTP Client**: `httpx` (with custom User-Agent, configurable timeout, and proxy/mirror support)
- **Project Structure**:
  - `tpb/api.py`: Apibay client (querying, category filtering, magnet link generation with tracker announce list)
  - `tpb/parser.py`: Season/Episode regex parser, size humanizer, torrent health sorter
  - `tpb/interactive.py`: InquirerPy interactive menus (search prompt, multi-select episode selector, export options)
  - `tpb/cli.py`: Entrypoint with hybrid mode (CLI flags vs interactive prompt)
  - `tpb/exporter.py`: File writing (`.txt` magnet lists) and console printing

## Tasks
- [x] Task 1: Initialize project setup and requirements (`requirements.txt`, `pyproject.toml`) → Verify: `pip install -r requirements.txt` succeeds.
- [x] Task 2: Implement `tpb/api.py` to query `apibay.org` and construct tracker-enriched magnet URLs → Verify: Run unit test querying a known show and receiving valid magnet URIs.
- [x] Task 3: Implement `tpb/parser.py` to parse episode numbers (`S01E01`, `1x01`) and format sizes/status → Verify: Parse test release strings correctly into season/episode metadata.
- [x] Task 4: Implement `tpb/exporter.py` to save magnet links to text files and print formatted console outputs → Verify: Export output generates formatted file on disk.
- [x] Task 5: Implement `tpb/interactive.py` with multi-select episode checkboxes and rich tables → Verify: Test interactive navigation in terminal.
- [x] Task 6: Implement `tpb/cli.py` integrating hybrid CLI flags (`--search`, `--season`, `--output`) and interactive launcher → Verify: Both scripted flag runs and interactive runs execute cleanly.
- [x] Task 7: End-to-end verification and error handling tests (empty results, connection error, invalid inputs) → Verify: Graceful messages without raw stack traces.

## Done When
- [x] User can search movies/shows interactively or via CLI flags.
- [x] User can inspect TV series episodes for a season and multi-select which episodes to download.
- [x] Magnet links are generated with standard trackers and saved to the target `.txt` file or printed to console.
- [x] Zero unhandled API/network exceptions on blocked connections or missing torrents.

## Notes
- Apibay returns a single dummy object `[{"name": "No results returned", "id": "0", ...}]` when 0 hits occur; explicitly handled.
- Trackers include standard high-uptime public trackers (`opentrackr`, `openbittorrent`, etc.) so magnets resolve immediately in any client.
- Windows CP1252-safe output handling prevents Unicode encoding crashes on classic consoles.
- Option A implemented: Immediate Apibay query after title input with auto-detected seasons menu, regional disambiguation (e.g. US vs UK), and instant 0ms back navigation.
