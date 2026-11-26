package com.ysn4irix.tpb.domain.parser

import com.ysn4irix.tpb.domain.model.Torrent
import java.net.URLEncoder
import java.nio.charset.StandardCharsets
import java.time.Instant
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter
import java.util.Locale

private val BYTE_UNITS = arrayOf("B", "KiB", "MiB", "GiB", "TiB")
private val DATE_FORMATTER: DateTimeFormatter =
    DateTimeFormatter.ofPattern("yyyy-MM-dd", Locale.US).withZone(ZoneOffset.UTC)
private val NON_WORD_REGEX = Regex("[^\\w\\s-]")
private val WHITESPACE_OR_UNDERSCORE_REGEX = Regex("[\\s_]+")

fun formatBytes(sizeBytes: Long): String {
    var value = sizeBytes.coerceAtLeast(0L).toDouble()
    for (unit in BYTE_UNITS) {
        if (value < 1024.0 || unit == "TiB") {
            return if (unit == "B") {
                String.format(Locale.US, "%d B", value.toInt())
            } else {
                String.format(Locale.US, "%.2f %s", value, unit)
            }
        }
        value /= 1024.0
    }
    return String.format(Locale.US, "%d B", sizeBytes.coerceAtLeast(0L))
}

fun sanitizeFilename(name: String): String {
    val clean = NON_WORD_REGEX.replace(name.lowercase(Locale.US), "")
    val slug = WHITESPACE_OR_UNDERSCORE_REGEX.replace(clean, "_").trim('_')
    return slug.ifEmpty { "torrents" }
}

fun formatUnixDateUtc(epochSeconds: Long): String {
    if (epochSeconds <= 0L) return "N/A"
    return runCatching {
        DATE_FORMATTER.format(Instant.ofEpochSecond(epochSeconds))
    }.getOrDefault("N/A")
}

fun formatMagnetsDocument(
    torrents: List<Torrent>,
    includeMetadataComments: Boolean = true,
): String {
    val valid = torrents.filter { it.magnetLink.isNotEmpty() }
    if (valid.isEmpty()) return ""
    return buildString {
        valid.forEach { torrent ->
            if (includeMetadataComments) {
                append("# ")
                append(torrent.name)
                append(" | Size: ")
                append(torrent.humanSize)
                append(" | Seeds: ")
                append(torrent.seeders)
                append('\n')
            }
            append(torrent.magnetLink)
            append("\n\n")
        }
    }
}

object MagnetBuilder {
    private const val ZERO_HASH = "0000000000000000000000000000000000000000"

    val DEFAULT_TRACKERS: List<String> = listOf(
        "udp://tracker.opentrackr.org:1337/announce",
        "udp://open.stealth.si:80/announce",
        "udp://tracker.torrent.eu.org:451/announce",
        "udp://tracker.bittor.pw:1337/announce",
        "udp://public.popcorn-tracker.org:6969/announce",
        "udp://tracker.dler.org:6969/announce",
        "udp://exodus.desync.com:6969/announce",
        "udp://open.demonii.com:1337/announce",
    )

    fun build(name: String, infoHash: String): String {
        val cleanHash = infoHash.trim()
        if (cleanHash.isEmpty() || cleanHash == ZERO_HASH) {
            return ""
        }
        val encodedName = rfc3986Encode(name)
        val params = buildList {
            add("xt=urn:btih:$cleanHash")
            add("dn=$encodedName")
            DEFAULT_TRACKERS.forEach { tracker ->
                add("tr=${rfc3986Encode(tracker)}")
            }
        }
        return "magnet:?${params.joinToString("&")}"
    }

    private fun rfc3986Encode(value: String): String =
        URLEncoder.encode(value, StandardCharsets.UTF_8.name())
            .replace("+", "%20")
}
