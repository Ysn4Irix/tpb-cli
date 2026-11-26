package com.ysn4irix.tpb.ui.search

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Bookmark
import androidx.compose.material.icons.outlined.BookmarkBorder
import androidx.compose.material.icons.outlined.Clear
import androidx.compose.material.icons.outlined.Search
import androidx.compose.material3.Button
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.SegmentedButton
import androidx.compose.material3.SegmentedButtonDefaults
import androidx.compose.material3.SingleChoiceSegmentedButtonRow
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.ysn4irix.tpb.domain.model.SearchMode
import com.ysn4irix.tpb.domain.model.Torrent
import com.ysn4irix.tpb.ui.ReleaseSort
import com.ysn4irix.tpb.ui.TpbUiState
import com.ysn4irix.tpb.ui.TvSubMode
import java.util.Locale

private val TV_QUALITIES = listOf("Any", "1080p", "720p", "2160p", "480p")

@Composable
fun SearchScreen(
    uiState: TpbUiState,
    onQueryChanged: (String) -> Unit,
    onModeSelected: (SearchMode) -> Unit,
    onRunSearch: () -> Unit,
    onCancelSearch: () -> Unit,
    onToggleBookmark: () -> Unit,
    onSelectVariantTag: (String) -> Unit,
    onSelectSeason: (Int?) -> Unit,
    onSelectTvSubMode: (TvSubMode) -> Unit,
    onSelectTvQuality: (String) -> Unit,
    onSelectRecommended: () -> Unit,
    onClearSelection: () -> Unit,
    onToggleEpisodeRelease: (Int, String) -> Unit,
    onToggleListRelease: (String) -> Unit,
    onListTextFilterChanged: (String) -> Unit,
    onListQualityFilterChanged: (String) -> Unit,
    onCycleSort: () -> Unit,
    onSelectVisibleList: () -> Unit,
    onInspectFiles: (Torrent) -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(horizontal = 12.dp, vertical = 8.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        SearchHeader(
            query = uiState.query,
            mode = uiState.mode,
            isSearching = uiState.isSearching,
            isBookmarked = uiState.isCurrentQueryBookmarked,
            onQueryChanged = onQueryChanged,
            onModeSelected = onModeSelected,
            onRunSearch = onRunSearch,
            onToggleBookmark = onToggleBookmark,
        )

        when {
            uiState.isSearching -> {
                SearchLoadingPanel(
                    query = uiState.query,
                    elapsedSec = uiState.searchElapsedSec,
                    onCancel = onCancelSearch,
                )
            }

            uiState.searchError != null -> {
                SearchMessageCard(
                    title = "Search Failed",
                    subtitle = uiState.searchError,
                    isError = true,
                    actionLabel = "Retry Search",
                    onAction = onRunSearch,
                )
            }

            !uiState.hasSearched -> {
                SearchMessageCard(
                    title = "TPB / Apibay Mobile",
                    subtitle = "Choose TV Series, Movies, or General above, enter a title, and tap Search.\n" +
                        "TV Series auto-detects regional editions, seasons, full packs, and multi-quality episodes.",
                )
            }

            uiState.rawResults.isEmpty() -> {
                SearchMessageCard(
                    title = "No Results Found",
                    subtitle = "No releases found on Apibay for '${uiState.activeSearchQuery}'.",
                )
            }

            uiState.mode == SearchMode.TV -> {
                TvBrowserSection(
                    uiState = uiState,
                    onSelectVariantTag = onSelectVariantTag,
                    onSelectSeason = onSelectSeason,
                    onSelectTvSubMode = onSelectTvSubMode,
                    onSelectTvQuality = onSelectTvQuality,
                    onSelectRecommended = onSelectRecommended,
                    onClearSelection = onClearSelection,
                    onToggleEpisodeRelease = onToggleEpisodeRelease,
                    onToggleListRelease = onToggleListRelease,
                    onListTextFilterChanged = onListTextFilterChanged,
                    onListQualityFilterChanged = onListQualityFilterChanged,
                    onCycleSort = onCycleSort,
                    onSelectVisibleList = onSelectVisibleList,
                    onInspectFiles = onInspectFiles,
                    modifier = Modifier.weight(1f),
                )
            }

            else -> {
                ReleaseListSection(
                    torrents = uiState.filteredReleaseList,
                    textFilter = uiState.listTextFilter,
                    qualityFilter = uiState.listQualityFilter,
                    sortOption = uiState.listSort,
                    selectedIds = uiState.selectedIds,
                    onTextFilterChanged = onListTextFilterChanged,
                    onQualityFilterChanged = onListQualityFilterChanged,
                    onCycleSort = onCycleSort,
                    onSelectVisible = onSelectVisibleList,
                    onClearSelection = onClearSelection,
                    onToggleRelease = onToggleListRelease,
                    onInspectFiles = onInspectFiles,
                    modifier = Modifier.weight(1f),
                )
            }
        }
    }
}

