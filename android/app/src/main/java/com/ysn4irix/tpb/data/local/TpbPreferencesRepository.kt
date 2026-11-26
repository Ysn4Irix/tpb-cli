package com.ysn4irix.tpb.data.local

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.emptyPreferences
import androidx.datastore.preferences.core.stringPreferencesKey
import com.ysn4irix.tpb.data.remote.ApibayApiClient
import com.ysn4irix.tpb.data.remote.NetworkValidator
import com.ysn4irix.tpb.domain.model.AppSettings
import com.ysn4irix.tpb.domain.model.BookmarkEntry
import com.ysn4irix.tpb.domain.model.SearchHistoryEntry
import com.ysn4irix.tpb.domain.model.SearchMode
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.map
import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import java.io.IOException
import java.time.Instant
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter
import java.util.Locale

@Serializable
private data class HistoryDto(
    val query: String,
    val mode: String,
    val timestamp: String,
)

@Serializable
private data class BookmarkDto(
    val title: String,
    val mode: String,
    val addedAt: String,
)

class TpbPreferencesRepository(
    private val dataStore: DataStore<Preferences>,
) {
    private val json = Json { ignoreUnknownKeys = true }

    private val safeData: Flow<Preferences> = dataStore.data.catch { exc ->
        if (exc is IOException) emit(emptyPreferences()) else throw exc
    }

    val settingsFlow: Flow<AppSettings> = safeData.map { prefs ->
        AppSettings(
            darkTheme = prefs[KEY_DARK_THEME] ?: true,
            apiUrl = prefs[KEY_API_URL] ?: ApibayApiClient.DEFAULT_BASE_URL,
            proxyUrl = prefs[KEY_PROXY_URL].orEmpty(),
            defaultQuality = prefs[KEY_DEFAULT_QUALITY] ?: "1080p",
        )
    }

    val historyFlow: Flow<List<SearchHistoryEntry>> = safeData.map { prefs ->
        decodeHistory(prefs[KEY_HISTORY_JSON])
            .map { dto ->
                SearchHistoryEntry(
                    query = dto.query,
                    mode = parseMode(dto.mode),
                    timestamp = dto.timestamp,
                )
            }
    }

    val bookmarksFlow: Flow<List<BookmarkEntry>> = safeData.map { prefs ->
        decodeBookmarks(prefs[KEY_BOOKMARKS_JSON])
            .map { dto ->
                BookmarkEntry(
                    title = dto.title,
                    mode = parseMode(dto.mode),
                    addedAt = dto.addedAt,
                )
            }
    }

    suspend fun saveSettings(
        darkTheme: Boolean,
        apiUrl: String,
        proxyUrl: String,
        defaultQuality: String,
    ) {
        val validUrl = NetworkValidator.validateHttpUrl(apiUrl)
        val validProxy = NetworkValidator.validateProxyUrl(proxyUrl)?.normalizedUrl.orEmpty()
        val quality = if (defaultQuality in VALID_QUALITIES) defaultQuality else "1080p"

        dataStore.edit { prefs ->
            prefs[KEY_DARK_THEME] = darkTheme
            prefs[KEY_API_URL] = validUrl
            prefs[KEY_PROXY_URL] = validProxy
            prefs[KEY_DEFAULT_QUALITY] = quality
        }
    }

    suspend fun setDarkTheme(darkTheme: Boolean) {
        dataStore.edit { prefs ->
            prefs[KEY_DARK_THEME] = darkTheme
        }
    }

    suspend fun addSearchHistory(query: String, mode: SearchMode) {
        val clean = query.trim()
        if (clean.isEmpty()) return

        val nowIso = TIMESTAMP_FORMATTER.format(Instant.now())
        dataStore.edit { prefs ->
            val current = decodeHistory(prefs[KEY_HISTORY_JSON])
                .filterNot {
                    it.query.equals(clean, ignoreCase = true) && parseMode(it.mode) == mode
                }
            val updated = listOf(HistoryDto(clean, mode.name, nowIso)) + current
            prefs[KEY_HISTORY_JSON] = json.encodeToString(updated.take(MAX_HISTORY))
        }
    }

    suspend fun clearHistory() {
        dataStore.edit { prefs ->
            prefs[KEY_HISTORY_JSON] = "[]"
        }
    }

    suspend fun toggleBookmark(title: String, mode: SearchMode): Boolean {
        val clean = title.trim()
        if (clean.isEmpty()) return false

        var added = false
        val dateIso = DATE_FORMATTER.format(Instant.now())
        dataStore.edit { prefs ->
            val current = decodeBookmarks(prefs[KEY_BOOKMARKS_JSON])
            val exists = current.any {
                it.title.equals(clean, ignoreCase = true) && parseMode(it.mode) == mode
            }
            val updated = if (exists) {
                added = false
                current.filterNot {
                    it.title.equals(clean, ignoreCase = true) && parseMode(it.mode) == mode
                }
            } else {
                added = true
                listOf(BookmarkDto(clean, mode.name, dateIso)) + current
            }
            prefs[KEY_BOOKMARKS_JSON] = json.encodeToString(updated)
        }
        return added
    }

    suspend fun removeBookmark(title: String, mode: SearchMode) {
        val clean = title.trim()
        dataStore.edit { prefs ->
            val current = decodeBookmarks(prefs[KEY_BOOKMARKS_JSON])
            val updated = current.filterNot {
                it.title.equals(clean, ignoreCase = true) && parseMode(it.mode) == mode
            }
            prefs[KEY_BOOKMARKS_JSON] = json.encodeToString(updated)
        }
    }

    private fun decodeHistory(raw: String?): List<HistoryDto> {
        if (raw.isNullOrBlank()) return emptyList()
        return runCatching { json.decodeFromString<List<HistoryDto>>(raw) }
            .getOrDefault(emptyList())
    }

    private fun decodeBookmarks(raw: String?): List<BookmarkDto> {
        if (raw.isNullOrBlank()) return emptyList()
        return runCatching { json.decodeFromString<List<BookmarkDto>>(raw) }
            .getOrDefault(emptyList())
    }

    private fun parseMode(raw: String): SearchMode =
        SearchMode.entries.firstOrNull { it.name.equals(raw, ignoreCase = true) } ?: SearchMode.TV

    companion object {
        private const val MAX_HISTORY = 25
        private val VALID_QUALITIES = setOf("Any", "2160p", "1080p", "720p", "480p")

        private val KEY_DARK_THEME = booleanPreferencesKey("dark_theme")
        private val KEY_API_URL = stringPreferencesKey("api_url")
        private val KEY_PROXY_URL = stringPreferencesKey("proxy_url")
        private val KEY_DEFAULT_QUALITY = stringPreferencesKey("default_quality")
        private val KEY_HISTORY_JSON = stringPreferencesKey("history_json")
        private val KEY_BOOKMARKS_JSON = stringPreferencesKey("bookmarks_json")

        private val TIMESTAMP_FORMATTER: DateTimeFormatter =
            DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm 'UTC'", Locale.US)
                .withZone(ZoneOffset.UTC)
        private val DATE_FORMATTER: DateTimeFormatter =
            DateTimeFormatter.ofPattern("yyyy-MM-dd", Locale.US).withZone(ZoneOffset.UTC)
    }
}
