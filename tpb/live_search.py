"""Live real-time search interface for Apibay using prompt_toolkit."""

import shutil
import sys
import threading
from typing import Dict, List, Optional, Tuple

from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.data_structures import Size
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.output.defaults import create_output
from prompt_toolkit.output.vt100 import Vt100_Output
from prompt_toolkit.styles import Style

from tpb.api import ApibayClient, ApibayError
from tpb.models import Torrent


def get_safe_output():
    """Return platform output, falling back to Vt100_Output if no Windows console buffer exists."""
    try:
        return create_output()
    except Exception:
        cols, rows = shutil.get_terminal_size((80, 24))
        return Vt100_Output(sys.stdout, lambda: Size(rows, cols), term="xterm-256color")


class LiveSearchSession:
    """Real-time debounced live search for Apibay."""

    def __init__(
        self,
        client: Optional[ApibayClient] = None,
        category: Optional[str] = None,
        debounce_seconds: float = 0.25,
    ):
        self.client = client or ApibayClient()
        self.category = category
        self.debounce_seconds = debounce_seconds

        self.results: List[Torrent] = []
        self.selected_index: int = 0
        self.is_searching: bool = False
        self.status_message: str = "Type to search live (e.g. Severance, Inception)..."
        self.debounce_timer: Optional[threading.Timer] = None
        self.cache: Dict[str, List[Torrent]] = {}
        self.lock = threading.Lock()

        # Final result chosen by user (Torrent or None)
        self.chosen_result: Optional[Torrent] = None
        self.chosen_query: Optional[str] = None

        # Build UI layout
        self.app = self._build_application()

    def _build_application(self) -> Application:
        kb = KeyBindings()

        @kb.add("down")
        @kb.add("c-n")
        def _move_down(event):
            if self.results:
                self.selected_index = min(self.selected_index + 1, len(self.results) - 1)
                event.app.invalidate()

        @kb.add("up")
        @kb.add("c-p")
        def _move_up(event):
            if self.results:
                self.selected_index = max(self.selected_index - 1, 0)
                event.app.invalidate()

        @kb.add("pagedown")
        def _page_down(event):
            if self.results:
                self.selected_index = min(self.selected_index + 10, len(self.results) - 1)
                event.app.invalidate()

        @kb.add("pageup")
        def _page_up(event):
            if self.results:
                self.selected_index = max(self.selected_index - 10, 0)
                event.app.invalidate()

        @kb.add("enter")
        def _confirm(event):
            with self.lock:
                if self.results and 0 <= self.selected_index < len(self.results):
                    self.chosen_result = self.results[self.selected_index]
                self.chosen_query = self.query_buffer.text.strip()
            event.app.exit()

        @kb.add("escape")
        @kb.add("c-c")
        def _cancel(event):
            self.chosen_result = None
            self.chosen_query = None
            event.app.exit()

        # Query input buffer
        self.query_buffer = Buffer(
            name="query",
            on_text_changed=self._on_text_changed,
            multiline=False,
        )

        input_control = BufferControl(buffer=self.query_buffer)
        results_control = FormattedTextControl(text=self._render_results)
        status_control = FormattedTextControl(text=self._render_status)
        header_control = FormattedTextControl(text=self._render_header)

        layout = Layout(
            HSplit([
                Window(content=header_control, height=Dimension.exact(2)),
                Window(content=input_control, height=Dimension.exact(1)),
                Window(content=status_control, height=Dimension.exact(1)),
                Window(content=results_control, height=Dimension(min=5, preferred=16)),
            ])
        )

        style = Style.from_dict({
            "header.title": "bold cyan",
            "header.subtitle": "dim",
            "prompt.icon": "bold cyan",
            "status.info": "dim cyan",
            "status.searching": "bold yellow",
            "status.empty": "dim yellow",
            "col.header": "bold dim underline",
            "row.selected": "reverse bold cyan",
            "row.normal": "white",
            "row.quality": "magenta",
            "row.size": "green",
            "row.seeds": "bold green",
            "row.seeds_low": "red",
            "row.leech": "dim",
            "row.vip": "bold green",
            "row.trust": "bold magenta",
        })

        return Application(
            layout=layout,
            key_bindings=kb,
            style=style,
            output=get_safe_output(),
            full_screen=False,
        )

    def _render_header(self) -> List[Tuple[str, str]]:
        cat_label = f" [{self.category}]" if self.category else ""
        return [
            ("class:header.title", f"⚡ Live Apibay Search{cat_label}\n"),
            ("class:prompt.icon", "🔍 > "),
        ]

    def _render_status(self) -> List[Tuple[str, str]]:
        if self.is_searching:
            return [("class:status.searching", f"Searching Apibay for '{self.query_buffer.text}'...")]
        if not self.query_buffer.text.strip():
            return [("class:status.info", self.status_message)]
        if not self.results:
            return [("class:status.empty", f"No results found for '{self.query_buffer.text.strip()}'.")]

        count = len(self.results)
        curr = self.selected_index + 1
        return [
            ("class:status.info", f"Found {count} torrent(s) [Selected {curr}/{count}]  |  [↑/↓] Navigate  [Enter] Select  [Esc] Back")
        ]

    def _render_results(self) -> List[Tuple[str, str]]:
        if not self.results:
            return []

        cols, _ = shutil.get_terminal_size((80, 24))
        title_width = max(24, cols - 46)

        fragments: List[Tuple[str, str]] = [
            ("class:col.header", f"   {'Title':<{title_width}}  {'Quality':<8}  {'Size':>10}  {'Seeds':>6}  {'Leech':>5}  {'Uploader':<10}\n")
        ]

        # Window visible items around selected_index
        max_visible = 12
        total = len(self.results)
        start_idx = max(0, min(self.selected_index - max_visible // 2, total - max_visible))
        end_idx = min(total, start_idx + max_visible)

        for idx in range(start_idx, end_idx):
            t = self.results[idx]
            is_selected = (idx == self.selected_index)

            # Truncate title cleanly
            raw_title = t.name
            if len(raw_title) > title_width:
                disp_title = raw_title[: title_width - 3] + "..."
            else:
                disp_title = raw_title.ljust(title_width)

            q_str = f"{t.quality:<8}"
            size_str = f"{t.human_size:>10}"
            seeds_str = f"{t.seeders:>6}"
            leech_str = f"{t.leechers:>5}"

            uploader = t.username[:8] if t.username else "anon"
            if t.is_vip:
                up_tag = f"[VIP] {uploader}"
            elif t.is_trusted:
                up_tag = f"[TRUST] {uploader}"
            else:
                up_tag = f"      {uploader}"
            up_str = f"{up_tag:<10}"

            prefix = "❯ " if is_selected else "  "

            if is_selected:
                row_text = f"{prefix}{disp_title}  {q_str}  {size_str}  {seeds_str}  {leech_str}  {up_str}\n"
                fragments.append(("class:row.selected", row_text))
            else:
                fragments.append(("class:row.normal", f"{prefix}{disp_title}  "))
                fragments.append(("class:row.quality", f"{q_str}  "))
                fragments.append(("class:row.size", f"{size_str}  "))
                seed_style = "class:row.seeds" if t.seeders > 5 else "class:row.seeds_low"
                fragments.append((seed_style, f"{seeds_str}  "))
                fragments.append(("class:row.leech", f"{leech_str}  "))
                up_style = "class:row.vip" if t.is_vip else ("class:row.trust" if t.is_trusted else "class:row.normal")
                fragments.append((up_style, f"{up_str}\n"))

        return fragments

    def _on_text_changed(self, buffer: Buffer) -> None:
        query = buffer.text.strip()
        if not query:
            with self.lock:
                self.results = []
                self.selected_index = 0
                self.is_searching = False
                self.status_message = "Type to search live (e.g. Severance, Inception)..."
            self.app.invalidate()
            return

        # Check in-memory cache first
        cache_key = f"{query}_{self.category or ''}"
        with self.lock:
            if cache_key in self.cache:
                self.results = self.cache[cache_key]
                self.selected_index = 0
                self.is_searching = False
                self.app.invalidate()
                return

        # Debounce network requests
        if self.debounce_timer:
            self.debounce_timer.cancel()

        self.is_searching = True
        self.app.invalidate()
        self.debounce_timer = threading.Timer(self.debounce_seconds, self._perform_search, args=[query, cache_key])
        self.debounce_timer.daemon = True
        self.debounce_timer.start()

    def _perform_search(self, query: str, cache_key: str) -> None:
        try:
            results = self.client.search(query, category=self.category)
        except ApibayError:
            results = []

        with self.lock:
            self.cache[cache_key] = results
            # Only update if user hasn't changed query since request was made
            if self.query_buffer.text.strip() == query:
                self.results = results
                self.selected_index = 0
                self.is_searching = False

        self.app.invalidate()

    def run(self) -> Tuple[Optional[Torrent], Optional[str]]:
        """
        Run the live search prompt.
        Returns: (chosen_torrent, query_string)
        """
        try:
            self.app.run()
        except KeyboardInterrupt:
            return None, None
        return self.chosen_result, self.chosen_query
