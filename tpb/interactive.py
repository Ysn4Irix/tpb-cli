"""Interactive TUI / terminal workflow using InquirerPy and Rich with high-speed go-back support."""

import re
import sys
from pathlib import Path
from typing import List, Optional, Any

import prompt_toolkit.application.application
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from InquirerPy.separator import Separator
from rich.console import Console
from rich.panel import Panel

# Reduce Escape key detection delay from 500ms down to 10ms for instant back navigation
_orig_app_init = prompt_toolkit.application.application.Application.__init__


def _fast_app_init(self, *args, **kwargs):
    _orig_app_init(self, *args, **kwargs)
    self.ttimeoutlen = 0.01


prompt_toolkit.application.application.Application.__init__ = _fast_app_init

from tpb.api import ApibayClient, ApibayError, CAT_TV_HD, CAT_MOVIES_HD, CAT_ALL
from tpb.models import Torrent
from tpb.parser import (
    filter_and_group_episodes,
    get_season_packs,
    detect_quality,
    get_episode_quality_variants,
)
from tpb.exporter import render_torrents_table, render_magnet_list, export_magnets_to_file

console = Console()

# Instant keybindings (0ms delay for single keys like 'b', 'q', 'left' and 10ms for 'escape')
SELECT_BACK_KEYBINDINGS = {
    "skip": [
        {"key": "escape"},
        {"key": "c-c"},
        {"key": "b"},
        {"key": "q"},
        {"key": "left"},
    ]
}

CHECKBOX_BACK_KEYBINDINGS = {
    "skip": [
        {"key": "escape"},
        {"key": "c-c"},
        {"key": "b"},
        {"key": "q"},
        {"key": "left"},
    ]
}

TEXT_BACK_KEYBINDINGS = {
    "skip": [
        {"key": "escape"},
        {"key": "c-c"},
        {"key": "c-b"},
    ]
}


def sanitize_filename(name: str) -> str:
    """Convert a show or title string into a safe file slug."""
    clean = re.sub(r"[^\w\s-]", "", name.lower())
    clean = re.sub(r"[\s_]+", "_", clean).strip("_")
    return clean or "torrents"


def is_back(val: Any) -> bool:
    """Check if the user requested to go back via keybinding or text command."""
    if val is None:
        return True
    if isinstance(val, str) and val.strip().lower() in ("b", "back", ":b"):
        return True
    if val == "back":
        return True
    return False


