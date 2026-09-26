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
