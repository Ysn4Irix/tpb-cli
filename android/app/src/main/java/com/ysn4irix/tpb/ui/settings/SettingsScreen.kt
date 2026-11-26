package com.ysn4irix.tpb.ui.settings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.ysn4irix.tpb.data.remote.NetworkValidator
import com.ysn4irix.tpb.domain.model.AppSettings
import com.ysn4irix.tpb.ui.theme.LocalTpbSemanticColors
import kotlinx.coroutines.launch

private val DEFAULT_QUALITIES = listOf("1080p", "720p", "2160p", "480p", "Any")

@Composable
fun SettingsScreen(
    settings: AppSettings,
    onSaveSettings: suspend (Boolean, String, String, String) -> Result<Unit>,
    onClearCache: () -> Unit,
    onShowMessage: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    val scope = rememberCoroutineScope()
    val semantics = LocalTpbSemanticColors.current

    var darkTheme by remember(settings.darkTheme) { mutableStateOf(settings.darkTheme) }
    var apiUrl by remember(settings.apiUrl) { mutableStateOf(settings.apiUrl) }
    var proxyUrl by remember(settings.proxyUrl) { mutableStateOf(settings.proxyUrl) }
    var defaultQuality by remember(settings.defaultQuality) { mutableStateOf(settings.defaultQuality) }
    var validationError by remember { mutableStateOf<String?>(null) }

    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Text(
            text = "Network & Appearance",
            style = MaterialTheme.typography.titleLarge,
            fontWeight = FontWeight.Bold,
        )

        Row(
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 48.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "OLED Dark Theme",
                    style = MaterialTheme.typography.titleMedium,
                )
                Text(
                    text = "Use battery-friendly obsidian slate dark surfaces",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Switch(
                checked = darkTheme,
                onCheckedChange = { darkTheme = it },
            )
        }

        HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)

        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(
                text = "Default Preferred Quality",
                style = MaterialTheme.typography.titleMedium,
            )
            LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                items(DEFAULT_QUALITIES, key = { it }) { quality ->
                    FilterChip(
                        selected = defaultQuality == quality,
                        onClick = { defaultQuality = quality },
                        label = { Text(quality) },
                        modifier = Modifier.heightIn(min = 40.dp),
                    )
                }
            }
        }

        HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)

        OutlinedTextField(
            value = apiUrl,
            onValueChange = {
                apiUrl = it
                validationError = null
            },
            label = { Text("Apibay API Mirror URL") },
            placeholder = { Text("https://apibay.org") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )

        if (NetworkValidator.isCleartextHttp(apiUrl)) {
            Text(
                text = "Warning: Plain HTTP mirror selected. HTTPS is recommended on public networks.",
                style = MaterialTheme.typography.bodySmall,
                color = semantics.seedModerate,
            )
        }

        OutlinedTextField(
            value = proxyUrl,
            onValueChange = {
                proxyUrl = it
                validationError = null
            },
            label = { Text("Optional Proxy (HTTP / SOCKS5)") },
            placeholder = { Text("socks5://127.0.0.1:9050 (Orbot)") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )

        val err = validationError
        if (err != null) {
            Text(
                text = err,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.error,
            )
        }

        Button(
            onClick = {
                scope.launch {
                    val result = onSaveSettings(darkTheme, apiUrl, proxyUrl, defaultQuality)
                    result
                        .onSuccess {
                            validationError = null
                            onShowMessage("Settings saved.")
                        }
                        .onFailure { exc ->
                            validationError = exc.message ?: "Invalid network settings."
                        }
                }
            },
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 48.dp),
        ) {
            Text("Save Settings")
        }

        Spacer(modifier = Modifier.height(4.dp))

        OutlinedButton(
            onClick = {
                onClearCache()
                onShowMessage("Search cache cleared.")
            },
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 48.dp),
        ) {
            Text("Clear Search Cache")
        }
    }
}
