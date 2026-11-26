package com.ysn4irix.tpb.domain.parser

import com.ysn4irix.tpb.domain.model.Torrent
import com.ysn4irix.tpb.domain.model.TvSeasonSummary
import java.util.Locale

data class ParsedTvMetadata(
    val season: Int?,
    val episode: Int?,
    val episodes: List<Int>,
    val isSeasonPack: Boolean,
)

object TitleParser {
    private val qualityPatterns: List<Pair<Regex, String>> = listOf(
        Regex("\\b(2160p|4k|uhd)\\b", RegexOption.IGNORE_CASE) to "2160p",
        Regex("\\b(1080p|fhd|1080i)\\b", RegexOption.IGNORE_CASE) to "1080p",
        Regex("\\b(720p|hd)\\b", RegexOption.IGNORE_CASE) to "720p",
        Regex("\\b(480p|576p|dvdrip|dvdr|sd)\\b", RegexOption.IGNORE_CASE) to "480p",
    )

    private val codecPatterns: List<Pair<Regex, String>> = listOf(
        Regex("\\b(x265|hevc|h\\.?\\s*265)\\b", RegexOption.IGNORE_CASE) to "x265",
        Regex("\\b(x264|avc|h\\.?\\s*264)\\b", RegexOption.IGNORE_CASE) to "x264",
        Regex("\\b(xvid|divx)\\b", RegexOption.IGNORE_CASE) to "XviD",
        Regex("\\b(av1)\\b", RegexOption.IGNORE_CASE) to "AV1",
    )

    private val episodeRegexMulti = Regex(
        "\\b[sS](\\d{1,2})[eE](\\d{1,2})(?:-[eE]?(\\d{1,2}))?\\b",
    )
    private val episodeRegexX = Regex("\\b(\\d{1,2})x(\\d{1,2})\\b")
    private val multiSeasonPackRegex = Regex(
        "\\b[sS](\\d{1,2})\\s*-\\s*[sS]?(\\d{1,2})\\b",
        RegexOption.IGNORE_CASE,
    )
    private val seasonPackRegex = Regex(
        "(?:(?:\\b|(?<=_))[sS]eason[\\s._-]*(\\d{1,2})(?:\\b|(?=_))|(?:\\b|(?<=_))[sS](\\d{1,2})(?:\\b|(?=_)))",
        RegexOption.IGNORE_CASE,
    )
    private val regionTagRegex = Regex(
        "\\b(US|UK|AU|NZ|CA)\\b",
        RegexOption.IGNORE_CASE,
    )

    fun detectQuality(name: String): String {
        for ((pattern, label) in qualityPatterns) {
            if (pattern.containsMatchIn(name)) return label
        }
        return "Unknown"
    }

    fun detectCodec(name: String): String {
        for ((pattern, label) in codecPatterns) {
            if (pattern.containsMatchIn(name)) return label
        }
        return "Unknown"
    }

    fun parseTvMetadata(name: String): ParsedTvMetadata {
        val multi = episodeRegexMulti.find(name)
        if (multi != null) {
            val season = multi.groupValues[1].toInt()
            val epStart = multi.groupValues[2].toInt()
            val epEndStr = multi.groupValues[3]
            val episodes = if (epEndStr.isNotEmpty()) {
                val epEnd = epEndStr.toInt()
                if (epEnd >= epStart) (epStart..epEnd).toList() else listOf(epStart)
            } else {
                listOf(epStart)
            }
            return ParsedTvMetadata(season, episodes.first(), episodes, isSeasonPack = false)
        }

        val xMatch = episodeRegexX.find(name)
        if (xMatch != null) {
            val season = xMatch.groupValues[1].toInt()
            val ep = xMatch.groupValues[2].toInt()
            return ParsedTvMetadata(season, ep, listOf(ep), isSeasonPack = false)
        }

        val multiSeason = multiSeasonPackRegex.find(name)
        if (multiSeason != null) {
            val startSeason = multiSeason.groupValues[1].toInt()
            return ParsedTvMetadata(startSeason, null, emptyList(), isSeasonPack = true)
        }

        val packMatch = seasonPackRegex.find(name)
        if (packMatch != null) {
            val seasonStr = packMatch.groupValues[1].ifEmpty { packMatch.groupValues[2] }
            if (seasonStr.isNotEmpty()) {
                return ParsedTvMetadata(seasonStr.toInt(), null, emptyList(), isSeasonPack = true)
            }
        }

        return ParsedTvMetadata(null, null, emptyList(), isSeasonPack = false)
    }

