import urllib.parse
from tpb.models import Torrent, DEFAULT_TRACKERS


def test_torrent_magnet_generation():
    torrent = Torrent(
        id="12345",
        name="Severance S01E01 1080p",
        info_hash="ABCDEF1234567890ABCDEF1234567890ABCDEF12",
        leechers=10,
        seeders=150,
        size_bytes=1024 * 1024 * 1500,  # ~1.46 GiB
        username="VIP_User",
        status="vip",
    )

    magnet = torrent.magnet_link
    assert magnet.startswith("magnet:?xt=urn:btih:ABCDEF1234567890ABCDEF1234567890ABCDEF12")
    assert "dn=Severance%20S01E01%201080p" in magnet
    for tracker in DEFAULT_TRACKERS[:2]:
        assert f"tr={urllib.parse.quote(tracker)}" in magnet
    assert torrent.is_vip is True
    assert torrent.is_trusted is False
    assert "GiB" in torrent.human_size


def test_torrent_dummy_hash():
    torrent = Torrent(
        id="0",
        name="No results returned",
        info_hash="0000000000000000000000000000000000000000",
        leechers=0,
        seeders=0,
        size_bytes=0,
    )
    assert torrent.magnet_link == ""
