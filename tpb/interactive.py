"""Interactive TUI / terminal workflow using InquirerPy and Rich with high-speed go-back support."""

import sys
from pathlib import Path
from typing import Any
from collections.abc import Sequence

import prompt_toolkit.application.application
from InquirerPy import inquirer
from InquirerPy.base.control import Choice, InquirerPyUIListControl
from InquirerPy.separator import Separator
from InquirerPy.utils import InquirerPyKeybindings
from rich.console import Console
from rich.panel import Panel

# Reduce Escape key and multi-key timeouts from 500ms/1000ms down to 5ms for instant responsiveness
_orig_app_init = prompt_toolkit.application.application.Application.__init__


def _fast_app_init(self, *args, **kwargs):
    _orig_app_init(self, *args, **kwargs)
    self.ttimeoutlen = 0.005  # 5ms escape sequence timeout
    self.timeoutlen = 0.005  # 5ms key sequence timeout


# Upstream prompt_toolkit workaround; method assignment triggers mypy [method-assign].
prompt_toolkit.application.application.Application.__init__ = _fast_app_init  # type: ignore[method-assign]

# Patch InquirerPy Choice handling: avoid dataclasses.asdict(choice) which recursively
# decomposes nested dataclass instances (like Torrent) into plain dicts.
_orig_get_choices = InquirerPyUIListControl._get_choices


def _safe_get_choices(self, choices, default):
    if isinstance(choices, list):
        choices = [
            {"name": ch.name, "value": ch.value, "enabled": ch.enabled}
            if isinstance(ch, Choice)
            else ch
            for ch in choices
        ]
    return _orig_get_choices(self, choices, default)


# Upstream InquirerPy workaround to preserve Torrent dataclass instances in Choice.value.
InquirerPyUIListControl._get_choices = _safe_get_choices  # type: ignore[method-assign]

from tpb.api import ApibayClient, ApibayError, CAT_TV_HD, CAT_MOVIES_HD, CAT_ALL
from tpb.models import Torrent, ensure_torrents, sanitize_filename
from tpb.parser import (
    filter_and_group_episodes,
    get_season_packs,
    get_episode_quality_variants,
    get_detected_seasons_summary,
    detect_series_variants,
)
from tpb.exporter import render_torrents_table, render_magnet_list, export_magnets_to_file

console = Console()

# Instant keybindings (0ms delay for single keys like 'b', 'q', 'left' and 10ms for 'escape')
SELECT_BACK_KEYBINDINGS: InquirerPyKeybindings = {
    "skip": [
        {"key": "escape"},
        {"key": "c-c"},
        {"key": "b"},
        {"key": "q"},
        {"key": "left"},
    ]
}

CHECKBOX_BACK_KEYBINDINGS: InquirerPyKeybindings = {
    "skip": [
        {"key": "escape"},
        {"key": "c-c"},
        {"key": "b"},
        {"key": "q"},
        {"key": "left"},
    ]
}

TEXT_BACK_KEYBINDINGS: InquirerPyKeybindings = {
    "skip": [
        {"key": "escape"},
        {"key": "c-c"},
        {"key": "c-b"},
    ]
}


# sanitize_filename is shared via tpb.models and re-exported here for compatibility.


def is_back(val: Any) -> bool:
    """Check if the user requested to go back via keybinding or text command."""
    if val is None:
        return True
    if isinstance(val, str) and val.strip().lower() in ("b", "back", ":b", "q", "quit"):
        return True
    if val == "back":
        return True
    return False


