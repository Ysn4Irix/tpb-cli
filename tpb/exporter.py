"""Export utilities for magnet links and terminal rendering."""

from pathlib import Path
from typing import List, Optional, Sequence, Any
from rich.console import Console
from rich.table import Table

from tpb.models import Torrent, ensure_torrents

# Force UTF-8 safe rendering
console = Console()


def render_torrents_table(torrents: Sequence[Any], title: str = "Search Results") -> None:
    """Render a styled Rich table of torrents."""
    torrents = ensure_torrents(torrents)
    if not torrents:
        console.print("[yellow]No torrents to display.[/yellow]")
        return

    table = Table(title=title, show_header=True, header_style="bold cyan", border_style="dim")
    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("Title", style="white", ratio=4)
    table.add_column("Quality", style="magenta", width=9)
    table.add_column("Codec", style="blue", width=8)
    table.add_column("Size", style="green", width=11, justify="right")
    table.add_column("Seeds", width=8, justify="right")
    table.add_column("Leech", style="dim", width=8, justify="right")
    table.add_column("Uploader", style="cyan", width=14)

    for idx, t in enumerate(torrents, 1):
        # Color seeders based on health
        if t.seeders > 50:
            seed_style = "[bold green]"
        elif t.seeders > 5:
            seed_style = "[yellow]"
        else:
            seed_style = "[red]"
        seed_str = f"{seed_style}{t.seeders}[/]"

        # Uploader badge (Windows safe, no raw emojis that break cp1252)
        uploader = t.username or "Anonymous"
        if t.is_vip:
            uploader = f"[bold green][VIP][/] {uploader}"
        elif t.is_trusted:
            uploader = f"[bold magenta][TRUST][/] {uploader}"

        table.add_row(
            str(idx),
            t.name,
            t.quality,
            t.codec,
            t.human_size,
            seed_str,
            str(t.leechers),
            uploader,
        )

    console.print(table)


def render_magnet_list(torrents: Sequence[Any]) -> None:
    """Print magnet links directly to the console."""
    torrents = ensure_torrents(torrents)
    if not torrents:
        return

    console.print("\n[bold cyan]==== Magnet Links ====[/bold cyan]")
    for idx, t in enumerate(torrents, 1):
        console.print(f"[bold yellow]#{idx} {t.name}[/bold yellow] ({t.human_size}, {t.seeders} seeds)")
        console.print(f"[dim]{t.magnet_link}[/dim]\n")


def export_magnets_to_file(
    torrents: Sequence[Any],
    file_path: Path,
    append: bool = False,
    include_metadata_comments: bool = True,
) -> int:
    """
    Write magnet links to a text file.
    Returns the number of written links.
    """
    torrents = ensure_torrents(torrents)
    if not torrents:
        return 0

    mode = "a" if append else "w"
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, mode, encoding="utf-8") as f:
        if mode == "a":
            f.write("\n")

        for t in torrents:
            if include_metadata_comments:
                f.write(f"# {t.name} | Size: {t.human_size} | Seeds: {t.seeders}\n")
            f.write(f"{t.magnet_link}\n\n")

    return len(torrents)
