"""Parsing utilities for torrent titles, quality, codecs, and TV episodes."""

import re
from typing import Optional, List, Dict
from tpb.models import Torrent

QUALITY_PATTERNS = [
    (re.compile(r"\b(2160p|4k|uhd)\b", re.IGNORECASE), "2160p"),
    (re.compile(r"\b(1080p|fhd|1080i)\b", re.IGNORECASE), "1080p"),
    (re.compile(r"\b(720p|hd)\b", re.IGNORECASE), "720p"),
    (re.compile(r"\b(480p|576p|dvdrip|dvdr|sd)\b", re.IGNORECASE), "480p"),
]

CODEC_PATTERNS = [
    (re.compile(r"\b(x265|hevc|h\.?\s*265)\b", re.IGNORECASE), "x265"),
    (re.compile(r"\b(x264|avc|h\.?\s*264)\b", re.IGNORECASE), "x264"),
    (re.compile(r"\b(xvid|divx)\b", re.IGNORECASE), "XviD"),
    (re.compile(r"\b(av1)\b", re.IGNORECASE), "AV1"),
]

# Episode matchers: S01E02, S01E01-E04, 1x02
EPISODE_REGEX_MULTI = re.compile(
    r"\b[sS](?P<season>\d{1,2})[eE](?P<ep_start>\d{1,2})(?:-[eE]?(?P<ep_end>\d{1,2}))?\b"
)
EPISODE_REGEX_X = re.compile(
    r"\b(?P<season>\d{1,2})x(?P<ep_start>\d{1,2})\b"
)

# Season pack matchers: "Season 1", "S01", "S1", "Season 01-05"
SEASON_PACK_REGEX = re.compile(
    r"(?:\b[sS]eason\s*(?P<season>\d{1,2})\b|\b[sS](?P<s_tag>\d{1,2})\b)",
    re.IGNORECASE,
)
MULTI_SEASON_PACK_REGEX = re.compile(
    r"\b[sS](?P<start>\d{1,2})\s*-\s*[sS]?(?P<end>\d{1,2})\b",
    re.IGNORECASE,
)


def detect_quality(name: str) -> str:
    """Extract video quality resolution from torrent title."""
    for pattern, label in QUALITY_PATTERNS:
        if pattern.search(name):
            return label
    return "Unknown"


def detect_codec(name: str) -> str:
    """Extract video codec from torrent title."""
    for pattern, label in CODEC_PATTERNS:
        if pattern.search(name):
            return label
    return "Unknown"


def parse_tv_metadata(name: str):
    """
    Parse season and episode numbers from title.
    Returns: (season, episode, episodes_list, is_season_pack)
    """
    # 1. Check for SxxExx or SxxExx-Exx
    match = EPISODE_REGEX_MULTI.search(name)
    if match:
        season = int(match.group("season"))
        ep_start = int(match.group("ep_start"))
        ep_end = match.group("ep_end")
        if ep_end:
            episodes = list(range(ep_start, int(ep_end) + 1))
        else:
            episodes = [ep_start]
        return season, episodes[0], episodes, False

    # 2. Check for 1x02
    match_x = EPISODE_REGEX_X.search(name)
    if match_x:
        season = int(match_x.group("season"))
        ep = int(match_x.group("ep_start"))
        return season, ep, [ep], False

    # 3. Check for multi-season packs like S01-S05
    match_ms = MULTI_SEASON_PACK_REGEX.search(name)
    if match_ms:
        start_s = int(match_ms.group("start"))
        return start_s, None, [], True

    # 4. Check for standalone season mentions (Season 1, S01, Complete)
    match_s = SEASON_PACK_REGEX.search(name)
    if match_s:
        s_val = match_s.group("season") or match_s.group("s_tag")
        if s_val:
            return int(s_val), None, [], True

    return None, None, [], False


def enrich_torrent_metadata(torrent: Torrent) -> Torrent:
    """Populate quality, codec, season, and episode data on a Torrent."""
    torrent.quality = detect_quality(torrent.name)
    torrent.codec = detect_codec(torrent.name)
    season, episode, episodes, is_pack = parse_tv_metadata(torrent.name)
    torrent.season = season
    torrent.episode = episode
    torrent.episodes = episodes
    torrent.is_season_pack = is_pack
    return torrent


def filter_and_group_episodes(
    torrents: List[Torrent],
    target_season: int,
    preferred_quality: Optional[str] = None,
) -> Dict[int, List[Torrent]]:
    """
    Filter torrents matching target_season and group by episode number.
    Each episode's list is sorted by:
    1. Preferred quality match (if specified)
    2. Number of seeders (descending)
    """
    episodes_map: Dict[int, List[Torrent]] = {}

    for t in torrents:
        # Check if matches target season
        if t.season != target_season:
            continue
        # Only episodic torrents
        if not t.episodes:
            continue

        for ep in t.episodes:
            if ep not in episodes_map:
                episodes_map[ep] = []
            episodes_map[ep].append(t)

    # Sort candidates for each episode
    for ep in episodes_map:
        def sort_key(item: Torrent):
            quality_score = 1 if (preferred_quality and preferred_quality.lower() in item.quality.lower()) else 0
            return (quality_score, item.seeders)

        episodes_map[ep].sort(key=sort_key, reverse=True)

    return episodes_map


def get_season_packs(torrents: List[Torrent], target_season: int) -> List[Torrent]:
    """Return torrents that are full season packs for the target season."""
    packs = [
        t for t in torrents
        if t.season == target_season and t.is_season_pack
    ]
    packs.sort(key=lambda x: x.seeders, reverse=True)
    return packs


def get_episode_quality_variants(
    candidates: List[Torrent],
    max_variants: int = 5,
) -> List[Torrent]:
    """
    Extract distinct quality & codec variants for an episode,
    keeping the best-seeded release for each quality.
    """
    seen_keys = set()
    variants: List[Torrent] = []

    for t in candidates:
        key = (t.quality, t.codec)
        if key not in seen_keys:
            seen_keys.add(key)
            variants.append(t)
            if len(variants) >= max_variants:
                break

    # If only 1 variant was found but multiple candidates exist,
    # include other top releases so user has manual choices:
    if len(variants) < 3 and len(candidates) > len(variants):
        for t in candidates:
            if t not in variants:
                variants.append(t)
                if len(variants) >= 3:
                    break

    return variants

