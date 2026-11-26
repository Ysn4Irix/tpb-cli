package com.ysn4irix.tpb.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.ysn4irix.tpb.data.local.TpbPreferencesRepository
import com.ysn4irix.tpb.data.remote.ApibayApiClient
import com.ysn4irix.tpb.data.remote.ApibayConnectionException
import com.ysn4irix.tpb.data.remote.ApibayException
import com.ysn4irix.tpb.domain.model.AppSettings
import com.ysn4irix.tpb.domain.model.BookmarkEntry
import com.ysn4irix.tpb.domain.model.SearchHistoryEntry
import com.ysn4irix.tpb.domain.model.SearchMode
import com.ysn4irix.tpb.domain.model.Torrent
import com.ysn4irix.tpb.domain.model.TorrentFile
import com.ysn4irix.tpb.domain.model.TvSeasonSummary
import com.ysn4irix.tpb.domain.parser.TitleParser
import com.ysn4irix.tpb.domain.parser.sanitizeFilename
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

enum class TvSubMode(val label: String) {
    EPISODES("Episodes"),
    PACKS("Season Packs"),
    ALL("All"),
}

enum class ReleaseSort(val label: String) {
    SEEDERS_DESC("Seeds ↓"),
    SIZE_DESC("Size ↓"),
    DATE_DESC("Date ↓"),
    NAME_ASC("Title A–Z"),
}

data class TpbUiState(
    val query: String = "",
    val mode: SearchMode = SearchMode.TV,
    val settings: AppSettings = AppSettings(),
    val history: List<SearchHistoryEntry> = emptyList(),
    val bookmarks: List<BookmarkEntry> = emptyList(),
    val isSearching: Boolean = false,
    val searchElapsedSec: Double = 0.0,
    val searchError: String? = null,
    val hasSearched: Boolean = false,
    val activeSearchQuery: String = "",
    val rawResults: List<Torrent> = emptyList(),
    val seriesVariants: Map<String, List<Torrent>> = emptyMap(),
    val selectedVariantTag: String? = null,
    val seasonsSummary: Map<Int, TvSeasonSummary> = emptyMap(),
    val selectedSeason: Int? = null,
    val tvSubMode: TvSubMode = TvSubMode.EPISODES,
    val tvPreferredQuality: String = "1080p",
    val episodeVariantsMap: Map<Int, List<Torrent>> = emptyMap(),
    val seasonPacks: List<Torrent> = emptyList(),
    val filteredReleaseList: List<Torrent> = emptyList(),
    val listTextFilter: String = "",
    val listQualityFilter: String = "All",
    val listSort: ReleaseSort = ReleaseSort.SEEDERS_DESC,
    val selectedIds: Set<String> = emptySet(),
    val inspectedTorrent: Torrent? = null,
    val isLoadingFiles: Boolean = false,
    val inspectedFiles: List<TorrentFile> = emptyList(),
    val filesError: String? = null,
) {
    val selectedTorrents: List<Torrent>
        get() = rawResults.filter { it.id in selectedIds && it.magnetLink.isNotEmpty() }

    val isCurrentQueryBookmarked: Boolean
        get() {
            val clean = query.trim()
            return clean.isNotEmpty() && bookmarks.any {
                it.title.equals(clean, ignoreCase = true) && it.mode == mode
            }
        }

    val suggestedExportFilename: String
        get() {
            val slug = sanitizeFilename(activeSearchQuery.ifBlank { query }.ifBlank { "torrents" })
            return if (mode == SearchMode.TV && selectedSeason != null) {
                "${slug}_S${selectedSeason.toString().padStart(2, '0')}_magnets.txt"
            } else {
                "${slug}_magnets.txt"
            }
        }
}

private data class SearchSnapshot(
    val activeSearchQuery: String,
    val rawResults: List<Torrent>,
    val selectedIds: Set<String>,
    val selectedVariantTag: String?,
    val selectedSeason: Int?,
    val tvSubMode: TvSubMode,
    val hasSearched: Boolean,
)

