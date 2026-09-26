import pytest
from pathlib import Path
from tpb.models import Torrent
from tpb.exporter import export_magnets_to_file


def test_export_magnets_to_file(tmp_path: Path):
    t1 = Torrent(id="1", name="Movie 1", info_hash="AAA111", leechers=1, seeders=10, size_bytes=1024*1024*500)
    t2 = Torrent(id="2", name="Movie 2", info_hash="BBB222", leechers=2, seeders=20, size_bytes=1024*1024*700)

    out_file = tmp_path / "test_magnets.txt"

    # Write initial file
    count = export_magnets_to_file([t1], out_file, append=False)
    assert count == 1
    assert out_file.exists()

    content = out_file.read_text(encoding="utf-8")
    assert "Movie 1" in content
    assert "xt=urn:btih:AAA111" in content

    # Append second torrent
    count_append = export_magnets_to_file([t2], out_file, append=True)
    assert count_append == 1

    content_appended = out_file.read_text(encoding="utf-8")
    assert "Movie 1" in content_appended
    assert "Movie 2" in content_appended
    assert "xt=urn:btih:BBB222" in content_appended


def test_export_magnets_with_dicts(tmp_path: Path):
    """Verify that export_magnets_to_file handles dictionary objects without raising AttributeError."""
    import dataclasses
    t = Torrent(id="1", name="Show S01E01", info_hash="CCC333", leechers=0, seeders=15, size_bytes=1000)
    d = dataclasses.asdict(t)

    raw_api_dict = {
        "id": "2",
        "name": "Show S01E02",
        "info_hash": "DDD444",
        "leechers": "1",
        "seeders": "25",
        "size": "2000",
        "username": "uploader",
    }

    out_file = tmp_path / "dict_magnets.txt"
    count = export_magnets_to_file([d, raw_api_dict], out_file, append=False)
    assert count == 2

    content = out_file.read_text(encoding="utf-8")
    assert "Show S01E01" in content
    assert "xt=urn:btih:CCC333" in content
    assert "Show S01E02" in content
    assert "xt=urn:btih:DDD444" in content


def test_render_with_dicts():
    """Verify render_torrents_table and render_magnet_list do not crash when given dicts."""
    from tpb.exporter import render_torrents_table, render_magnet_list
    import dataclasses

    t = Torrent(id="1", name="Movie Dict", info_hash="EEE555", leechers=0, seeders=10, size_bytes=50000)
    d = dataclasses.asdict(t)

    # These should execute cleanly without raising AttributeError
    render_torrents_table([d])
    render_magnet_list([d])

