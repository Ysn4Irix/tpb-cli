package com.ysn4irix.tpb.ui.library

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.DeleteOutline
import androidx.compose.material.icons.outlined.History
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.PrimaryTabRow
import androidx.compose.material3.Surface
import androidx.compose.material3.Tab
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.ysn4irix.tpb.domain.model.BookmarkEntry
import com.ysn4irix.tpb.domain.model.SearchHistoryEntry
import com.ysn4irix.tpb.domain.model.SearchMode

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LibraryScreen(
    history: List<SearchHistoryEntry>,
    bookmarks: List<BookmarkEntry>,
    onSelectSearch: (String, SearchMode) -> Unit,
    onClearHistory: () -> Unit,
    onRemoveBookmark: (BookmarkEntry) -> Unit,
    modifier: Modifier = Modifier,
) {
    var selectedTab by rememberSaveable { mutableIntStateOf(0) }

    Column(modifier = modifier.fillMaxSize()) {
        PrimaryTabRow(selectedTabIndex = selectedTab) {
            Tab(
                selected = selectedTab == 0,
                onClick = { selectedTab = 0 },
                text = { Text("History (${history.size})") },
            )
            Tab(
                selected = selectedTab == 1,
                onClick = { selectedTab = 1 },
                text = { Text("Bookmarks (${bookmarks.size})") },
            )
        }

        if (selectedTab == 0) {
            if (history.isNotEmpty()) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 12.dp, vertical = 4.dp),
                    horizontalArrangement = Arrangement.End,
                ) {
                    TextButton(
                        onClick = onClearHistory,
                        modifier = Modifier.heightIn(min = 48.dp),
                    ) {
                        Text("Clear History")
                    }
                }
            }
            if (history.isEmpty()) {
                EmptyLibraryMessage("Your recent search history will appear here.")
            } else {
                LazyColumn(
                    contentPadding = PaddingValues(12.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    items(
                        items = history,
                        key = { "${it.mode.name}-${it.query}-${it.timestamp}" },
                    ) { entry ->
                        LibraryRowCard(
                            mode = entry.mode,
                            title = entry.query,
                            subtitle = entry.timestamp,
                            onClick = { onSelectSearch(entry.query, entry.mode) },
                        )
                    }
                }
            }
        } else {
            if (bookmarks.isEmpty()) {
                EmptyLibraryMessage("Tap the bookmark icon on any query to pin it here.")
            } else {
                LazyColumn(
                    contentPadding = PaddingValues(12.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    items(
                        items = bookmarks,
                        key = { "bm-${it.mode.name}-${it.title}" },
                    ) { bookmark ->
                        LibraryRowCard(
                            mode = bookmark.mode,
                            title = bookmark.title,
                            subtitle = "Saved ${bookmark.addedAt}",
                            onClick = { onSelectSearch(bookmark.title, bookmark.mode) },
                            trailingAction = {
                                IconButton(
                                    onClick = { onRemoveBookmark(bookmark) },
                                    modifier = Modifier.size(48.dp),
                                ) {
                                    Icon(
                                        imageVector = Icons.Outlined.DeleteOutline,
                                        contentDescription = "Remove bookmark ${bookmark.title}",
                                    )
                                }
                            },
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun LibraryRowCard(
    mode: SearchMode,
    title: String,
    subtitle: String,
    onClick: () -> Unit,
    trailingAction: (@Composable () -> Unit)? = null,
) {
    Surface(
        shape = RoundedCornerShape(10.dp),
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 14.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Icon(
                imageVector = Icons.Outlined.History,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.primary,
            )
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "[${mode.name}] $title",
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.Medium,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(
                    text = subtitle,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            trailingAction?.invoke()
        }
    }
}

@Composable
private fun EmptyLibraryMessage(message: String) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Text(
            text = message,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}
