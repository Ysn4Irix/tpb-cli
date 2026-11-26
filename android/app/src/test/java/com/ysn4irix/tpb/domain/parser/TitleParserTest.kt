package com.ysn4irix.tpb.domain.parser

import com.ysn4irix.tpb.domain.model.Torrent
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class TitleParserTest {
    private fun torrent(
        id: String,
        name: String,
        seeders: Int = 10,
        sizeBytes: Long = 1000L,
    ): Torrent = TitleParser.enrichTorrent(
        Torrent(
            id = id,
            name = name,
            infoHash = "${id.padStart(40, '0')}",
            leechers = 1,
            seeders = seeders,
            sizeBytes = sizeBytes,
        ),
    )

    @Test
    fun detectQualityMatchesPythonParity() {
        assertEquals("2160p", TitleParser.detectQuality("Movie.2024.2160p.UHD.BluRay"))
        assertEquals("1080p", TitleParser.detectQuality("Show.S01E01.1080p.WEBRip"))
        assertEquals("720p", TitleParser.detectQuality("Show.S01E02.720p.HDTV"))
        assertEquals("480p", TitleParser.detectQuality("Classic.Movie.DVDRip.xvid"))
        assertEquals("Unknown", TitleParser.detectQuality("Unknown.Video.File"))
    }

    @Test
    fun detectCodecMatchesPythonParity() {
        assertEquals("x265", TitleParser.detectCodec("Show.S01.1080p.x265.HEVC"))
        assertEquals("x264", TitleParser.detectCodec("Movie.720p.H.264"))
        assertEquals("XviD", TitleParser.detectCodec("Old.Film.XviD"))
        assertEquals("AV1", TitleParser.detectCodec("Modern.4k.AV1"))
    }

    @Test
    fun parseTvMetadataHandlesEpisodesMultiEpisodeAndPacks() {
        val single = TitleParser.parseTvMetadata("Severance.S01E05.1080p")
        assertEquals(1, single.season)
        assertEquals(5, single.episode)
        assertEquals(listOf(5), single.episodes)
        assertFalse(single.isSeasonPack)

        val multi = TitleParser.parseTvMetadata("Show.S02E01-E03.720p")
        assertEquals(2, multi.season)
        assertEquals(listOf(1, 2, 3), multi.episodes)
        assertFalse(multi.isSeasonPack)

        val altX = TitleParser.parseTvMetadata("The.Wire.1x04.HDTV")
        assertEquals(1, altX.season)
        assertEquals(listOf(4), altX.episodes)
        assertFalse(altX.isSeasonPack)

        val pack = TitleParser.parseTvMetadata("Severance - Season 1 - 1080p")
        assertEquals(1, pack.season)
        assertNull(pack.episode)
        assertTrue(pack.isSeasonPack)

        val shortPack = TitleParser.parseTvMetadata("Show.Name.S03.1080p.BluRay")
        assertEquals(3, shortPack.season)
        assertTrue(shortPack.isSeasonPack)
    }

    @Test
    fun filterGroupVariantsSummaryAndRegionalDisambiguation() {
        val us1 = torrent("1", "The.Office.US.S01E01.720p.x264", seeders = 100)
        val us2 = torrent("2", "The.Office.US.S01E01.1080p.x265", seeders = 60)
        val us3 = torrent("3", "The.Office.US.Season.1.Complete.1080p", seeders = 250)
        val uk1 = torrent("4", "The.Office.UK.S01E01.720p", seeders = 90)
        val uk2 = torrent("5", "The.Office.UK.S02E01.720p", seeders = 70)

        val variants = TitleParser.detectSeriesVariants(listOf(us1, us2, us3, uk1, uk2))
        assertTrue("US" in variants && "UK" in variants)
        assertEquals(3, variants.getValue("US").size)
        assertEquals(emptyMap<String, List<Torrent>>(), TitleParser.detectSeriesVariants(listOf(us1, us2)))

        val grouped = TitleParser.filterAndGroupEpisodes(
            torrents = listOf(us1, us2, us3),
            targetSeason = 1,
            preferredQuality = "1080p",
        )
        assertEquals("1080p", grouped.getValue(1).first().quality)

        val epVariants = TitleParser.getEpisodeQualityVariants(grouped.getValue(1))
        assertEquals(2, epVariants.size)
        assertEquals("2", epVariants.first().id)

        val packs = TitleParser.getSeasonPacks(listOf(us1, us2, us3), targetSeason = 1)
        assertEquals(listOf("3"), packs.map { it.id })

        val summary = TitleParser.getDetectedSeasonsSummary(listOf(us1, us2, us3, uk2))
        assertTrue(1 in summary && 2 in summary)
        assertEquals(setOf(1), summary.getValue(1).episodes)
        assertEquals(1, summary.getValue(1).packs.size)
    }
}