class InteractiveSession:
    """Manages the interactive terminal session flow with full go-back support."""

    def __init__(self, client: Optional[ApibayClient] = None):
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
                again = inquirer.confirm(message="Perform another search?", default=True).execute()
                if not again:
                    console.print("[dim]Goodbye![/dim]")
                    break

        except KeyboardInterrupt:
            console.print("\n[yellow]Operation cancelled by user. Goodbye![/yellow]")
            sys.exit(0)

    def handle_tv_flow(self) -> None:
        """Workflow for finding and downloading TV show seasons/episodes with instant back navigation."""
        step = 1
        show_name = ""
        season_num = 1
        quality_pref = "1080p"
        selected_torrents: List[Torrent] = []

        while True:
            if step == 1:
                # Step 1: Show title
                val = inquirer.text(
                    message="Enter TV show title (e.g. Severance, Breaking Bad):",
                    default=show_name,
                    instruction="(Esc or 'b': go back)",
                    mandatory=False,
                    keybindings=TEXT_BACK_KEYBINDINGS,
                ).execute()

                if is_back(val):
                    return  # Back to main menu
                show_name = val.strip()
                step = 2

            elif step == 2:
                # Step 2: Season number
                val = inquirer.text(
                    message="Enter Season number:",
                    default=str(season_num),
                    instruction="(Esc or 'b': go back)",
                    mandatory=False,
                    keybindings=TEXT_BACK_KEYBINDINGS,
                ).execute()

                if is_back(val):
                    step = 1
                    continue

                if not val.strip().isdigit() or int(val.strip()) <= 0:
                    console.print("[red]Please enter a valid positive number.[/red]")
                    continue

                season_num = int(val.strip())
                step = 3

            elif step == 3:
                # Step 3: Quality preference
                val = inquirer.select(
                    message="Select preferred quality:",
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
                    step = 2
                    continue

                quality_pref = val
                step = 4

            elif step == 4:
                # Step 4: Fast Search & episode resolution (uses in-memory cache if already fetched!)
                cache_key = (show_name.lower(), "")
                if cache_key in self.client._cache:
                    torrents = self.client.search(show_name)
                else:
                    with console.status(f"[cyan]Searching Apibay for '[bold]{show_name}[/bold]'...[/cyan]", spinner="dots"):
                        try:
                            torrents = self.client.search(show_name)
                        except ApibayError as err:
                            console.print(f"[bold red]Search Error:[/] {err}")
                            step = 1
                            continue

                if not torrents:
                    console.print(f"[yellow]No results found on Apibay for '{show_name}'.[/yellow]")
                    step = 1
                    continue

                season_packs = get_season_packs(torrents, season_num)
                episodes_map = filter_and_group_episodes(
                    torrents,
                    target_season=season_num,
                    preferred_quality=None if quality_pref == "Any" else quality_pref,
                )

                if season_packs:
                    console.print(f"\n[green][OK] Found {len(season_packs)} complete Season {season_num} pack(s)![/green]")
                    choice_type = inquirer.select(
                        message=f"How would you like to grab Season {season_num}?",
                        choices=[
                            Choice("episodes", f"📋 Select individual episodes ({len(episodes_map)} episode numbers detected)"),
                            Choice("pack", f"📦 Grab a complete Season {season_num} pack ({season_packs[0].human_size})"),
                            Separator(),
                            Choice("back", "⬅️ Go Back [b / Esc / ←]"),
                        ] if episodes_map else [
                            Choice("pack", f"📦 Grab a complete Season {season_num} pack ({season_packs[0].human_size})"),
                            Separator(),
                            Choice("back", "⬅️ Go Back [b / Esc / ←]"),
                        ],
                        default="episodes" if episodes_map else "pack",
                        instruction="(b / Esc / ←: go back)",
                        mandatory=False,
                        keybindings=SELECT_BACK_KEYBINDINGS,
                    ).execute()

                    if is_back(choice_type):
                        step = 3
                        continue

                    if choice_type == "pack":
                        pack_choices = [
                            Choice(
                                p,
                                name=f"{p.name} ({p.quality}, {p.human_size}, {p.seeders} seeds, uploader: {p.username})"
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
                            continue  # Re-prompt pack vs episodes

                        selected_torrents = [chosen_pack]
                    else:
                        selected_torrents = self._select_episodes_flow(episodes_map, show_name, season_num)
                        if is_back(selected_torrents):
                            continue  # Re-prompt pack vs episodes
                else:
                    if not episodes_map:
                        console.print(
                            f"[yellow]Could not find specific Season {season_num} episodes for '{show_name}'.[/yellow]\n"
                            f"[dim]Tip: Showing all search results so you can manually select releases:[/dim]"
                        )
                        render_torrents_table(torrents[:20], title=f"All Results for '{show_name}'")
                        selected_torrents = self._manual_multi_select(torrents[:20])
                        if is_back(selected_torrents):
                            step = 3
                            continue
                    else:
                        selected_torrents = self._select_episodes_flow(episodes_map, show_name, season_num)
                        if is_back(selected_torrents):
                            step = 3
                            continue

                if not selected_torrents:
                    console.print("[yellow]No torrents selected.[/yellow]")
                    step = 3
                    continue

                step = 5

            elif step == 5:
                # Step 5: Export destination workflow
                default_filename = f"{sanitize_filename(show_name)}_S{season_num:02d}_magnets.txt"
                completed = self._export_workflow(selected_torrents, default_filename=default_filename)
                if completed:
                    break
                else:
                    # User requested to go back from export workflow
                    step = 4

    def _select_episodes_flow(
        self,
        episodes_map: dict,
        show_name: str,
        season_num: int,
    ) -> Optional[List[Torrent]]:
        """Allow user to review and check/uncheck episodes and pick between different quality variants."""
        choices = []
        total_eps = len(episodes_map)

        for ep_num in sorted(episodes_map.keys()):
            candidates = episodes_map[ep_num]
            variants = get_episode_quality_variants(candidates)

            sep_text = f"── Episode {ep_num:02d} ({len(variants)} quality option{'s' if len(variants) > 1 else ''}) ──"
            choices.append(Separator(sep_text))

            for idx, variant in enumerate(variants):
                is_default = (idx == 0)
                default_tag = " [Default]" if is_default else ""
                codec_tag = f" | {variant.codec}" if variant.codec != "Unknown" else ""
                label = (
                    f"E{ep_num:02d} [{variant.quality}{codec_tag}] {variant.name} "
                    f"[{variant.human_size} | {variant.seeders} seeds]{default_tag}"
                )
                choices.append(Choice(variant, name=label, enabled=is_default))

        console.print(f"\n[bold cyan]Found {total_eps} episode(s) for {show_name} Season {season_num}:[/bold cyan]")
        console.print(
            "[dim]• Top release per episode is pre-checked [X] by default.\n"
            "• Different quality options are listed underneath — use [Spacebar] to switch/toggle.\n"
            "• Press [a] to toggle all, [Enter] to confirm, or [b / Esc / ←] to Go Back.[/dim]"
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

    def _manual_multi_select(self, torrents: List[Torrent]) -> Optional[List[Torrent]]:
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
        selected: Optional[List[Torrent]] = None

        while True:
            if step == 1:
                val = inquirer.text(
                    message="Enter movie title:",
                    default=movie_title,
                    instruction="(Esc or 'b': go back)",
                    mandatory=False,
                    keybindings=TEXT_BACK_KEYBINDINGS,
                ).execute()

                if is_back(val):
                    return  # Back to main menu
                movie_title = val.strip()
                step = 2

            elif step == 2:
                cache_key = (movie_title.lower(), CAT_MOVIES_HD)
                if cache_key in self.client._cache:
                    torrents = self.client.search(movie_title, category=CAT_MOVIES_HD)
                else:
                    with console.status(f"[cyan]Searching Apibay for '[bold]{movie_title}[/bold]'...[/cyan]", spinner="dots"):
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
                selected = self._manual_multi_select(torrents[:25])
                if is_back(selected):
                    step = 1
                    continue

                if not selected:
                    console.print("[yellow]No items selected.[/yellow]")
                    step = 1
                    continue

                step = 3

            elif step == 3:
                default_filename = f"{sanitize_filename(movie_title)}_magnets.txt"
                completed = self._export_workflow(selected, default_filename=default_filename)
                if completed:
                    break
                else:
                    step = 2

    def handle_general_flow(self) -> None:
        """Workflow for general search across all categories with fast back navigation."""
        step = 1
        query = ""
        selected: Optional[List[Torrent]] = None

        while True:
            if step == 1:
                val = inquirer.text(
                    message="Enter search query:",
                    default=query,
                    instruction="(Esc or 'b': go back)",
                    mandatory=False,
                    keybindings=TEXT_BACK_KEYBINDINGS,
                ).execute()

                if is_back(val):
                    return  # Back to main menu
                query = val.strip()
                step = 2

            elif step == 2:
                cache_key = (query.lower(), CAT_ALL)
                if cache_key in self.client._cache:
                    torrents = self.client.search(query, category=CAT_ALL)
                else:
                    with console.status(f"[cyan]Searching Apibay for '[bold]{query}[/bold]'...[/cyan]", spinner="dots"):
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
                selected = self._manual_multi_select(torrents[:30])
                if is_back(selected):
                    step = 1
                    continue

                if not selected:
                    console.print("[yellow]No items selected.[/yellow]")
                    step = 1
                    continue

                step = 3

            elif step == 3:
                default_filename = f"{sanitize_filename(query)}_magnets.txt"
                completed = self._export_workflow(selected, default_filename=default_filename)
                if completed:
                    break
                else:
                    step = 2

    def _export_workflow(self, torrents: List[Torrent], default_filename: str) -> bool:
        """
        Handles export actions: Save to file and/or print to console (P2: B, Edge 1: A).
        Returns True if export completed, False if user chose to Go Back.
        """
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
                instruction="(Esc or 'b': go back)",
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
                        Choice("cancel", "🚫 Cancel file save"),
                    ],
                    default="overwrite",
                    instruction="(b / Esc / ←: cancel)",
                    mandatory=False,
                    keybindings=SELECT_BACK_KEYBINDINGS,
                ).execute()

                if is_back(conflict_action) or conflict_action == "cancel":
                    console.print("[yellow]File save cancelled.[/yellow]")
                else:
                    append_mode = (conflict_action == "append")
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
