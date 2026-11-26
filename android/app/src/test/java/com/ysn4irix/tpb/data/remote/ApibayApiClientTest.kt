package com.ysn4irix.tpb.data.remote

import com.ysn4irix.tpb.domain.model.SearchMode
import kotlinx.coroutines.test.runTest
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import java.net.Proxy

class ApibayApiClientTest {
    private lateinit var server: MockWebServer

    @Before
    fun setUp() {
        server = MockWebServer()
        server.start()
    }

    @After
    fun tearDown() {
        server.shutdown()
    }

    @Test
    fun validatesUrlsAndProxyConfiguration() {
        assertEquals("https://apibay.org", NetworkValidator.validateHttpUrl("https://apibay.org/"))
        assertTrue(NetworkValidator.isCleartextHttp("http://192.168.1.10:8080"))
        assertNull(NetworkValidator.validateProxyUrl("   "))

        val socks = NetworkValidator.validateProxyUrl("socks5://127.0.0.1:9050")
        assertEquals(Proxy.Type.SOCKS, socks?.type)
        assertEquals("127.0.0.1", socks?.host)
        assertEquals(9050, socks?.port)

        val badScheme = runCatching { NetworkValidator.validateHttpUrl("ftp://bad.org") }
        assertTrue(badScheme.isFailure)

        val badProxy = runCatching { NetworkValidator.validateProxyUrl("javascript:alert(1)") }
        assertTrue(badProxy.isFailure)
    }

    @Test
    fun searchFallbackAndCachingWorkViaMockServer() = runTest {
        server.enqueue(
            MockResponse().setResponseCode(200).setBody(
                """[{"id":"0","name":"No results returned","info_hash":"0000000000000000000000000000000000000000","seeders":"0","leechers":"0","size":"0"}]""",
            ),
        )
        server.enqueue(
            MockResponse().setResponseCode(200).setBody(
                """[{"id":"42","name":"Severance.S01E01.1080p.WEB.x265","info_hash":"1111111111111111111111111111111111111111","seeders":"250","leechers":"12","size":"1073741824","username":"VIPUser","status":"vip"}]""",
            ),
        )

        val client = ApibayApiClient(initialBaseUrl = server.url("/").toString())
        val first = client.searchWithFallback("Severance", SearchMode.TV)
        assertEquals(1, first.size)
        assertEquals("1080p", first.first().quality)
        assertEquals("x265", first.first().codec)
        assertEquals(2, server.requestCount)

        // Second lookup on primary category is served from cache
        val cached = client.search("Severance", category = SearchMode.GENERAL.categoryCode)
        assertEquals(1, cached.size)
        assertEquals(2, server.requestCount)

        val req1 = server.takeRequest()
        val req2 = server.takeRequest()
        assertTrue(req1.path.orEmpty().contains("cat=208"))
        assertTrue(req2.path.orEmpty().contains("cat=0"))
    }

    @Test
    fun getParsedFilesNormalizesListAndScalarShapes() = runTest {
        server.enqueue(
            MockResponse().setResponseCode(200).setBody(
                """[{"name":["Season 1","Show.S01E01.mkv"],"size":["1048576"]},{"name":"README.txt","size":512},{"name":["File list not found"],"size":[0]}]""",
            ),
        )
        val client = ApibayApiClient(initialBaseUrl = server.url("/").toString())
        val files = client.getParsedFiles("77")
        assertEquals(2, files.size)
        assertEquals("Season 1/Show.S01E01.mkv", files[0].name)
        assertEquals(1048576L, files[0].sizeBytes)
        assertEquals("README.txt", files[1].name)
        assertEquals(512L, files[1].sizeBytes)
    }
}
