package com.ysn4irix.tpb.ui.common

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.OpenInNew
import androidx.compose.material.icons.outlined.Clear
import androidx.compose.material.icons.outlined.ContentCopy
import androidx.compose.material.icons.outlined.Download
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
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

@Composable
fun SelectionActionBar(
    selectedCount: Int,
    onCopyAll: () -> Unit,
    onOpenInClient: () -> Unit,
    onExportTxt: () -> Unit,
    onClearSelection: () -> Unit,
    modifier: Modifier = Modifier,
) {
    AnimatedVisibility(
        visible = selectedCount > 0,
        enter = slideInVertically(initialOffsetY = { it }),
        exit = slideOutVertically(targetOffsetY = { it }),
        modifier = modifier,
    ) {
        Surface(
            color = MaterialTheme.colorScheme.surface,
            tonalElevation = 4.dp,
        ) {
            Column(modifier = Modifier.fillMaxWidth()) {
                HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 12.dp, vertical = 8.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    IconButton(
                        onClick = onClearSelection,
                        modifier = Modifier.size(48.dp),
                    ) {
                        Icon(
                            imageVector = Icons.Outlined.Clear,
                            contentDescription = "Clear selected releases",
                        )
                    }
                    Text(
                        text = "$selectedCount selected",
                        style = MaterialTheme.typography.labelLarge,
                        fontWeight = FontWeight.SemiBold,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.weight(1f),
                    )
                    FilledTonalButton(
                        onClick = onCopyAll,
                        contentPadding = PaddingValues(horizontal = 12.dp),
                        modifier = Modifier.heightIn(min = 48.dp),
                    ) {
                        Icon(
                            imageVector = Icons.Outlined.ContentCopy,
                            contentDescription = null,
                            modifier = Modifier.size(18.dp),
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("Copy")
                    }
                    FilledTonalButton(
                        onClick = onOpenInClient,
                        contentPadding = PaddingValues(horizontal = 12.dp),
                        modifier = Modifier.heightIn(min = 48.dp),
                    ) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Outlined.OpenInNew,
                            contentDescription = null,
                            modifier = Modifier.size(18.dp),
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("Open")
                    }
                    Button(
                        onClick = onExportTxt,
                        contentPadding = PaddingValues(horizontal = 12.dp),
                        modifier = Modifier.heightIn(min = 48.dp),
                    ) {
                        Icon(
                            imageVector = Icons.Outlined.Download,
                            contentDescription = null,
                            modifier = Modifier.size(18.dp),
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                        Text(".txt")
                    }
                }
            }
        }
    }
}

@Composable
fun MultiMagnetHandoffDialog(
    torrents: List<Torrent>,
    currentStepIndex: Int?,
    onCopyAll: () -> Unit,
    onExportTxt: () -> Unit,
    onSendStep: (Int) -> Unit,
    onDismiss: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Text(
                if (currentStepIndex == null) {
                    "Send ${torrents.size} Magnet Links"
                } else {
                    "Opening Magnet ${currentStepIndex + 1} of ${torrents.size}"
                },
            )
        },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                if (currentStepIndex == null) {
                    Text(
                        text = "Android switches immediately to your torrent client on the first magnet link, which can drop additional batch links.",
                        style = MaterialTheme.typography.bodyMedium,
                    )
                    Text(
                        text = "Recommended: copy all links to your clipboard or export a .txt file for batch import.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                } else {
                    val active = torrents.getOrNull(currentStepIndex)
                    if (active != null) {
                        Text(
                            text = active.name,
                            style = MaterialTheme.typography.bodyMedium,
                            fontWeight = FontWeight.Medium,
                        )
                        Text(
                            text = "${active.quality} · ${active.humanSize} · ${active.seeders} seeds",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
            }
        },
        confirmButton = {
            if (currentStepIndex == null) {
                Button(
                    onClick = onCopyAll,
                    modifier = Modifier.heightIn(min = 48.dp),
                ) {
                    Text("Copy All")
                }
            } else {
                Button(
                    onClick = { onSendStep(currentStepIndex) },
                    modifier = Modifier.heightIn(min = 48.dp),
                ) {
                    Text("Send ${currentStepIndex + 1}/${torrents.size}")
                }
            }
        },
        dismissButton = {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                if (currentStepIndex == null) {
                    OutlinedButton(
                        onClick = { onSendStep(0) },
                        modifier = Modifier.heightIn(min = 48.dp),
                    ) {
                        Text("1-by-1")
                    }
                    FilledTonalButton(
                        onClick = onExportTxt,
                        modifier = Modifier.heightIn(min = 48.dp),
                    ) {
                        Text("Export .txt")
                    }
                } else {
                    TextButton(
                        onClick = onDismiss,
                        modifier = Modifier.heightIn(min = 48.dp),
                    ) {
                        Text("Done")
                    }
                }
            }
        },
    )
}
