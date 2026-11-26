"""Command-line entrypoint supporting both interactive mode and scripted flags."""

import argparse
import io
import sys
from pathlib import Path
from rich.console import Console

# Ensure UTF-8 output encoding on Windows if supported
try:
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    if isinstance(sys.stderr, io.TextIOWrapper):
        sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, OSError, ValueError):
    # Some non-TTY or frozen hosts do not support stream reconfiguration.
    pass

from tpb import __version__
from tpb.api import ApibayClient, ApibayError
from tpb.parser import filter_and_group_episodes, get_season_packs
from tpb.exporter import render_torrents_table, render_magnet_list, export_magnets_to_file

console = Console()


def build_parser() -> argparse.ArgumentParser:
    """Build argument parser for CLI flags."""
    parser = argparse.ArgumentParser(
        prog="tpb",
        description="Search movies and TV series magnet links via Apibay / The Pirate Bay.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  tpb                                # Launch interactive menu
  tpb "Severance" -s 1               # Interactive episode picker for Severance Season 1
  tpb "Severance" -s 1 -q 1080p -o severance_s1.txt  # Non-interactive batch export
  tpb "Inception" -o inception.txt   # Download top movie magnet
  tpb "Avatar" --print               # Search and print magnets directly to terminal
        """,
    )

    parser.add_argument(
        "query",
        nargs="?",
        default=None,
        help="Search query (movie title or TV show name). If omitted, opens interactive menu.",
    )
    parser.add_argument(
        "-s",
        "--season",
        type=int,
        default=None,
        help="TV Show season number to fetch (e.g. 1 or 2).",
    )
    parser.add_argument(
        "-q",
        "--quality",
        type=str,
        default=None,
        choices=["2160p", "1080p", "720p", "480p", "any"],
        help="Preferred video resolution (e.g. 1080p).",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Path to output text file for saving magnet links.",
    )
    parser.add_argument(
        "-p",
        "--print",
        dest="print_magnets",
        action="store_true",
        help="Print magnet links directly to the console.",
    )
    parser.add_argument(
        "--pack",
        action="store_true",
        help="For TV seasons, export complete season pack if available instead of individual episodes.",
    )
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Force interactive selection even if search query is provided.",
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default=None,
        help="Custom Apibay API base URL (default: https://apibay.org).",
    )
    parser.add_argument(
        "--proxy",
        type=str,
        default=None,
        help="HTTP/SOCKS5 proxy URL (e.g. http://127.0.0.1:8080).",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Launch the PySide6 desktop graphical user interface.",
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"tpb-cli {__version__}",
    )

    return parser


def handle_scripted_run(args: argparse.Namespace) -> int:
    """Handle CLI execution when flags/queries are provided."""
    client = ApibayClient(
        base_url=args.api_url or "https://apibay.org",
        proxy=args.proxy,
    )

    query = args.query.strip()
    quality = None if not args.quality or args.quality.lower() == "any" else args.quality

    console.print(f"[cyan]Searching Apibay for '[bold]{query}[/bold]'...[/cyan]")
    try:
        torrents = client.search(query)
    except ApibayError as exc:
        console.print(f"[bold red]API Error:[/] {exc}")
        return 1

    if not torrents:
        console.print(f"[yellow]No results found for '{query}'.[/yellow]")
        return 0

    selected_torrents = []

    # TV Season workflow
    if args.season is not None:
        season_num = args.season
        season_packs = get_season_packs(torrents, season_num)
        episodes_map = filter_and_group_episodes(
            torrents,
            target_season=season_num,
            preferred_quality=quality,
        )

        if args.pack and season_packs:
            console.print(f"[green]Using Season {season_num} complete pack.[/green]")
            selected_torrents = [season_packs[0]]
        elif episodes_map:
            for ep_num in sorted(episodes_map.keys()):
                selected_torrents.append(episodes_map[ep_num][0])
            console.print(
                f"[green]Collected {len(selected_torrents)} episodes for Season {season_num}.[/green]"
            )
        elif season_packs:
            console.print(
                f"[green]No individual episodes found; using complete Season {season_num} pack.[/green]"
            )
            selected_torrents = [season_packs[0]]
        else:
            console.print(f"[yellow]No season {season_num} releases found for '{query}'.[/yellow]")
            return 1
    else:
        # General query / movie
        if quality:
            filtered = [t for t in torrents if quality.lower() in t.quality.lower()]
            selected_torrents = filtered[:1] if filtered else torrents[:1]
        else:
            selected_torrents = torrents[:1]

    # Render table of selected items
    render_torrents_table(selected_torrents, title=f"Selected Releases for '{query}'")

    # Output handling
    output_path = args.output
    if not output_path and not args.print_magnets:
        # If neither output nor print specified, default to printing and notify
        args.print_magnets = True

    if output_path:
        dest_file = Path(output_path)
        count = export_magnets_to_file(selected_torrents, dest_file)
        console.print(
            f"[bold green]OK:[/] Exported {count} magnet link(s) to '{dest_file.resolve()}'"
        )

    if args.print_magnets:
        render_magnet_list(selected_torrents)

    return 0


def main() -> None:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args()

    if args.gui:
        try:
            from tpb.gui.app import main as gui_main
        except ImportError:
            console.print(
                "[bold red]GUI dependencies missing:[/] PySide6 is required for desktop mode.\n"
                'Install with: [cyan]pip install "tpb-cli[gui]"[/cyan]'
            )
            sys.exit(1)
        sys.exit(gui_main(api_url=args.api_url, proxy=args.proxy))

    # If no arguments provided or explicitly interactive
    if args.query is None or args.interactive:
        from tpb.interactive import InteractiveSession

        client = ApibayClient(
            base_url=args.api_url or "https://apibay.org",
            proxy=args.proxy,
        )
        session = InteractiveSession(client=client)
        session.run()
        sys.exit(0)

    # Scripted flag execution
    exit_code = handle_scripted_run(args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