@Composable
private fun SearchHeader(
    query: String,
    mode: SearchMode,
    isSearching: Boolean,
    isBookmarked: Boolean,
    onQueryChanged: (String) -> Unit,
    onModeSelected: (SearchMode) -> Unit,
    onRunSearch: () -> Unit,
    onToggleBookmark: () -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            OutlinedTextField(
                value = query,
                onValueChange = onQueryChanged,
                enabled = !isSearching,
                singleLine = true,
                placeholder = {
                    val hint = when (mode) {
                        SearchMode.TV -> "Search TV show (e.g. Severance)..."
                        SearchMode.MOVIE -> "Search movie title..."
                        SearchMode.GENERAL -> "Search any torrent..."
                    }
                    Text(hint)
                },
                leadingIcon = {
                    Icon(Icons.Outlined.Search, contentDescription = null)
                },
                trailingIcon = {
                    if (query.isNotEmpty() && !isSearching) {
                        IconButton(
                            onClick = { onQueryChanged("") },
                            modifier = Modifier.size(48.dp),
                        ) {
                            Icon(Icons.Outlined.Clear, contentDescription = "Clear search query")
                        }
                    }
                },
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
                keyboardActions = KeyboardActions(onSearch = { onRunSearch() }),
                modifier = Modifier.weight(1f),
            )

            IconButton(
                onClick = onToggleBookmark,
                enabled = query.isNotBlank() && !isSearching,
                modifier = Modifier.size(48.dp),
            ) {
                Icon(
                    imageVector = if (isBookmarked) Icons.Filled.Bookmark else Icons.Outlined.BookmarkBorder,
                    contentDescription = if (isBookmarked) "Remove bookmark" else "Bookmark query",
                    tint = if (isBookmarked) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            Button(
                onClick = onRunSearch,
                enabled = query.isNotBlank() && !isSearching,
                modifier = Modifier.heightIn(min = 52.dp),
            ) {
                Text(if (isSearching) "..." else "Go")
            }
        }

        SingleChoiceSegmentedButtonRow(modifier = Modifier.fillMaxWidth()) {
            SearchMode.entries.forEachIndexed { idx, entry ->
                SegmentedButton(
                    selected = mode == entry,
                    onClick = { if (!isSearching) onModeSelected(entry) },
                    enabled = !isSearching,
                    shape = SegmentedButtonDefaults.itemShape(
                        index = idx,
                        count = SearchMode.entries.size,
                    ),
                    label = { Text(entry.label) },
                )
            }
        }
    }
}

