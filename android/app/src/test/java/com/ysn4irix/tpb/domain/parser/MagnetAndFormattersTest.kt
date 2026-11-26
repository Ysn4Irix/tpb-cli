package com.ysn4irix.tpb.domain.parser

import com.ysn4irix.tpb.domain.model.Torrent
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class MagnetAndFormattersTest {
    @Test
    fun torrentMagnetUriAndHelpersMatchCliOutput() {
        val torrent = Torrent(
            id = "12345",
            name = "Severance S01E01 1080p",
            infoHash = "ABCDEF1234567890ABCDEF1234567890ABCDEF12",
            leechers = 10,
            seeders = 150,
            sizeBytes = 1024L * 1024L * 1500L,
            username = "VIP_User",
            added = 1700000000L,
            status = "vip",
        )

        val magnet = torrent.magnetLink
        assertTrue(magnet.startsWith("magnet:?xt=urn:btih:ABCDEF1234567890ABCDEF1234567890ABCDEF12"))
        assertTrue("dn=Severance%20S01E01%201080p" in magnet)
        assertTrue("tr=udp%3A%2F%2Ftracker.opentrackr.org%3A1337%2Fannounce" in magnet)
        assertTrue(torrent.isVip)
        assertEquals("1.46 GiB", torrent.humanSize)
        assertEquals("2023-11-14", torrent.formattedDate)

        val doc = formatMagnetsDocument(listOf(torrent))
        assertTrue("# Severance S01E01 1080p | Size: 1.46 GiB | Seeds: 150" in doc)
        assertTrue(magnet in doc)
    }

    @Test
    fun dummyZeroHashProducesEmptyMagnetAndSlugSanitizes() {
        val dummy = Torrent(
            id = "0",
            name = "No results returned",
            infoHash = "0000000000000000000000000000000000000000",
            leechers = 0,
            seeders = 0,
            sizeBytes = 0L,
        )
        assertEquals("", dummy.magnetLink)
        assertEquals("mr_robot_us", sanitizeFilename("Mr. Robot (US)!"))
        assertEquals("torrents", sanitizeFilename("!!!"))
    }
}