class TpbViewModel(
    private val apiClient: ApibayApiClient,
    private val preferencesRepository: TpbPreferencesRepository,
) : ViewModel() {
    private val _uiState = MutableStateFlow(TpbUiState())
    val uiState: StateFlow<TpbUiState> = _uiState.asStateFlow()

    private var activeSearchJob: Job? = null
    private var elapsedTickerJob: Job? = null
    private var activeFilesJob: Job? = null
    private var preSearchSnapshot: SearchSnapshot? = null
    private var initializedClientConfig = false

    init {
        viewModelScope.launch {
            preferencesRepository.settingsFlow.collect { settings ->
                if (!initializedClientConfig ||
                    apiClient.baseUrl != settings.apiUrl ||
                    (apiClient.proxyUrl ?: "") != settings.proxyUrl
                ) {
                    runCatching {
                        apiClient.reconfigure(settings.apiUrl, settings.proxyUrl.ifBlank { null })
                    }
                    initializedClientConfig = true
                }
                _uiState.update { state ->
                    val qualityPref = if (!state.hasSearched) {
                        settings.defaultQuality
                    } else {
                        state.tvPreferredQuality
                    }
                    recomputeDerivedState(
                        state.copy(
                            settings = settings,
                            tvPreferredQuality = qualityPref,
                        ),
                    )
                }
            }
        }

        viewModelScope.launch {
            preferencesRepository.historyFlow.collect { history ->
                _uiState.update { it.copy(history = history) }
            }
        }

        viewModelScope.launch {
            preferencesRepository.bookmarksFlow.collect { bookmarks ->
                _uiState.update { it.copy(bookmarks = bookmarks) }
            }
        }
    }

    fun onQueryChanged(value: String) {
        _uiState.update { it.copy(query = value) }
    }

    fun onModeSelected(mode: SearchMode) {
        _uiState.update { it.copy(mode = mode) }
    }

    fun runSearch(explicitQuery: String? = null, explicitMode: SearchMode? = null) {
        val current = _uiState.value
        val targetQuery = (explicitQuery ?: current.query).trim()
        val targetMode = explicitMode ?: current.mode
        if (targetQuery.isEmpty()) return

        activeSearchJob?.cancel()
        elapsedTickerJob?.cancel()

        preSearchSnapshot = SearchSnapshot(
            activeSearchQuery = current.activeSearchQuery,
            rawResults = current.rawResults,
            selectedIds = current.selectedIds,
            selectedVariantTag = current.selectedVariantTag,
            selectedSeason = current.selectedSeason,
            tvSubMode = current.tvSubMode,
            hasSearched = current.hasSearched,
        )

        _uiState.update {
            it.copy(
                query = targetQuery,
                mode = targetMode,
                isSearching = true,
                searchElapsedSec = 0.0,
                searchError = null,
                selectedIds = emptySet(),
            )
        }

        val ticker = viewModelScope.launch {
            var ticks = 0
            while (isActive) {
                delay(200L)
                ticks += 1
                _uiState.update { it.copy(searchElapsedSec = ticks * 0.2) }
            }
        }
        elapsedTickerJob = ticker

        activeSearchJob = viewModelScope.launch {
            try {
                preferencesRepository.addSearchHistory(targetQuery, targetMode)
                val results = apiClient.searchWithFallback(targetQuery, targetMode)
                ticker.cancel()
                preSearchSnapshot = null
                _uiState.update { state ->
                    val resetState = state.copy(
                        isSearching = false,
                        hasSearched = true,
                        searchError = null,
                        activeSearchQuery = targetQuery,
                        rawResults = results,
                        selectedIds = emptySet(),
                        listTextFilter = "",
                        listQualityFilter = initialListQualityFilter(
                            results = results,
                            preferred = if (targetMode == SearchMode.MOVIE) state.settings.defaultQuality else "All",
                        ),
                        tvPreferredQuality = state.settings.defaultQuality,
                    )
                    reinitializeTvHierarchy(recomputeDerivedState(resetState))
                }
            } catch (_: CancellationException) {
                ticker.cancel()
            } catch (err: ApibayConnectionException) {
                ticker.cancel()
                _uiState.update {
                    it.copy(
                        isSearching = false,
                        hasSearched = true,
                        searchError = err.message ?: "Network connection error.",
                    )
                }
            } catch (err: ApibayException) {
                ticker.cancel()
                _uiState.update {
                    it.copy(
                        isSearching = false,
                        hasSearched = true,
                        searchError = err.message ?: "Apibay search error.",
                    )
                }
            }
        }
    }

    fun cancelSearch() {
        activeSearchJob?.cancel()
        elapsedTickerJob?.cancel()
        activeSearchJob = null
        elapsedTickerJob = null
        val snapshot = preSearchSnapshot
        preSearchSnapshot = null

        _uiState.update { state ->
            if (snapshot != null && snapshot.rawResults.isNotEmpty()) {
                recomputeDerivedState(
                    state.copy(
                        isSearching = false,
                        searchError = null,
                        hasSearched = snapshot.hasSearched,
                        activeSearchQuery = snapshot.activeSearchQuery,
                        rawResults = snapshot.rawResults,
                        selectedIds = snapshot.selectedIds,
                        selectedVariantTag = snapshot.selectedVariantTag,
                        selectedSeason = snapshot.selectedSeason,
                        tvSubMode = snapshot.tvSubMode,
                    ),
                )
            } else {
                state.copy(isSearching = false, searchError = null)
            }
        }
    }

    fun selectVariantTag(tag: String) {
        _uiState.update { state ->
            reinitializeSeasonsOnly(state.copy(selectedVariantTag = tag))
        }
    }

    fun selectSeason(season: Int?) {
        _uiState.update { state ->
            val withSeason = recomputeDerivedState(state.copy(selectedSeason = season))
            val nextSubMode = when {
                season == null -> TvSubMode.ALL
                withSeason.episodeVariantsMap.isNotEmpty() -> TvSubMode.EPISODES
                withSeason.seasonPacks.isNotEmpty() -> TvSubMode.PACKS
                else -> TvSubMode.ALL
            }
            withSeason.copy(tvSubMode = nextSubMode)
        }
    }

    fun selectTvSubMode(subMode: TvSubMode) {
        _uiState.update { state ->
            recomputeDerivedState(state.copy(tvSubMode = subMode))
        }
    }

    fun selectTvPreferredQuality(quality: String) {
        _uiState.update { state ->
            recomputeDerivedState(state.copy(tvPreferredQuality = quality))
        }
    }

    fun onListTextFilterChanged(filter: String) {
        _uiState.update { state ->
            recomputeDerivedState(state.copy(listTextFilter = filter))
        }
    }

    fun onListQualityFilterChanged(quality: String) {
        _uiState.update { state ->
            recomputeDerivedState(state.copy(listQualityFilter = quality))
        }
    }

    fun onListSortChanged(sort: ReleaseSort) {
        _uiState.update { state ->
            recomputeDerivedState(state.copy(listSort = sort))
        }
    }

    fun toggleReleaseSelection(torrentId: String) {
        _uiState.update { state ->
            val next = state.selectedIds.toMutableSet()
            if (!next.add(torrentId)) {
                next.remove(torrentId)
            }
            state.copy(selectedIds = next)
        }
    }

    fun toggleEpisodeReleaseSelection(episodeNumber: Int, torrentId: String) {
        _uiState.update { state ->
            val next = state.selectedIds.toMutableSet()
            val siblings = state.episodeVariantsMap[episodeNumber].orEmpty().map { it.id }.toSet()
            if (torrentId in next) {
                next.remove(torrentId)
            } else {
                next.removeAll(siblings)
                next.add(torrentId)
            }
            state.copy(selectedIds = next)
        }
    }

    fun selectRecommendedEpisodes() {
        _uiState.update { state ->
            val recommended = state.episodeVariantsMap.values
                .mapNotNull { variants -> variants.firstOrNull()?.id }
                .toSet()
            state.copy(selectedIds = recommended)
        }
    }

    fun selectAllVisibleListReleases() {
        _uiState.update { state ->
            val visibleIds = state.filteredReleaseList
                .filter { it.magnetLink.isNotEmpty() }
                .map { it.id }
                .toSet()
            state.copy(selectedIds = state.selectedIds + visibleIds)
        }
    }

    fun clearSelection() {
        _uiState.update { it.copy(selectedIds = emptySet()) }
    }

    fun inspectTorrentFiles(torrent: Torrent) {
        activeFilesJob?.cancel()
        if (torrent.id.isBlank() || torrent.id == "0") {
            _uiState.update {
                it.copy(
                    inspectedTorrent = torrent,
                    isLoadingFiles = false,
                    inspectedFiles = emptyList(),
                    filesError = null,
                )
            }
            return
        }

        _uiState.update {
            it.copy(
                inspectedTorrent = torrent,
                isLoadingFiles = true,
                inspectedFiles = emptyList(),
                filesError = null,
            )
        }

        activeFilesJob = viewModelScope.launch {
            try {
                val files = apiClient.getParsedFiles(torrent.id)
                _uiState.update {
                    if (it.inspectedTorrent?.id == torrent.id) {
                        it.copy(isLoadingFiles = false, inspectedFiles = files, filesError = null)
                    } else {
                        it
                    }
                }
            } catch (_: CancellationException) {
                // Ignore cancelled inspection
            } catch (err: Exception) {
                _uiState.update {
                    if (it.inspectedTorrent?.id == torrent.id) {
                        it.copy(
                            isLoadingFiles = false,
                            inspectedFiles = emptyList(),
                            filesError = err.message ?: "Failed to load file listing.",
                        )
                    } else {
                        it
                    }
                }
            }
        }
    }

    fun dismissFileInspector() {
        activeFilesJob?.cancel()
        _uiState.update {
            it.copy(
                inspectedTorrent = null,
                isLoadingFiles = false,
                inspectedFiles = emptyList(),
                filesError = null,
            )
        }
    }

    fun retryInspectedFiles() {
        val current = _uiState.value.inspectedTorrent ?: return
        inspectTorrentFiles(current)
    }

    fun toggleCurrentBookmark() {
        val state = _uiState.value
        val target = state.query.trim()
        if (target.isEmpty()) return
        viewModelScope.launch {
            preferencesRepository.toggleBookmark(target, state.mode)
        }
    }

    fun removeBookmark(bookmark: BookmarkEntry) {
        viewModelScope.launch {
            preferencesRepository.removeBookmark(bookmark.title, bookmark.mode)
        }
    }

    fun clearHistory() {
        viewModelScope.launch {
            preferencesRepository.clearHistory()
        }
    }

    fun toggleTheme() {
        val nextDark = !_uiState.value.settings.darkTheme
        viewModelScope.launch {
            preferencesRepository.setDarkTheme(nextDark)
        }
    }

    suspend fun saveSettings(
        darkTheme: Boolean,
        apiUrl: String,
        proxyUrl: String,
        defaultQuality: String,
    ): Result<Unit> = runCatching {
        preferencesRepository.saveSettings(
            darkTheme = darkTheme,
            apiUrl = apiUrl,
            proxyUrl = proxyUrl,
            defaultQuality = defaultQuality,
        )
        apiClient.reconfigure(apiUrl, proxyUrl.ifBlank { null })
    }

    fun clearApiCache() {
        apiClient.clearCache()
    }

    private fun initialListQualityFilter(results: List<Torrent>, preferred: String): String {
        if (preferred in setOf("2160p", "1080p", "720p", "480p")) {
            val hasMatch = results.any { it.quality.equals(preferred, ignoreCase = true) }
            if (hasMatch) return preferred
        }
        return "All"
    }

    private fun reinitializeTvHierarchy(state: TpbUiState): TpbUiState {
        if (state.mode != SearchMode.TV) return state
        val variants = TitleParser.detectSeriesVariants(state.rawResults)
        val firstTag = if (variants.isNotEmpty()) variants.keys.sorted().first() else null
        return reinitializeSeasonsOnly(
            state.copy(
                seriesVariants = variants,
                selectedVariantTag = firstTag,
            ),
        )
    }

    private fun reinitializeSeasonsOnly(state: TpbUiState): TpbUiState {
        val activeVariantTorrents = variantTorrentsFor(state)
        val summary = TitleParser.getDetectedSeasonsSummary(activeVariantTorrents)
        val firstSeason = summary.keys.firstOrNull()
        val updated = recomputeDerivedState(
            state.copy(
                seasonsSummary = summary,
                selectedSeason = firstSeason,
            ),
        )
        val defaultSubMode = when {
            firstSeason == null -> TvSubMode.ALL
            updated.episodeVariantsMap.isNotEmpty() -> TvSubMode.EPISODES
            updated.seasonPacks.isNotEmpty() -> TvSubMode.PACKS
            else -> TvSubMode.ALL
        }
        return recomputeDerivedState(updated.copy(tvSubMode = defaultSubMode))
    }

    private fun variantTorrentsFor(state: TpbUiState): List<Torrent> {
        val tag = state.selectedVariantTag
        return if (tag != null && tag != "all" && tag in state.seriesVariants) {
            state.seriesVariants.getValue(tag)
        } else {
            state.rawResults
        }
    }

    private fun recomputeDerivedState(state: TpbUiState): TpbUiState {
        if (state.mode != SearchMode.TV) {
            return state.copy(
                filteredReleaseList = filterAndSortList(
                    source = state.rawResults,
                    textFilter = state.listTextFilter,
                    qualityFilter = state.listQualityFilter,
                    sort = state.listSort,
                ),
            )
        }

        val variantTorrents = variantTorrentsFor(state)
        val season = state.selectedSeason
        val packs = if (season != null) TitleParser.getSeasonPacks(variantTorrents, season) else emptyList()
        val episodes = if (season != null) {
            val grouped = TitleParser.filterAndGroupEpisodes(
                torrents = variantTorrents,
                targetSeason = season,
                preferredQuality = state.tvPreferredQuality,
            )
            grouped.mapValues { (_, candidates) ->
                TitleParser.getEpisodeQualityVariants(candidates)
            }
        } else {
            emptyMap()
        }

        val listSource = when (state.tvSubMode) {
            TvSubMode.PACKS -> packs
            TvSubMode.ALL -> if (season != null) {
                state.seasonsSummary[season]?.torrents ?: variantTorrents
            } else {
                variantTorrents
            }
            TvSubMode.EPISODES -> emptyList()
        }

        return state.copy(
            episodeVariantsMap = episodes,
            seasonPacks = packs,
            filteredReleaseList = filterAndSortList(
                source = listSource,
                textFilter = state.listTextFilter,
                qualityFilter = state.listQualityFilter,
                sort = state.listSort,
            ),
        )
    }

    private fun filterAndSortList(
        source: List<Torrent>,
        textFilter: String,
        qualityFilter: String,
        sort: ReleaseSort,
    ): List<Torrent> {
        val needle = textFilter.trim().lowercase()
        val filtered = source.filter { torrent ->
            val qualityOk = qualityFilter == "All" ||
                torrent.quality.equals(qualityFilter, ignoreCase = true)
            val textOk = needle.isEmpty() ||
                "${torrent.name} ${torrent.username} ${torrent.codec} ${torrent.quality}"
                    .lowercase()
                    .contains(needle)
            qualityOk && textOk
        }

        return when (sort) {
            ReleaseSort.SEEDERS_DESC -> filtered.sortedByDescending { it.seeders }
            ReleaseSort.SIZE_DESC -> filtered.sortedByDescending { it.sizeBytes }
            ReleaseSort.DATE_DESC -> filtered.sortedByDescending { it.added }
            ReleaseSort.NAME_ASC -> filtered.sortedBy { it.name.lowercase() }
        }
    }

    class Factory(
        private val apiClient: ApibayApiClient,
        private val preferencesRepository: TpbPreferencesRepository,
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            return TpbViewModel(apiClient, preferencesRepository) as T
        }
    }
}
