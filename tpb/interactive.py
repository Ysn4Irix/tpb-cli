"""Interactive TUI / terminal workflow using InquirerPy, Rich, and prompt_toolkit."""

import re
import sys
from pathlib import Path
from typing import List, Optional

from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from InquirerPy.separator import Separator
from rich.console import Console
from rich.panel import Panel

from tpb.api import ApibayClient, ApibayError, CAT_TV_HD, CAT_MOVIES_HD, CAT_ALL
from tpb.models import Torrent
from tpb.parser import (
    filter_and_group_episodes,
    get_season_packs,
    detect_quality,
    get_episode_quality_variants,
)
from tpb.exporter import render_torrents_table, render_magnet_list, export_magnets_to_file
from tpb.live_search import LiveSearchSession

console = Console()


def sanitize_filename(name: str) -> str:
    """Convert a show or title string into a safe file slug."""
    clean = re.sub(r"[^\w\s-]", "", name.lower())
    clean = re.sub(r"[\s_]+", "_", clean).strip("_")
    return clean or "torrents"


class InteractiveSession:
    """Manages the interactive terminal session flow."""

    def __init__(self, client: Optional[ApibayClient] = None):
        self.client = client or ApibayClient()

    def run(self) -> None:
        """Main entry point for interactive wizard."""
        console.print(
            Panel.fit(
                "[bold cyan]TPB / Apibay Interactive CLI[/bold cyan]\n"
                "[dim]Search movies & TV series live, grab magnet links, and batch export seasons.[/dim]",
                border_style="cyan",
            )
        )

        try:
            while True:
                mode = inquirer.select(
                    message="What would you like to do?",
                    choices=[
                        Choice("live", "⚡ Live Search (Real-time Apibay search as you type)"),
                        Choice("tv", "📺 TV Series (Season / Episodes batch)"),
                        Choice("movie", "🎬 Movies (Search & pick magnet)"),
                        Choice("general", "🔍 General Search (All categories)"),
                        Choice("exit", "❌ Exit"),
                    ],
                    default="live",
                ).execute()

                if mode == "exit" or mode is None:
                    console.print("[dim]Goodbye![/dim]")
                    break

                if mode == "live":
                    self.handle_live_flow()
                elif mode == "tv":
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

    def handle_live_flow(self, category: Optional[str] = None) -> None:
        """Workflow for real-time live search as you type."""
        console.print("[dim]Opening Live Search. Start typing query, use ↑/↓ to navigate results, [Enter] to select.[/dim]\n")
        session = LiveSearchSession(client=self.client, category=category)
        chosen_torrent, query = session.run()

        if not chosen_torrent and not query:
            return

        if chosen_torrent:
            console.print(
                f"\n[green][OK] Selected:[/] [bold]{chosen_torrent.name}[/bold] "
                f"[{chosen_torrent.quality} | {chosen_torrent.human_size} | {chosen_torrent.seeders} seeds]"
            )

            # If it's identified as a TV show release, provide TV-specific actions
            if (
                chosen_torrent.season is not None
                or chosen_torrent.episode is not None
                or chosen_torrent.is_season_pack
            ):
                season_num = chosen_torrent.season or 1
                action = inquirer.select(
                    message="TV Series release detected. What would you like to do?",
                    choices=[
                        Choice("single", f"💾 Export magnet for this release ({chosen_torrent.quality})"),
                        Choice("season", f"📺 Inspect and batch-select all Season {season_num} episodes"),
                        Choice("pack", f"📦 Grab a complete Season {season_num} pack"),
                    ],
                    default="season",
                ).execute()

                if action == "single":
                    default_fn = f"{sanitize_filename(chosen_torrent.name)}_magnet.txt"
                    self._export_workflow([chosen_torrent], default_filename=default_fn)
                elif action == "season":
                    clean_name = query or chosen_torrent.name.split("S0")[0].replace(".", " ").strip()
                    self._process_tv_season(clean_name, season_num)
                elif action == "pack":
                    clean_name = query or chosen_torrent.name.split("S0")[0].replace(".", " ").strip()
                    self._process_tv_season(clean_name, season_num, prefer_pack=True)
            else:
                default_fn = f"{sanitize_filename(chosen_torrent.name)}_magnet.txt"
                self._export_workflow([chosen_torrent], default_filename=default_fn)

        elif query:
            # User submitted query without highlighting a row
            with console.status(f"[cyan]Searching Apibay for '[bold]{query}[/bold]'...[/cyan]", spinner="dots"):
                try:
                    torrents = self.client.search(query, category=category)
                except ApibayError as err:
                    console.print(f"[bold red]Search Error:[/] {err}")
                    return

            if not torrents:
                console.print(f"[yellow]No results found on Apibay for '{query}'.[/yellow]")
                return

            render_torrents_table(torrents[:25], title=f"Results for '{query}'")
            selected = self._manual_multi_select(torrents[:25])
            if selected:
                default_fn = f"{sanitize_filename(query)}_magnets.txt"
                self._export_workflow(selected, default_filename=default_fn)

    def handle_tv_flow(self) -> None:
        """Workflow for finding and downloading TV show seasons/episodes."""
        search_method = inquirer.select(
            message="How would you like to search for the TV show?",
            choices=[
                Choice("live", "⚡ Live Search (Real-time as you type)"),
                Choice("manual", "⌨️ Type show name & season number manually"),
            ],
            default="live",
        ).execute()

        if search_method == "live":
            self.handle_live_flow()
            return

        show_name = inquirer.text(
            message="Enter TV show title (e.g. Severance, Breaking Bad):",
            validate=lambda x: len(x.strip()) > 0 or "Show name cannot be empty",
        ).execute()
        if not show_name:
            return

        season_str = inquirer.text(
            message="Enter Season number (e.g. 1):",
            default="1",
            validate=lambda x: x.strip().isdigit() and int(x.strip()) > 0 or "Please enter a valid positive number",
        ).execute()
        if not season_str:
            return

        season_num = int(season_str.strip())
        self._process_tv_season(show_name, season_num)

    def _process_tv_season(
        self,
        show_name: str,
        season_num: int,
        prefer_pack: bool = False,
    ) -> None:
        """Process episode resolution and selection for a given TV show season."""
        # Quality filter preference first (Decision 2: B)
        quality_pref = inquirer.select(
            message="Select preferred quality:",
            choices=[
                Choice("Any", "✨ Any Quality (Best seeded)"),
                Choice("1080p", "💎 1080p (Full HD)"),
                Choice("720p", "📺 720p (HD)"),
                Choice("2160p", "🔥 2160p / 4K (Ultra HD)"),
                Choice("480p", "📼 480p / SD"),
            ],
            default="1080p",
        ).execute()

        with console.status(f"[cyan]Searching Apibay for '[bold]{show_name}[/bold]'...[/cyan]", spinner="dots"):
            try:
                torrents = self.client.search(show_name)
            except ApibayError as err:
                console.print(f"[bold red]Search Error:[/] {err}")
                return

        if not torrents:
            console.print(f"[yellow]No results found on Apibay for '{show_name}'.[/yellow]")
            return

        # Check for season packs & individual episodes
        season_packs = get_season_packs(torrents, season_num)
        episodes_map = filter_and_group_episodes(
            torrents,
            target_season=season_num,
            preferred_quality=None if quality_pref == "Any" else quality_pref,
        )

        selected_torrents: List[Torrent] = []

        if prefer_pack and season_packs:
            chosen_pack = self._prompt_season_pack(season_packs)
            if chosen_pack:
                selected_torrents = [chosen_pack]
        elif season_packs:
            console.print(f"\n[green][OK] Found {len(season_packs)} complete Season {season_num} pack(s)![/green]")
            choice_type = inquirer.select(
                message=f"How would you like to grab Season {season_num}?",
                choices=[
                    Choice("episodes", f"📋 Select individual episodes ({len(episodes_map)} episode numbers detected)"),
                    Choice("pack", f"📦 Grab a complete Season {season_num} pack ({season_packs[0].human_size})"),
                ] if episodes_map else [
                    Choice("pack", f"📦 Grab a complete Season {season_num} pack ({season_packs[0].human_size})"),
                ],
                default="episodes" if episodes_map else "pack",
            ).execute()

            if choice_type == "pack":
                chosen_pack = self._prompt_season_pack(season_packs)
                if chosen_pack:
                    selected_torrents = [chosen_pack]
            else:
                selected_torrents = self._select_episodes_flow(episodes_map, show_name, season_num)
        else:
            if not episodes_map:
                console.print(
                    f"[yellow]Could not find specific Season {season_num} episodes for '{show_name}'.[/yellow]\n"
                    f"[dim]Tip: Showing all search results so you can manually select releases:[/dim]"
                )
                render_torrents_table(torrents[:20], title=f"All Results for '{show_name}'")
                selected_torrents = self._manual_multi_select(torrents[:20])
            else:
                selected_torrents = self._select_episodes_flow(episodes_map, show_name, season_num)

        if not selected_torrents:
            console.print("[yellow]No torrents selected.[/yellow]")
            return

        # Output / Export workflow
        default_filename = f"{sanitize_filename(show_name)}_S{season_num:02d}_magnets.txt"
        self._export_workflow(selected_torrents, default_filename=default_filename)

    def _prompt_season_pack(self, season_packs: List[Torrent]) -> Optional[Torrent]:
        """Prompt to pick a season pack."""
        pack_choices = [
            Choice(
                p,
                name=f"{p.name} ({p.quality}, {p.human_size}, {p.seeders} seeds, uploader: {p.username})"
            )
            for p in season_packs[:8]
        ]
        return inquirer.select(
            message="Select Season Pack:",
            choices=pack_choices,
        ).execute()

    def _select_episodes_flow(
        self,
        episodes_map: dict,
        show_name: str,
        season_num: int,
    ) -> List[Torrent]:
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
                # Only the top (best/preferred) candidate per episode is pre-checked by default!
                choices.append(Choice(variant, name=label, enabled=is_default))

        console.print(f"\n[bold cyan]Found {total_eps} episode(s) for {show_name} Season {season_num}:[/bold cyan]")
        console.print(
            "[dim]• Top release per episode is pre-checked [X] by default.\n"
            "• Different quality options are listed underneath — use [Spacebar] to switch/toggle.\n"
            "• Press [a] to toggle all, [Enter] to confirm selection.[/dim]"
        )

        selected = inquirer.checkbox(
            message=f"Select episodes & qualities to include in export ({total_eps} episodes):",
            choices=choices,
            validate=lambda result: len(result) > 0 or "You must select at least one episode release",
        ).execute()

        return selected or []

    def _manual_multi_select(self, torrents: List[Torrent]) -> List[Torrent]:
        """Manual checkbox selection from a list of torrents."""
        choices = [
            Choice(
                t,
                name=f"{t.name} [{t.quality}, {t.human_size}, {t.seeders} seeds]",
                enabled=False,
            )
            for t in torrents
        ]
        return inquirer.checkbox(
            message="Check off the torrents you want:",
            choices=choices,
        ).execute() or []

    def handle_movie_flow(self) -> None:
        """Workflow for searching movies."""
        search_method = inquirer.select(
            message="How would you like to search for the movie?",
            choices=[
                Choice("live", "⚡ Live Search (Real-time as you type)"),
                Choice("manual", "⌨️ Type movie title manually"),
            ],
            default="live",
        ).execute()

        if search_method == "live":
            self.handle_live_flow(category=CAT_MOVIES_HD)
            return

        movie_title = inquirer.text(
            message="Enter movie title:",
            validate=lambda x: len(x.strip()) > 0 or "Movie title cannot be empty",
        ).execute()
        if not movie_title:
            return

        with console.status(f"[cyan]Searching Apibay for '[bold]{movie_title}[/bold]'...[/cyan]", spinner="dots"):
            try:
                torrents = self.client.search(movie_title, category=CAT_MOVIES_HD)
                if not torrents:
                    torrents = self.client.search(movie_title)
            except ApibayError as err:
                console.print(f"[bold red]Search Error:[/] {err}")
                return

        if not torrents:
            console.print(f"[yellow]No movie releases found for '{movie_title}'.[/yellow]")
            return

        render_torrents_table(torrents[:25], title=f"Results for '{movie_title}'")
        selected = self._manual_multi_select(torrents[:25])
        if not selected:
            console.print("[yellow]No items selected.[/yellow]")
            return

        default_filename = f"{sanitize_filename(movie_title)}_magnets.txt"
        self._export_workflow(selected, default_filename=default_filename)

    def handle_general_flow(self) -> None:
        """Workflow for general search across all categories."""
        query = inquirer.text(
            message="Enter search query:",
            validate=lambda x: len(x.strip()) > 0 or "Query cannot be empty",
        ).execute()
        if not query:
            return

        with console.status(f"[cyan]Searching Apibay for '[bold]{query}[/bold]'...[/cyan]", spinner="dots"):
            try:
                torrents = self.client.search(query, category=CAT_ALL)
            except ApibayError as err:
                console.print(f"[bold red]Search Error:[/] {err}")
                return

        if not torrents:
            console.print(f"[yellow]No results found for '{query}'.[/yellow]")
            return

        render_torrents_table(torrents[:30], title=f"Results for '{query}'")
        selected = self._manual_multi_select(torrents[:30])
        if not selected:
            console.print("[yellow]No items selected.[/yellow]")
            return

        default_filename = f"{sanitize_filename(query)}_magnets.txt"
        self._export_workflow(selected, default_filename=default_filename)

    def _export_workflow(self, torrents: List[Torrent], default_filename: str) -> None:
        """Handles export actions: Save to file and/or print to console (P2: B, Edge 1: A)."""
        action = inquirer.select(
            message="Choose output action:",
            choices=[
                Choice("file", "💾 Save magnet links to text file"),
                Choice("console", "🖥️ Print magnet links to console"),
                Choice("both", "✨ Both (Save to text file & Print to console)"),
            ],
            default="file",
        ).execute()

        if action in ("file", "both"):
            # Prompt user with smart default filename (Edge Case 1: Option A)
            file_str = inquirer.text(
                message="Enter destination filename / path:",
                default=default_filename,
                validate=lambda x: len(x.strip()) > 0 or "Path cannot be empty",
            ).execute()

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
                ).execute()

                if conflict_action == "cancel":
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
