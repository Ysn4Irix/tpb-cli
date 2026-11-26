package com.ysn4irix.tpb.data.local

import androidx.datastore.preferences.core.PreferenceDataStoreFactory
import com.ysn4irix.tpb.domain.model.SearchMode
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.TestScope
import kotlinx.coroutines.test.UnconfinedTestDispatcher
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder

@OptIn(ExperimentalCoroutinesApi::class)
class TpbPreferencesRepositoryTest {
    @get:Rule
    val tempFolder = TemporaryFolder()

    @Test
    fun settingsHistoryAndBookmarksPersistCleanly() = runTest {
        val dataStoreFile = tempFolder.newFile("test_prefs.preferences_pb")
        val dataStore = PreferenceDataStoreFactory.create(
            scope = TestScope(UnconfinedTestDispatcher(testScheduler)),
            produceFile = { dataStoreFile },
        )
        val repo = TpbPreferencesRepository(dataStore)

        repo.saveSettings(
            darkTheme = false,
            apiUrl = "https://mirror.example.org/",
            proxyUrl = "socks5://127.0.0.1:9050",
            defaultQuality = "2160p",
        )
        val saved = repo.settingsFlow.first()
        assertFalse(saved.darkTheme)
        assertEquals("https://mirror.example.org", saved.apiUrl)
        assertEquals("socks5://127.0.0.1:9050", saved.proxyUrl)
        assertEquals("2160p", saved.defaultQuality)

        repo.addSearchHistory("Severance", SearchMode.TV)
        repo.addSearchHistory("Inception", SearchMode.MOVIE)
        repo.addSearchHistory("severance", SearchMode.TV)
        val history = repo.historyFlow.first()
        assertEquals(2, history.size)
        assertEquals("severance", history[0].query)

        assertTrue(repo.toggleBookmark("Severance", SearchMode.TV))
        assertEquals(1, repo.bookmarksFlow.first().size)
        assertFalse(repo.toggleBookmark("severance", SearchMode.TV))
        assertEquals(0, repo.bookmarksFlow.first().size)

        repo.clearHistory()
        assertEquals(0, repo.historyFlow.first().size)
    }
}
