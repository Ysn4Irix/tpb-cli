package com.ysn4irix.tpb.ui.common

import android.content.ActivityNotFoundException
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import com.ysn4irix.tpb.domain.model.Torrent
import com.ysn4irix.tpb.domain.parser.formatMagnetsDocument

sealed interface MagnetDispatchResult {
    data object OpenedClient : MagnetDispatchResult
    data object CopiedFallbackNoClient : MagnetDispatchResult
    data object NothingSelected : MagnetDispatchResult
}

object MagnetIntentHelper {
    fun copyMagnetsToClipboard(context: Context, torrents: List<Torrent>): Int {
        val valid = torrents.filter { it.magnetLink.isNotEmpty() }
        if (valid.isEmpty()) return 0

        val text = valid.joinToString("\n") { it.magnetLink }
        val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        clipboard.setPrimaryClip(ClipData.newPlainText("Magnet Links", text))
        return valid.size
    }

    fun openSingleMagnetInClient(context: Context, torrent: Torrent): MagnetDispatchResult {
        val magnetUri = torrent.magnetLink
        if (magnetUri.isEmpty()) return MagnetDispatchResult.NothingSelected

        val intent = Intent(Intent.ACTION_VIEW, Uri.parse(magnetUri)).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        return try {
            context.startActivity(intent)
            MagnetDispatchResult.OpenedClient
        } catch (_: ActivityNotFoundException) {
            copyMagnetsToClipboard(context, listOf(torrent))
            MagnetDispatchResult.CopiedFallbackNoClient
        }
    }

    fun buildExportContent(torrents: List<Torrent>): String =
        formatMagnetsDocument(torrents, includeMetadataComments = true)
}
