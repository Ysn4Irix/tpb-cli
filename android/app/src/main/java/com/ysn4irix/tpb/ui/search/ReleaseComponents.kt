package com.ysn4irix.tpb.ui.search

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.Sort
import androidx.compose.material.icons.outlined.Clear
import androidx.compose.material.icons.outlined.FolderOpen
import androidx.compose.material3.Checkbox
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.ysn4irix.tpb.domain.model.Torrent
import com.ysn4irix.tpb.ui.ReleaseSort
import com.ysn4irix.tpb.ui.theme.LocalTpbSemanticColors

private val QUALITY_FILTERS = listOf("All", "2160p", "1080p", "720p", "480p")

@Composable
fun ReleaseCard(
    torrent: Torrent,
    selected: Boolean,
    recommended: Boolean = false,
    onToggleSelect: () -> Unit,
    onInspectFiles: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val semantics = LocalTpbSemanticColors.current
    val seedColor = when {
        torrent.isHealthy -> semantics.seedHealthy
        torrent.isModerateHealth -> semantics.seedModerate
        else -> semantics.seedLow
    }

    val borderColor = if (selected) {
        MaterialTheme.colorScheme.primary
    } else {
        MaterialTheme.colorScheme.outlineVariant
    }

    Surface(
        shape = RoundedCornerShape(10.dp),
        color = if (selected) semantics.accentSubtle else MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, borderColor),
        modifier = modifier
            .fillMaxWidth()
            .clickable(onClick = onToggleSelect),
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 8.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Checkbox(
                checked = selected,
                onCheckedChange = { onToggleSelect() },
                modifier = Modifier.size(48.dp),
            )
            Spacer(modifier = Modifier.width(4.dp))
            Column(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(4.dp),
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    Text(
                        text = torrent.name,
                        style = MaterialTheme.typography.bodyMedium,
                        fontWeight = FontWeight.Medium,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.weight(1f),
                    )
                    if (recommended) {
                        Text(
                            text = "Recommended",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.primary,
                            fontWeight = FontWeight.Bold,
                        )
                    }
                }

                val codecPart = if (torrent.codec != "Unknown") " · ${torrent.codec}" else ""
                val uploaderLabel = buildString {
                    val user = torrent.username.ifBlank { "Anonymous" }
                    if (torrent.isVip) append("[VIP] ")
                    else if (torrent.isTrusted) append("[TRUST] ")
                    append(user)
                }

                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    Text(
                        text = "${torrent.quality}$codecPart · ${torrent.humanSize}",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    Text(
                        text = "${torrent.seeders} seeds",
                        style = MaterialTheme.typography.labelMedium,
                        color = seedColor,
                        fontWeight = FontWeight.SemiBold,
                    )
                    Text(
                        text = "· $uploaderLabel",
                        style = MaterialTheme.typography.bodySmall,
                        color = if (torrent.isVip) semantics.seedHealthy else if (torrent.isTrusted) semantics.trustedBadge else MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }
            IconButton(
                onClick = onInspectFiles,
                modifier = Modifier.size(48.dp),
            ) {
                Icon(
                    imageVector = Icons.Outlined.FolderOpen,
                    contentDescription = "Inspect files in ${torrent.name}",
                    tint = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}

@Composable
fun ReleaseListSection(
    torrents: List<Torrent>,
    textFilter: String,
    qualityFilter: String,
    sortOption: ReleaseSort,
    selectedIds: Set<String>,
    onTextFilterChanged: (String) -> Unit,
    onQualityFilterChanged: (String) -> Unit,
    onCycleSort: () -> Unit,
    onSelectVisible: () -> Unit,
    onClearSelection: () -> Unit,
    onToggleRelease: (String) -> Unit,
    onInspectFiles: (Torrent) -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier.fillMaxSize(),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        OutlinedTextField(
            value = textFilter,
            onValueChange = onTextFilterChanged,
            placeholder = { Text("Filter title, codec, or uploader...") },
            singleLine = true,
            trailingIcon = {
                if (textFilter.isNotEmpty()) {
                    IconButton(
                        onClick = { onTextFilterChanged("") },
                        modifier = Modifier.size(48.dp),
                    ) {
                        Icon(Icons.Outlined.Clear, contentDescription = "Clear filter")
                    }
                }
            },
            modifier = Modifier.fillMaxWidth(),
        )

        LazyRow(
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            items(QUALITY_FILTERS, key = { it }) { quality ->
                FilterChip(
                    selected = qualityFilter == quality,
                    onClick = { onQualityFilterChanged(quality) },
                    label = { Text(quality) },
                    modifier = Modifier.heightIn(min = 40.dp),
                )
            }
            item(key = "sort") {
                FilterChip(
                    selected = false,
                    onClick = onCycleSort,
                    leadingIcon = {
                        Icon(
                            imageVector = Icons.AutoMirrored.Outlined.Sort,
                            contentDescription = "Change sort order",
                            modifier = Modifier.size(16.dp),
                        )
                    },
                    label = { Text(sortOption.label) },
                    modifier = Modifier.heightIn(min = 40.dp),
                )
            }
        }

        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Text(
                text = "${torrents.size} release${if (torrents.size == 1) "" else "s"}",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                TextButton(
                    onClick = onSelectVisible,
                    modifier = Modifier.heightIn(min = 48.dp),
                ) {
                    Text("Select Visible")
                }
                TextButton(
                    onClick = onClearSelection,
                    modifier = Modifier.heightIn(min = 48.dp),
                ) {
                    Text("Clear")
                }
            }
        }

        LazyColumn(
            modifier = Modifier.weight(1f),
            contentPadding = PaddingValues(bottom = 84.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            items(torrents, key = { it.id }) { torrent ->
                ReleaseCard(
                    torrent = torrent,
                    selected = torrent.id in selectedIds,
                    onToggleSelect = { onToggleRelease(torrent.id) },
                    onInspectFiles = { onInspectFiles(torrent) },
                )
            }
        }
    }
}