class InteractiveSession:
    """Manages the interactive terminal session flow with full go-back support."""

    def __init__(self, client: ApibayClient | None = None):
        self.client = client or ApibayClient()

    def run(self) -> None:
        """Main entry point for interactive wizard."""
        console.print(
            Panel.fit(
                "[bold cyan]TPB / Apibay Interactive CLI[/bold cyan]\n"
                "[dim]Search movies & TV series, grab magnet links, and batch export seasons.\n"
                "Navigation: Press [Esc], [b], or [← Left Arrow] to instantly go back to the previous screen.[/dim]",
                border_style="cyan",
            )
        )

        try:
            while True:
                mode = inquirer.select(
                    message="What would you like to search for?",
                    choices=[
                        Choice("tv", "📺 TV Series (Season / Episodes batch)"),
                        Choice("movie", "🎬 Movies (Search & pick magnet)"),
                        Choice("general", "🔍 General Search (All categories)"),
                        Separator(),
                        Choice("exit", "❌ Exit"),
                    ],
                    default="tv",
                    mandatory=False,
                    keybindings=SELECT_BACK_KEYBINDINGS,
                ).execute()

                if is_back(mode) or mode == "exit":
                    console.print("[dim]Goodbye![/dim]")
                    break

                if mode == "tv":
                    self.handle_tv_flow()
                elif mode == "movie":
                    self.handle_movie_flow()
                elif mode == "general":
                    self.handle_general_flow()

                console.print()

        except KeyboardInterrupt:
            console.print("\n[yellow]Operation cancelled by user. Goodbye![/yellow]")
            sys.exit(0)

    def handle_tv_flow(self) -> None:
        """Workflow for finding and downloading TV show seasons/episodes with instant search and auto-detected seasons."""
        step = 1
        show_name = ""
        season_num = 1
        quality_pref = "1080p"
        all_torrents: list[Torrent] = []
        filtered_torrents: list[Torrent] = []
        series_variants: dict = {}
        season_packs: list[Torrent] = []
        episodes_map: dict = {}
        selected_torrents: list[Torrent] = []
        selection_source: str = "episodes"

        while True:
            if step == 1:
                # Step 1: Show title
                val = inquirer.text(
                    message="Enter TV show title (e.g. Severance, Breaking Bad, The Office):",
                    default=show_name,
                    instruction="(Esc, 'b', or 'q': go back)",
                    mandatory=False,
                    keybindings=TEXT_BACK_KEYBINDINGS,
                ).execute()

                if is_back(val):
                    return  # Instantly return to main menu

                val_clean = val.strip()
                if not val_clean:
                    console.print("[red]Please enter a valid TV show title.[/red]")
                    continue

                show_name = val_clean
                step = 2

            elif step == 2:
                # Step 2: Immediate Search & Result Discovery (uses in-memory cache)
                cache_key_hd = (show_name.lower(), CAT_TV_HD)
                cache_key_all = (show_name.lower(), "")
                if cache_key_hd in self.client._cache:
                    all_torrents = self.client.search(show_name, category=CAT_TV_HD)
                elif cache_key_all in self.client._cache:
                    all_torrents = self.client.search(show_name)
                else:
                    with console.status(
                        f"[cyan]Searching Apibay for '[bold]{show_name}[/bold]'...[/cyan]",
                        spinner="dots",
                    ):
                        try:
                            all_torrents = self.client.search(show_name, category=CAT_TV_HD)
                            if not all_torrents:
                                all_torrents = self.client.search(show_name)
                        except ApibayError as err:
                            console.print(f"[bold red]Search Error:[/] {err}")
                            step = 1
                            continue

                if not all_torrents:
                    console.print(f"[yellow]No results found on Apibay for '{show_name}'.[/yellow]")
                    step = 1
                    continue

                # Check if multiple series variants are detected (e.g. US vs UK)
                series_variants = detect_series_variants(all_torrents)
                if series_variants:
                    step = 25  # Series Disambiguation
                else:
                    filtered_torrents = all_torrents
                    step = 3  # Auto-Detected Seasons Selector

            elif step == 25:
                # Step 25: Series Disambiguation (e.g. The Office US vs UK)
                sorted_variants = sorted(series_variants.items())
                variant_choices: list[Choice | Separator] = [
                    Choice(tag, f"📺 {show_name} ({tag}) [{len(v_list)} releases]")
                    for tag, v_list in sorted_variants
                ]
                variant_choices.append(
                    Choice("all", f"🌐 All / Mixed versions [{len(all_torrents)} releases]")
                )
                variant_choices.append(Separator())
                variant_choices.append(Choice("back", "⬅️ Go Back [b / Esc / ←]"))

                console.print(
                    f"\n[cyan][INFO] Multiple series versions detected for '{show_name}'.[/cyan]"
                )
                v_choice = inquirer.select(
                    message="Select which series version you want:",
                    choices=variant_choices,
                    default=sorted_variants[0][0],
                    instruction="(b / Esc / ←: go back)",
                    mandatory=False,
                    keybindings=SELECT_BACK_KEYBINDINGS,
                ).execute()

                if is_back(v_choice):
                    step = 1
                    continue

                if v_choice != "all" and v_choice in series_variants:
                    filtered_torrents = series_variants[v_choice]
                else:
                    filtered_torrents = all_torrents

                step = 3

            elif step == 3:
                # Step 3: Interactive Season Selector (Auto-Detected from Search Results)
                seasons_summary = get_detected_seasons_summary(filtered_torrents)

                if seasons_summary:
                    season_choices: list[Choice | Separator] = []
                    for s_num, s_info in seasons_summary.items():
                        eps_n = len(s_info["episodes"])
                        packs_n = len(s_info["packs"])
                        tot_n = s_info["total_torrents"]
                        desc_parts = []
                        if eps_n:
                            desc_parts.append(f"{eps_n} episode{'s' if eps_n > 1 else ''}")
                        if packs_n:
                            desc_parts.append(f"{packs_n} pack{'s' if packs_n > 1 else ''}")
                        if not desc_parts:
                            desc_parts.append(f"{tot_n} release{'s' if tot_n > 1 else ''}")
                        desc_str = f" ({', '.join(desc_parts)})"
                        season_choices.append(Choice(s_num, f"📺 Season {s_num}{desc_str}"))

                    season_choices.append(Separator())
                    season_choices.append(
                        Choice("manual", "✏️ Enter another season number manually")
                    )
                    season_choices.append(Choice("back", "⬅️ Go Back [b / Esc / ←]"))

                    console.print(
                        f"\n[bold green][OK] Found {len(filtered_torrents)} releases across "
                        f"{len(seasons_summary)} detected season(s) for '{show_name}':[/bold green]"
                    )

                    default_season = (
                        season_num
                        if season_num in seasons_summary
                        else next(iter(seasons_summary.keys()))
                    )
                    s_choice = inquirer.select(
                        message="Select Season:",
                        choices=season_choices,
                        default=default_season,
                        instruction="(b / Esc / ←: go back)",
                        mandatory=False,
                        keybindings=SELECT_BACK_KEYBINDINGS,
                    ).execute()

                    if is_back(s_choice):
                        step = 25 if series_variants else 1
                        continue

                    if s_choice == "manual":
                        val = inquirer.text(
                            message="Enter Season number:",
                            default=str(season_num),
                            instruction="(Esc, 'b', or 'q': go back)",
                            mandatory=False,
                            keybindings=TEXT_BACK_KEYBINDINGS,
                        ).execute()

                        if is_back(val):
                            continue  # Re-prompt season selector

                        if not val.strip().isdigit() or int(val.strip()) <= 0:
                            console.print("[red]Please enter a valid positive number.[/red]")
                            continue

                        season_num = int(val.strip())
                    else:
                        season_num = int(s_choice)

                    step = 4

                else:
                    # No structured seasons detected
                    console.print(
                        f"[yellow]Could not automatically detect standard season tags in {len(filtered_torrents)} releases for '{show_name}'.[/yellow]"
                    )
                    no_s_choices = [
                        Choice("manual", "✏️ Enter season number manually"),
                        Choice("browse", "📋 Browse all releases for manual selection"),
                        Separator(),
                        Choice("back", "⬅️ Go Back [b / Esc / ←]"),
                    ]
                    s_choice = inquirer.select(
                        message="How would you like to proceed?",
                        choices=no_s_choices,
                        instruction="(b / Esc / ←: go back)",
                        mandatory=False,
                        keybindings=SELECT_BACK_KEYBINDINGS,
                    ).execute()

                    if is_back(s_choice):
                        step = 25 if series_variants else 1
                        continue

                    if s_choice == "browse":
                        render_torrents_table(
                            filtered_torrents[:25], title=f"All Results for '{show_name}'"
                        )
                        step = 7  # Manual multi-select
                    else:
                        val = inquirer.text(
                            message="Enter Season number:",
                            default=str(season_num),
                            instruction="(Esc, 'b', or 'q': go back)",
                            mandatory=False,
                            keybindings=TEXT_BACK_KEYBINDINGS,
                        ).execute()

                        if is_back(val):
                            continue

                        if not val.strip().isdigit() or int(val.strip()) <= 0:
                            console.print("[red]Please enter a valid positive number.[/red]")
                            continue

                        season_num = int(val.strip())
                        step = 4

            elif step == 4:
                # Step 4: Quality preference
                val = inquirer.select(
                    message=f"Select preferred quality for Season {season_num}:",
                    choices=[
                        Choice("Any", "✨ Any Quality (Best seeded)"),
                        Choice("1080p", "💎 1080p (Full HD)"),
                        Choice("720p", "📺 720p (HD)"),
                        Choice("2160p", "🔥 2160p / 4K (Ultra HD)"),
                        Choice("480p", "📼 480p / SD"),
                        Separator(),
                        Choice("back", "⬅️ Go Back [b / Esc / ←]"),
                    ],
                    default=quality_pref,
                    instruction="(b / Esc / ←: go back)",
                    mandatory=False,
                    keybindings=SELECT_BACK_KEYBINDINGS,
                ).execute()

                if is_back(val):
                    step = 3
                    continue

                quality_pref = val

                # Resolve packs and episodes
                season_packs = get_season_packs(filtered_torrents, season_num)
                episodes_map = filter_and_group_episodes(
                    filtered_torrents,
                    target_season=season_num,
                    preferred_quality=None if quality_pref == "Any" else quality_pref,
                )

                if season_packs:
                    console.print(
                        f"\n[green][OK] Found {len(season_packs)} complete Season {season_num} pack(s)![/green]"
                    )
                    step = 5  # Prompt pack vs episodes
                elif episodes_map:
                    step = 6  # Directly to episode selector
                else:
                    console.print(
                        f"[yellow]Could not find specific Season {season_num} episodes for '{show_name}'.[/yellow]\n"
                        f"[dim]Tip: Showing all search results so you can manually select releases:[/dim]"
                    )
                    render_torrents_table(
                        filtered_torrents[:20], title=f"All Results for '{show_name}'"
                    )
                    step = 7  # Manual multi-select

            elif step == 5:
                # Step 5: Choose between Pack and Individual Episodes
                choice_type = inquirer.select(
                    message=f"How would you like to grab Season {season_num}?",
                    choices=[
                        Choice(
                            "episodes",
                            f"📋 Select individual episodes ({len(episodes_map)} episode numbers detected)",
                        ),
                        Choice(
                            "pack",
                            f"📦 Grab a complete Season {season_num} pack ({season_packs[0].human_size})",
                        ),
                        Separator(),
                        Choice("back", "⬅️ Go Back [b / Esc / ←]"),
                    ]
                    if episodes_map
                    else [
                        Choice(
                            "pack",
                            f"📦 Grab a complete Season {season_num} pack ({season_packs[0].human_size})",
                        ),
                        Separator(),
                        Choice("back", "⬅️ Go Back [b / Esc / ←]"),
                    ],
                    default="episodes" if episodes_map else "pack",
                    instruction="(b / Esc / ←: go back)",
                    mandatory=False,
                    keybindings=SELECT_BACK_KEYBINDINGS,
                ).execute()

                if is_back(choice_type):
                    step = 4  # Return to quality preference
                    continue

                if choice_type == "pack":
                    step = 8  # Go to pack selector
                else:
                    step = 6  # Go to episode selector

            elif step == 6:
                # Step 6: Select individual episodes
                res = self._select_episodes_flow(episodes_map, show_name, season_num)
                if is_back(res):
                    step = 5 if season_packs else 4
                    continue

                if not res:
                    console.print("[yellow]No episodes selected.[/yellow]")
                    continue

                selected_torrents = ensure_torrents(res)
                selection_source = "episodes"
                step = 9  # Export

            elif step == 7:
                # Step 7: Manual multi-select
                res = self._manual_multi_select(filtered_torrents[:20])
                if is_back(res):
                    step = 4
                    continue

                if not res:
                    console.print("[yellow]No torrents selected.[/yellow]")
                    continue

                selected_torrents = ensure_torrents(res)
                selection_source = "manual"
                step = 9  # Export

            elif step == 8:
                # Step 8: Select specific Season Pack
                pack_choices: list[Choice | Separator] = [
                    Choice(
                        p,
                        name=f"{p.name} ({p.quality}, {p.human_size}, {p.seeders} seeds, uploader: {p.username})",
                    )
                    for p in season_packs[:8]
                ]
                pack_choices.extend([Separator(), Choice("back", "⬅️ Go Back [b / Esc / ←]")])

                chosen_pack = inquirer.select(
                    message="Select Season Pack:",
                    choices=pack_choices,
                    instruction="(b / Esc / ←: go back)",
                    mandatory=False,
                    keybindings=SELECT_BACK_KEYBINDINGS,
                ).execute()

                if is_back(chosen_pack):
                    step = 5
                    continue

                selected_torrents = ensure_torrents([chosen_pack])
                selection_source = "pack"
                step = 9  # Export

            elif step == 9:
                # Step 9: Export destination workflow
                default_filename = f"{sanitize_filename(show_name)}_S{season_num:02d}_magnets.txt"
                completed = self._export_workflow(
                    selected_torrents, default_filename=default_filename
                )
                if completed:
                    break
                else:
                    # User went back from export: return directly to their selection step!
                    if selection_source == "pack":
                        step = 8
                    elif selection_source == "episodes":
                        step = 6
                    else:
                        step = 7

    def _select_episodes_flow(
        self,
        episodes_map: dict,
        show_name: str,
        season_num: int,
    ) -> list[Torrent] | None:
        """Allow user to review and check/uncheck episodes and pick between different quality variants."""
        choices: list[Choice | Separator] = []
        total_eps = len(episodes_map)

        for ep_num in sorted(episodes_map.keys()):
            candidates = episodes_map[ep_num]
            variants = get_episode_quality_variants(candidates)

            sep_text = f"-- Episode {ep_num:02d} ({len(variants)} quality option{'s' if len(variants) > 1 else ''}) --"
            choices.append(Separator(sep_text))

            for idx, variant in enumerate(variants):
                is_default = idx == 0
                default_tag = " [Default]" if is_default else ""
                codec_tag = f" | {variant.codec}" if variant.codec != "Unknown" else ""
                label = (
                    f"E{ep_num:02d} [{variant.quality}{codec_tag}] {variant.name} "
                    f"[{variant.human_size} | {variant.seeders} seeds]{default_tag}"
                )
                choices.append(Choice(variant, name=label, enabled=is_default))

        console.print(
            f"\n[bold cyan]Found {total_eps} episode(s) for {show_name} Season {season_num}:[/bold cyan]"
        )
        console.print(
            "[dim]* Top release per episode is pre-checked [X] by default.\n"
            "* Different quality options are listed underneath -- use [Spacebar] to switch/toggle.\n"
            "* Press [a] to toggle all, [Enter] to confirm, or [b / Esc / <-] to Go Back.[/dim]"
        )

        selected = inquirer.checkbox(
            message=f"Select episodes & qualities to include in export ({total_eps} episodes):",
            choices=choices,
            instruction="(Space: toggle, a: all, Enter: confirm, b/Esc/←: Go Back)",
            mandatory=False,
            keybindings=CHECKBOX_BACK_KEYBINDINGS,
        ).execute()

        if is_back(selected):
            return None

        return selected or []

    def _manual_multi_select(self, torrents: list[Torrent]) -> list[Torrent] | None:
        """Manual checkbox selection from a list of torrents."""
        choices = [
            Choice(
                t,
                name=f"{t.name} [{t.quality}, {t.human_size}, {t.seeders} seeds]",
                enabled=False,
            )
            for t in torrents
        ]
        selected = inquirer.checkbox(
            message="Check off the torrents you want:",
            choices=choices,
            instruction="(Space: toggle, Enter: confirm, b/Esc/←: Go Back)",
            mandatory=False,
            keybindings=CHECKBOX_BACK_KEYBINDINGS,
        ).execute()

        if is_back(selected):
            return None

        return selected or []

    def handle_movie_flow(self) -> None:
        """Workflow for searching movies with fast back navigation."""
        step = 1
        movie_title = ""
        torrents: list[Torrent] = []
        selected: list[Torrent] = []

        while True:
            if step == 1:
                val = inquirer.text(
                    message="Enter movie title:",
                    default=movie_title,
                    instruction="(Esc, 'b', or 'q': go back)",
                    mandatory=False,
                    keybindings=TEXT_BACK_KEYBINDINGS,
                ).execute()

                if is_back(val):
                    return  # Instantly return to main menu

                val_clean = val.strip()
                if not val_clean:
                    console.print("[red]Please enter a valid movie title.[/red]")
                    continue

                movie_title = val_clean
                step = 2

            elif step == 2:
                cache_key_hd = (movie_title.lower(), CAT_MOVIES_HD)
                cache_key_all = (movie_title.lower(), "")
                if cache_key_hd in self.client._cache:
                    torrents = self.client.search(movie_title, category=CAT_MOVIES_HD)
                elif cache_key_all in self.client._cache:
                    torrents = self.client.search(movie_title)
                else:
                    with console.status(
                        f"[cyan]Searching Apibay for '[bold]{movie_title}[/bold]'...[/cyan]",
                        spinner="dots",
                    ):
                        try:
                            torrents = self.client.search(movie_title, category=CAT_MOVIES_HD)
                            if not torrents:
                                torrents = self.client.search(movie_title)
                        except ApibayError as err:
                            console.print(f"[bold red]Search Error:[/] {err}")
                            step = 1
                            continue

                if not torrents:
                    console.print(f"[yellow]No movie releases found for '{movie_title}'.[/yellow]")
                    step = 1
                    continue

                render_torrents_table(torrents[:25], title=f"Results for '{movie_title}'")
                step = 3

            elif step == 3:
                res = self._manual_multi_select(torrents[:25])
                if is_back(res):
                    step = 1
                    continue

                if not res:
                    console.print("[yellow]No items selected.[/yellow]")
                    continue

                selected = ensure_torrents(res)
                step = 4

            elif step == 4:
                default_filename = f"{sanitize_filename(movie_title)}_magnets.txt"
                completed = self._export_workflow(selected, default_filename=default_filename)
                if completed:
                    break
                else:
                    # Going back from export returns directly to selection prompt without re-fetching
                    step = 3

    def handle_general_flow(self) -> None:
        """Workflow for general search across all categories with fast back navigation."""
        step = 1
        query = ""
        torrents: list[Torrent] = []
        selected: list[Torrent] = []

        while True:
            if step == 1:
                val = inquirer.text(
                    message="Enter search query:",
                    default=query,
                    instruction="(Esc, 'b', or 'q': go back)",
                    mandatory=False,
                    keybindings=TEXT_BACK_KEYBINDINGS,
                ).execute()

                if is_back(val):
                    return  # Instantly return to main menu

                val_clean = val.strip()
                if not val_clean:
                    console.print("[red]Please enter a valid search query.[/red]")
                    continue

                query = val_clean
                step = 2

            elif step == 2:
                cache_key = (query.lower(), CAT_ALL)
                if cache_key in self.client._cache:
                    torrents = self.client.search(query, category=CAT_ALL)
                else:
                    with console.status(
                        f"[cyan]Searching Apibay for '[bold]{query}[/bold]'...[/cyan]",
                        spinner="dots",
                    ):
                        try:
                            torrents = self.client.search(query, category=CAT_ALL)
                        except ApibayError as err:
                            console.print(f"[bold red]Search Error:[/] {err}")
                            step = 1
                            continue

                if not torrents:
                    console.print(f"[yellow]No results found for '{query}'.[/yellow]")
                    step = 1
                    continue

                render_torrents_table(torrents[:30], title=f"Results for '{query}'")
                step = 3

            elif step == 3:
                res = self._manual_multi_select(torrents[:30])
                if is_back(res):
                    step = 1
                    continue

                if not res:
                    console.print("[yellow]No items selected.[/yellow]")
                    continue

                selected = ensure_torrents(res)
                step = 4

            elif step == 4:
                default_filename = f"{sanitize_filename(query)}_magnets.txt"
                completed = self._export_workflow(selected, default_filename=default_filename)
                if completed:
                    break
                else:
                    step = 3

    def _export_workflow(self, torrents: Sequence[Any], default_filename: str) -> bool:
        """
        Handles export actions: Save to file and/or print to console (P2: B, Edge 1: A).
        Returns True if export completed, False if user chose to Go Back.
        """
        torrents = ensure_torrents(torrents)
        if not torrents:
            console.print("[yellow]No torrents provided for export.[/yellow]")
            return False

        action = inquirer.select(
            message="Choose output action:",
            choices=[
                Choice("file", "💾 Save magnet links to text file"),
                Choice("console", "🖥️ Print magnet links to console"),
                Choice("both", "✨ Both (Save to text file & Print to console)"),
                Separator(),
                Choice("back", "⬅️ Go Back [b / Esc / ←]"),
            ],
            default="file",
            instruction="(b / Esc / ←: go back)",
            mandatory=False,
            keybindings=SELECT_BACK_KEYBINDINGS,
        ).execute()

        if is_back(action):
            return False

        if action in ("file", "both"):
            # Prompt user with smart default filename (Edge Case 1: Option A)
            file_str = inquirer.text(
                message="Enter destination filename / path:",
                default=default_filename,
                instruction="(Esc, 'b', or 'q': go back)",
                mandatory=False,
                keybindings=TEXT_BACK_KEYBINDINGS,
            ).execute()

            if is_back(file_str):
                return False

            dest_path = Path(file_str.strip())
            append_mode = False

            if dest_path.exists():
                conflict_action = inquirer.select(
                    message=f"File '{dest_path.name}' already exists. What would you like to do?",
                    choices=[
                        Choice("overwrite", "🔄 Overwrite existing file"),
                        Choice("append", "➕ Append magnet links to file"),
                        Choice("cancel", "🚫 Cancel file save [b / Esc / ←]"),
                    ],
                    default="overwrite",
                    instruction="(b / Esc / ←: cancel)",
                    mandatory=False,
                    keybindings=SELECT_BACK_KEYBINDINGS,
                ).execute()

                if is_back(conflict_action) or conflict_action == "cancel":
                    console.print("[yellow]File save cancelled.[/yellow]")
                    return False
                else:
                    append_mode = conflict_action == "append"
                    count = export_magnets_to_file(torrents, dest_path, append=append_mode)
                    console.print(
                        f"[bold green][OK] Successfully exported {count} magnet link(s) to '{dest_path.resolve()}'![/bold green]"
                    )
            else:
                count = export_magnets_to_file(torrents, dest_path, append=False)
                console.print(
                    f"[bold green][OK] Successfully exported {count} magnet link(s) to '{dest_path.resolve()}'![/bold green]"
                )

        if action in ("console", "both"):
            render_magnet_list(torrents)

        return True
