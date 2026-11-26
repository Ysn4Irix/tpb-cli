package com.ysn4irix.tpb.ui

import androidx.datastore.preferences.core.PreferenceDataStoreFactory
import com.ysn4irix.tpb.data.local.TpbPreferencesRepository
import com.ysn4irix.tpb.data.remote.ApibayApiClient
import com.ysn4irix.tpb.domain.model.SearchMode
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.TestScope
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder

@OptIn(ExperimentalCoroutinesApi::class)
class TpbViewModelTest {
    @get:Rule
    val tempFolder = TemporaryFolder()

    private val testDispatcher = StandardTestDispatcher()
    private lateinit var server: MockWebServer

    @Before
    fun setUp() {
        Dispatchers.setMain(testDispatcher)
        server = MockWebServer()
        server.start()
    }

    @After
    fun tearDown() {
        server.shutdown()
        Dispatchers.resetMain()
    }

    @Test
    fun tvSearchStartsUncheckedSupportsRecommendedAndSingleQualityPerEpisode() = runTest(testDispatcher) {
        val dsFile = tempFolder.newFile("vm_prefs.preferences_pb")
        val ds = PreferenceDataStoreFactory.create(
            scope = TestScope(UnconfinedTestDispatcher(testScheduler)),
            produceFile = { dsFile },
        )
        val repo = TpbPreferencesRepository(ds)
        val mirrorUrl = server.url("/").toString().trimEnd('/')
        repo.saveSettings(
            darkTheme = true,
            apiUrl = mirrorUrl,
            proxyUrl = "",
            defaultQuality = "1080p",
        )
        val client = ApibayApiClient(initialBaseUrl = mirrorUrl)

        server.enqueue(
            MockResponse().setResponseCode(200).setBody(
                """[
                    {"id":"1","name":"Severance.S01E01.1080p.WEB.x265","info_hash":"1111111111111111111111111111111111111111","seeders":"200","leechers":"5","size":"1500000000"},
                    {"id":"2","name":"Severance.S01E01.720p.WEB.x264","info_hash":"2222222222222222222222222222222222222222","seeders":"90","leechers":"2","size":"800000000"},
                    {"id":"3","name":"Severance.S01E02.1080p.WEB.x265","info_hash":"3333333333333333333333333333333333333333","seeders":"160","leechers":"4","size":"1400000000"}
                ]""",
            ),
        )

        val vm = TpbViewModel(apiClient = client, preferencesRepository = repo)
        advanceUntilIdle()

        vm.runSearch("Severance", SearchMode.TV)
        advanceUntilIdle()

        val afterSearch = vm.uiState.value
        assertFalse(afterSearch.isSearching)
        assertTrue(afterSearch.hasSearched)
        assertTrue(afterSearch.selectedIds.isEmpty())
        assertEquals(2, afterSearch.episodeVariantsMap.size)

        // Select Recommended selects top quality (1080p) for each episode
        vm.selectRecommendedEpisodes()
        assertEquals(setOf("1", "3"), vm.uiState.value.selectedIds)

        // Selecting alternate quality on E01 auto-deselects sibling id "1"
        vm.toggleEpisodeReleaseSelection(episodeNumber = 1, torrentId = "2")
        assertEquals(setOf("2", "3"), vm.uiState.value.selectedIds)

        vm.clearSelection()
        assertTrue(vm.uiState.value.selectedIds.isEmpty())
    }
}