@Composable
private fun TvBrowserSection(
    uiState: TpbUiState,
    onSelectVariantTag: (String) -> Unit,
    onSelectSeason: (Int?) -> Unit,
    onSelectTvSubMode: (TvSubMode) -> Unit,
    onSelectTvQuality: (String) -> Unit,
    onSelectRecommended: () -> Unit,
    onClearSelection: () -> Unit,
    onToggleEpisodeRelease: (Int, String) -> Unit,
    onToggleListRelease: (String) -> Unit,
    onListTextFilterChanged: (String) -> Unit,
    onListQualityFilterChanged: (String) -> Unit,
    onCycleSort: () -> Unit,
    onSelectVisibleList: () -> Unit,
    onInspectFiles: (Torrent) -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier.fillMaxSize(),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        if (uiState.seriesVariants.isNotEmpty()) {
            LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                val sortedTags = uiState.seriesVariants.keys.sorted()
                items(sortedTags, key = { "var-$it" }) { tag ->
                    val count = uiState.seriesVariants[tag]?.size ?: 0
                    FilterChip(
                        selected = uiState.selectedVariantTag == tag,
                        onClick = { onSelectVariantTag(tag) },
                        label = { Text("$tag ($count)") },
                        modifier = Modifier.heightIn(min = 40.dp),
                    )
                }
                item(key = "var-all") {
                    FilterChip(
                        selected = uiState.selectedVariantTag == "all",
                        onClick = { onSelectVariantTag("all") },
                        label = { Text("All (${uiState.rawResults.size})") },
                        modifier = Modifier.heightIn(min = 40.dp),
                    )
                }
            }
        }

        LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            val seasons = uiState.seasonsSummary.entries.toList()
            items(seasons, key = { "season-${it.key}" }) { (seasonNum, info) ->
                val detail = when {
                    info.episodes.isNotEmpty() -> "${info.episodes.size} ep"
                    info.packs.isNotEmpty() -> "${info.packs.size} pack"
                    else -> "${info.totalTorrents} rel"
                }
                FilterChip(
                    selected = uiState.selectedSeason == seasonNum,
                    onClick = { onSelectSeason(seasonNum) },
                    label = { Text("S${seasonNum.toString().padStart(2, '0')} · $detail") },
                    modifier = Modifier.heightIn(min = 40.dp),
                )
            }
            item(key = "season-all") {
                FilterChip(
                    selected = uiState.selectedSeason == null,
                    onClick = { onSelectSeason(null) },
                    label = { Text("All Releases") },
                    modifier = Modifier.heightIn(min = 40.dp),
                )
            }
        }

        if (uiState.selectedSeason != null) {
            SingleChoiceSegmentedButtonRow(modifier = Modifier.fillMaxWidth()) {
                TvSubMode.entries.forEachIndexed { idx, subMode ->
                    val enabled = when (subMode) {
                        TvSubMode.EPISODES -> uiState.episodeVariantsMap.isNotEmpty()
                        TvSubMode.PACKS -> uiState.seasonPacks.isNotEmpty()
                        TvSubMode.ALL -> true
                    }
                    SegmentedButton(
                        selected = uiState.tvSubMode == subMode,
                        onClick = { onSelectTvSubMode(subMode) },
                        enabled = enabled,
                        shape = SegmentedButtonDefaults.itemShape(
                            index = idx,
                            count = TvSubMode.entries.size,
                        ),
                        label = {
                            val label = when (subMode) {
                                TvSubMode.EPISODES -> "Episodes (${uiState.episodeVariantsMap.size})"
                                TvSubMode.PACKS -> "Packs (${uiState.seasonPacks.size})"
                                TvSubMode.ALL -> "All"
                            }
                            Text(label, maxLines = 1)
                        },
                    )
                }
            }
        }

        if (uiState.tvSubMode == TvSubMode.EPISODES && uiState.episodeVariantsMap.isNotEmpty()) {
            LazyRow(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                items(TV_QUALITIES, key = { "q-$it" }) { quality ->
                    FilterChip(
                        selected = uiState.tvPreferredQuality == quality,
                        onClick = { onSelectTvQuality(quality) },
                        label = { Text(quality) },
                        modifier = Modifier.heightIn(min = 40.dp),
                    )
                }
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                FilledTonalButton(
                    onClick = onSelectRecommended,
                    modifier = Modifier.heightIn(min = 48.dp),
                ) {
                    Text("Select Recommended")
                }
                TextButton(
                    onClick = onClearSelection,
                    modifier = Modifier.heightIn(min = 48.dp),
                ) {
                    Text("Clear")
                }
            }

            LazyColumn(
                modifier = Modifier.weight(1f),
                contentPadding = PaddingValues(bottom = 84.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                uiState.episodeVariantsMap.entries.sortedBy { it.key }.forEach { (epNum, variants) ->
                    item(key = "ep-hdr-$epNum") {
                        Text(
                            text = "Episode ${epNum.toString().padStart(2, '0')} (${variants.size} option${if (variants.size == 1) "" else "s"})",
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.padding(top = 6.dp),
                        )
                    }
                    items(
                        items = variants,
                        key = { variant -> "ep-$epNum-${variant.id}" },
                    ) { variant ->
                        val isTopRecommended = variant == variants.firstOrNull()
                        ReleaseCard(
                            torrent = variant,
                            selected = variant.id in uiState.selectedIds,
                            recommended = isTopRecommended,
                            onToggleSelect = { onToggleEpisodeRelease(epNum, variant.id) },
                            onInspectFiles = { onInspectFiles(variant) },
                        )
                    }
                }
            }
        } else {
            ReleaseListSection(
                torrents = uiState.filteredReleaseList,
                textFilter = uiState.listTextFilter,
                qualityFilter = uiState.listQualityFilter,
                sortOption = uiState.listSort,
                selectedIds = uiState.selectedIds,
                onTextFilterChanged = onListTextFilterChanged,
                onQualityFilterChanged = onListQualityFilterChanged,
                onCycleSort = onCycleSort,
                onSelectVisible = onSelectVisibleList,
                onClearSelection = onClearSelection,
                onToggleRelease = onToggleListRelease,
                onInspectFiles = onInspectFiles,
                modifier = Modifier.weight(1f),
            )
        }
    }
}

@Composable
private fun SearchLoadingPanel(
    query: String,
    elapsedSec: Double,
    onCancel: () -> Unit,
) {
    Surface(
        shape = MaterialTheme.shapes.medium,
        color = MaterialTheme.colorScheme.surface,
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 24.dp),
    ) {
        Column(
            modifier = Modifier.padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(
                text = "Searching Apibay for \"$query\"...",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold,
                textAlign = TextAlign.Center,
            )
            LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
            Text(
                text = String.format(Locale.US, "Connecting... (%.1fs)", elapsedSec),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Spacer(modifier = Modifier.height(4.dp))
            OutlinedButton(
                onClick = onCancel,
                modifier = Modifier.heightIn(min = 48.dp),
            ) {
                Text("Cancel Search")
            }
        }
    }
}

@Composable
private fun SearchMessageCard(
    title: String,
    subtitle: String,
    isError: Boolean = false,
    actionLabel: String? = null,
    onAction: (() -> Unit)? = null,
) {
    Surface(
        shape = MaterialTheme.shapes.medium,
        color = MaterialTheme.colorScheme.surface,
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 24.dp),
    ) {
        Column(
            modifier = Modifier.padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text(
                text = title,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                color = if (isError) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurface,
                textAlign = TextAlign.Center,
            )
            Text(
                text = subtitle,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center,
            )
            if (actionLabel != null && onAction != null) {
                Spacer(modifier = Modifier.height(4.dp))
                Button(
                    onClick = onAction,
                    modifier = Modifier.heightIn(min = 48.dp),
                ) {
                    Text(actionLabel)
                }
            }
        }
    }
}
