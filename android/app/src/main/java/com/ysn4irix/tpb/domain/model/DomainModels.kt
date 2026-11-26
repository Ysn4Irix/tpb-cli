package com.ysn4irix.tpb.domain.model

import com.ysn4irix.tpb.domain.parser.MagnetBuilder
import com.ysn4irix.tpb.domain.parser.formatBytes
import com.ysn4irix.tpb.domain.parser.formatUnixDateUtc

enum class SearchMode(val categoryCode: String, val label: String) {
    TV(categoryCode = "208", label = "TV Series"),
    MOVIE(categoryCode = "207", label = "Movies"),
    GENERAL(categoryCode = "0", label = "General"),
}

data class Torrent(
    val id: String,
    val name: String,
    val infoHash: String,
    val leechers: Int,
    val seeders: Int,
    val sizeBytes: Long,
    val username: String = "",
    val added: Long = 0L,
    val status: String = "member",
    val category: String = "0",
    val imdb: String = "",
    val season: Int? = null,
    val episode: Int? = null,
    val episodes: List<Int> = emptyList(),
    val isSeasonPack: Boolean = false,
    val quality: String = "Unknown",
    val codec: String = "Unknown",
) {
    val magnetLink: String
        get() = MagnetBuilder.build(name = name, infoHash = infoHash)

    val humanSize: String
        get() = formatBytes(sizeBytes)

    val formattedDate: String
        get() = formatUnixDateUtc(added)

    val isVip: Boolean
        get() = status.equals("vip", ignoreCase = true)

    val isTrusted: Boolean
        get() = status.equals("trusted", ignoreCase = true)

    val isHealthy: Boolean
        get() = seeders > 50

    val isModerateHealth: Boolean
        get() = seeders in 6..50
}

data class TorrentFile(
    val name: String,
    val sizeBytes: Long,
) {
    val humanSize: String
        get() = formatBytes(sizeBytes)
}

data class TvSeasonSummary(
    val season: Int,
    val episodes: Set<Int>,
    val packs: List<Torrent>,
    val torrents: List<Torrent>,
    val totalTorrents: Int,
    val qualities: List<String>,
    val maxSeeders: Int,
)

data class AppSettings(
    val darkTheme: Boolean = true,
    val apiUrl: String = "https://apibay.org",
    val proxyUrl: String = "",
    val defaultQuality: String = "1080p",
)

data class SearchHistoryEntry(
    val query: String,
    val mode: SearchMode,
    val timestamp: String,
)

data class BookmarkEntry(
    val title: String,
    val mode: SearchMode,
    val addedAt: String,
)
