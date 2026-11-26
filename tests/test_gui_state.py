"""Unit tests for GUI persistent state store, torrent file normalization, and CLI --gui flag."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import sys

import pytest

from tpb.api import ApibayClient, validate_http_url, validate_proxy_url
from tpb.cli import build_parser, main as cli_main
from tpb.gui.state import AppStateStore
from tpb.models import TorrentFile, format_bytes, normalize_torrent_files, sanitize_filename


def test_app_state_store_persistence_and_history(tmp_path: Path):
    cfg = tmp_path / "gui_state.json"
    store = AppStateStore(config_path=cfg)
    assert store.settings.theme == "dark"

    store.settings.theme = "light"
    store.settings.proxy = "socks5://127.0.0.1:9050"
    store.settings.api_url = "https://mirror.example.org"
    store.add_history("Severance", "tv")
    store.add_history("Inception", "movie")
    store.add_history("severance", "tv")  # Deduplicates and moves to top

    assert len(store.history) == 2
    assert store.history[0].query == "severance"
    assert store.history[1].query == "Inception"

    assert store.toggle_bookmark("Breaking Bad", "tv") is True
    assert store.is_bookmarked("breaking bad", "tv") is True

    # Reload from disk
    reloaded = AppStateStore(config_path=cfg)
    assert reloaded.settings.theme == "light"
    assert reloaded.settings.proxy == "socks5://127.0.0.1:9050"
    assert reloaded.settings.api_url == "https://mirror.example.org"
    assert len(reloaded.history) == 2
    assert reloaded.is_bookmarked("Breaking Bad", "tv") is True

    assert reloaded.toggle_bookmark("Breaking Bad", "tv") is False
    assert reloaded.is_bookmarked("Breaking Bad", "tv") is False

    reloaded.clear_history()
    assert reloaded.history == []


def test_app_state_store_handles_corrupt_json(tmp_path: Path):
    cfg = tmp_path / "broken.json"
    cfg.write_text("{not-valid-json", encoding="utf-8")

    store = AppStateStore(config_path=cfg)
    assert store.settings.theme == "dark"
    assert store.history == []
    assert store.bookmarks == []


def test_normalize_torrent_files_handles_list_and_scalar_shapes():
    raw = [
        {"name": ["Season 1", "Show.S01E01.mkv"], "size": ["1048576"]},
        {"name": "README.txt", "size": 512},
        {"name": "", "size": 100},
    ]
    parsed = normalize_torrent_files(raw)
    assert len(parsed) == 2
    assert isinstance(parsed[0], TorrentFile)
    assert parsed[0].name == "Season 1/Show.S01E01.mkv"
    assert parsed[0].size_bytes == 1048576
    assert parsed[0].human_size == "1.00 MiB"
    assert parsed[1].name == "README.txt"
    assert parsed[1].size_bytes == 512

    assert normalize_torrent_files([{"name": ["File list not found"], "size": [0]}]) == []
    assert normalize_torrent_files({"unexpected": "object"}) == []


def test_client_get_parsed_files_caching_and_clear_cache():
    client = ApibayClient()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [{"name": ["Movie.mkv"], "size": [2048]}]

    with patch.object(client, "_get_client") as mock_get_client:
        mock_ctx = MagicMock()
        mock_ctx.get.return_value = mock_response
        mock_get_client.return_value.__enter__.return_value = mock_ctx

        first = client.get_parsed_files("42")
        second = client.get_parsed_files("42")
        assert len(first) == 1
        assert first[0].name == "Movie.mkv"
        assert second[0].size_bytes == 2048
        assert mock_ctx.get.call_count == 1

        client.clear_cache()
        client.get_parsed_files("42")
        assert mock_ctx.get.call_count == 2


def test_shared_helpers():
    assert format_bytes(1024 * 1024) == "1.00 MiB"
    assert sanitize_filename("Mr. Robot (US)!") == "mr_robot_us"


def test_url_and_proxy_boundary_validation():
    assert validate_http_url("https://apibay.org/") == "https://apibay.org"
    assert validate_proxy_url("  ") is None
    assert validate_proxy_url("socks5://127.0.0.1:9050") == "socks5://127.0.0.1:9050"

    with pytest.raises(ValueError):
        validate_http_url("ftp://example.org")
    with pytest.raises(ValueError):
        validate_http_url("not-a-url")
    with pytest.raises(ValueError):
        validate_proxy_url("file:///etc/passwd")

    client = ApibayClient()
    client.reconfigure("http://localhost:8080/", "http://127.0.0.1:8888")
    assert client.base_url == "http://localhost:8080"
    assert client.proxy == "http://127.0.0.1:8888"


def test_cli_gui_flag_parses_and_handles_missing_pyside6():
    parser = build_parser()
    args = parser.parse_args(
        ["--gui", "--api-url", "https://example.org", "--proxy", "http://127.0.0.1:8080"]
    )
    assert args.gui is True
    assert args.api_url == "https://example.org"
    assert args.proxy == "http://127.0.0.1:8080"

    with (
        patch.object(sys, "argv", ["tpb", "--gui"]),
        patch.dict(sys.modules, {"tpb.gui.app": None}),
    ):
        with pytest.raises(SystemExit) as exc_info:
            cli_main()
        assert exc_info.value.code == 1
