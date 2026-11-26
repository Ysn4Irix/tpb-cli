from tpb.models import Torrent
from tpb.parser import (
    detect_quality,
    detect_codec,
    parse_tv_metadata,
    enrich_torrent_metadata,
    filter_and_group_episodes,
    get_season_packs,
)


def test_detect_quality():
    assert detect_quality("Movie.2024.2160p.UHD.BluRay") == "2160p"
    assert detect_quality("Show.S01E01.1080p.WEBRip") == "1080p"
    assert detect_quality("Show.S01E02.720p.HDTV") == "720p"
    assert detect_quality("Classic.Movie.DVDRip.xvid") == "480p"
    assert detect_quality("Unknown.Video.File") == "Unknown"


def test_detect_codec():
    assert detect_codec("Show.S01.1080p.x265.HEVC") == "x265"
    assert detect_codec("Movie.720p.H.264") == "x264"
    assert detect_codec("Old.Film.XviD") == "XviD"
    assert detect_codec("Modern.4k.AV1") == "AV1"


def test_parse_tv_metadata():
    # S01E05
    s, ep, eps, is_pack = parse_tv_metadata("Severance.S01E05.1080p")
    assert s == 1
    assert ep == 5
    assert eps == [5]
    assert is_pack is False

    # Multi-episode S02E01-E03
    s, ep, eps, is_pack = parse_tv_metadata("Show.S02E01-E03.720p")
    assert s == 2
    assert ep == 1
    assert eps == [1, 2, 3]
    assert is_pack is False

    # 1x04 format
    s, ep, eps, is_pack = parse_tv_metadata("The.Wire.1x04.HDTV")
    assert s == 1
    assert ep == 4
    assert eps == [4]
    assert is_pack is False

    # Complete Season Pack "Severance - Season 1 - 1080p"
    s, ep, eps, is_pack = parse_tv_metadata("Severance - Season 1 - 1080p")
    assert s == 1
    assert ep is None
    assert is_pack is True

    # Standalone S03 pack
    s, ep, eps, is_pack = parse_tv_metadata("Show.Name.S03.1080p.BluRay")
    assert s == 3
    assert is_pack is True


def test_filter_and_group_episodes():
    t1 = Torrent(
        id="1", name="Show.S01E01.720p", info_hash="111", leechers=5, seeders=100, size_bytes=500
    )
    t2 = Torrent(
        id="2", name="Show.S01E01.1080p", info_hash="222", leechers=10, seeders=50, size_bytes=1000
    )
    t3 = Torrent(
        id="3", name="Show.S01E02.1080p", info_hash="333", leechers=10, seeders=80, size_bytes=1000
    )
    t4 = Torrent(
        id="4", name="Show.S02E01.1080p", info_hash="444", leechers=10, seeders=80, size_bytes=1000
    )

    all_torrents = [enrich_torrent_metadata(t) for t in [t1, t2, t3, t4]]

    # Target season 1 with preferred quality 1080p
    grouped = filter_and_group_episodes(all_torrents, target_season=1, preferred_quality="1080p")

    assert 1 in grouped
    assert 2 in grouped
    assert len(grouped[1]) == 2
    # Even though 720p has more seeds (100 vs 50), preferred quality 1080p should be top!
    assert grouped[1][0].quality == "1080p"
    assert grouped[2][0].name == "Show.S01E02.1080p"


def test_get_season_packs():
    pack = Torrent(
        id="1",
        name="Show Season 1 Complete 1080p",
        info_hash="AAA",
        leechers=5,
        seeders=200,
        size_bytes=10000,
    )
    single = Torrent(
        id="2", name="Show S01E01 1080p", info_hash="BBB", leechers=5, seeders=50, size_bytes=1000
    )

    enriched = [enrich_torrent_metadata(t) for t in [pack, single]]
    packs = get_season_packs(enriched, target_season=1)

    assert len(packs) == 1
    assert packs[0].id == "1"


def test_get_episode_quality_variants():
    from tpb.parser import get_episode_quality_variants

    t_1080p_1 = Torrent(
        id="1", name="Ep1 1080p x264", info_hash="11", leechers=1, seeders=100, size_bytes=1000
    )
    t_1080p_2 = Torrent(
        id="2",
        name="Ep1 1080p x264 duplicate",
        info_hash="22",
        leechers=1,
        seeders=50,
        size_bytes=1000,
    )
    t_1080p_x265 = Torrent(
        id="3", name="Ep1 1080p x265", info_hash="33", leechers=1, seeders=80, size_bytes=500
    )
    t_720p = Torrent(
        id="4", name="Ep1 720p x264", info_hash="44", leechers=1, seeders=90, size_bytes=400
    )
    t_2160p = Torrent(
        id="5", name="Ep1 2160p 4k", info_hash="55", leechers=1, seeders=30, size_bytes=4000
    )

    all_torrents = [
        enrich_torrent_metadata(t) for t in [t_1080p_1, t_1080p_2, t_1080p_x265, t_720p, t_2160p]
    ]

    variants = get_episode_quality_variants(all_torrents)

    # Should include 1080p x264, 1080p x265, 720p, 2160p
    qualities = [v.quality for v in variants]
    assert "1080p" in qualities
    assert "720p" in qualities
    assert "2160p" in qualities
    assert len(variants) == 4
    # The first 1080p x264 should be top-seeded
    assert variants[0].id == "1"


def test_get_detected_seasons_summary():
    from tpb.parser import get_detected_seasons_summary

    t1 = Torrent(
        id="1", name="Show.S01E01.1080p", info_hash="11", leechers=1, seeders=100, size_bytes=1000
    )
    t2 = Torrent(
        id="2", name="Show.S01E02.1080p", info_hash="22", leechers=1, seeders=80, size_bytes=1000
    )
    t3 = Torrent(
        id="3",
        name="Show.Season.1.Complete.720p",
        info_hash="33",
        leechers=1,
        seeders=200,
        size_bytes=5000,
    )
    t4 = Torrent(
        id="4", name="Show.S02E01.720p", info_hash="44", leechers=1, seeders=50, size_bytes=1000
    )

    summary = get_detected_seasons_summary([t1, t2, t3, t4])

    assert 1 in summary
    assert 2 in summary
    assert len(summary[1]["episodes"]) == 2  # ep 1 and 2
    assert len(summary[1]["packs"]) == 1  # 1 complete pack
    assert summary[1]["total_torrents"] == 3
    assert len(summary[2]["episodes"]) == 1  # ep 1
    assert len(summary[2]["packs"]) == 0


def test_detect_series_variants():
    from tpb.parser import detect_series_variants

    us_1 = Torrent(
        id="1",
        name="The.Office.US.S01E01.1080p",
        info_hash="1",
        leechers=1,
        seeders=10,
        size_bytes=100,
    )
    us_2 = Torrent(
        id="2",
        name="The.Office.US.S02E01.1080p",
        info_hash="2",
        leechers=1,
        seeders=10,
        size_bytes=100,
    )
    uk_1 = Torrent(
        id="3",
        name="The.Office.UK.S01E01.720p",
        info_hash="3",
        leechers=1,
        seeders=10,
        size_bytes=100,
    )
    uk_2 = Torrent(
        id="4",
        name="The.Office.UK.S02E01.720p",
        info_hash="4",
        leechers=1,
        seeders=10,
        size_bytes=100,
    )

    variants = detect_series_variants([us_1, us_2, uk_1, uk_2])
    assert "US" in variants
    assert "UK" in variants
    assert len(variants["US"]) == 2
    assert len(variants["UK"]) == 2

    # Single variant should return empty
    assert detect_series_variants([us_1, us_2]) == {}