    fun enrichTorrent(torrent: Torrent): Torrent {
        val meta = parseTvMetadata(torrent.name)
        return torrent.copy(
            quality = detectQuality(torrent.name),
            codec = detectCodec(torrent.name),
            season = meta.season,
            episode = meta.episode,
            episodes = meta.episodes,
            isSeasonPack = meta.isSeasonPack,
        )
    }

    fun filterAndGroupEpisodes(
        torrents: List<Torrent>,
        targetSeason: Int,
        preferredQuality: String? = null,
    ): Map<Int, List<Torrent>> {
        val grouped = linkedMapOf<Int, MutableList<Torrent>>()
        for (torrent in torrents) {
            if (torrent.season != targetSeason || torrent.episodes.isEmpty()) continue
            for (ep in torrent.episodes) {
                grouped.getOrPut(ep) { mutableListOf() }.add(torrent)
            }
        }

        val prefLower = preferredQuality?.takeIf {
            it.isNotBlank() && !it.equals("Any", ignoreCase = true)
        }?.lowercase(Locale.US)

        return grouped.keys.sorted().associateWith { ep ->
            grouped.getValue(ep).sortedWith(
                compareByDescending<Torrent> { item ->
                    if (prefLower != null && item.quality.lowercase(Locale.US).contains(prefLower)) 1 else 0
                }.thenByDescending { it.seeders },
            )
        }
    }

    fun getSeasonPacks(torrents: List<Torrent>, targetSeason: Int): List<Torrent> =
        torrents
            .filter { it.season == targetSeason && it.isSeasonPack }
            .sortedByDescending { it.seeders }

    fun getEpisodeQualityVariants(
        candidates: List<Torrent>,
        maxVariants: Int = 5,
    ): List<Torrent> {
        val seenKeys = mutableSetOf<Pair<String, String>>()
        val variants = mutableListOf<Torrent>()

        for (candidate in candidates) {
            val key = candidate.quality to candidate.codec
            if (seenKeys.add(key)) {
                variants.add(candidate)
                if (variants.size >= maxVariants) break
            }
        }

        if (variants.size < 3 && candidates.size > variants.size) {
            for (candidate in candidates) {
                if (candidate !in variants) {
                    variants.add(candidate)
                    if (variants.size >= 3) break
                }
            }
        }

        return variants
    }

    fun getDetectedSeasonsSummary(torrents: List<Torrent>): Map<Int, TvSeasonSummary> {
        class Bucket(val season: Int) {
            val episodes = sortedSetOf<Int>()
            val packs = mutableListOf<Torrent>()
            val all = mutableListOf<Torrent>()
            val qualities = sortedSetOf<String>()
            var total = 0
            var maxSeeders = 0
        }

        val buckets = sortedMapOf<Int, Bucket>()
        for (raw in torrents) {
            val t = if (raw.season == null) enrichTorrent(raw) else raw
            val s = t.season ?: continue
            if (s <= 0) continue

            val bucket = buckets.getOrPut(s) { Bucket(s) }
            bucket.all.add(t)
            bucket.total += 1
            if (t.quality.isNotEmpty() && t.quality != "Unknown") {
                bucket.qualities.add(t.quality)
            }
            if (t.seeders > bucket.maxSeeders) {
                bucket.maxSeeders = t.seeders
            }
            if (t.isSeasonPack) {
                bucket.packs.add(t)
            }
            if (t.episodes.isNotEmpty()) {
                bucket.episodes.addAll(t.episodes)
            }
        }

        return buckets.mapValues { (_, bucket) ->
            TvSeasonSummary(
                season = bucket.season,
                episodes = bucket.episodes.toSet(),
                packs = bucket.packs.sortedByDescending { it.seeders },
                torrents = bucket.all.toList(),
                totalTorrents = bucket.total,
                qualities = bucket.qualities.toList(),
                maxSeeders = bucket.maxSeeders,
            )
        }
    }

    fun detectSeriesVariants(torrents: List<Torrent>): Map<String, List<Torrent>> {
        val groups = linkedMapOf<String, MutableList<Torrent>>()
        for (t in torrents) {
            val match = regionTagRegex.find(t.name) ?: continue
            val tag = match.groupValues[1].uppercase(Locale.US)
            groups.getOrPut(tag) { mutableListOf() }.add(t)
        }
        val significant = groups.filterValues { it.size >= 2 }
        return if (significant.size >= 2) significant else emptyMap()
    }
}
