package com.ysn4irix.tpb

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Bookmarks
import androidx.compose.material.icons.outlined.Search
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.ysn4irix.tpb.ui.ReleaseSort
import com.ysn4irix.tpb.ui.TpbViewModel
import com.ysn4irix.tpb.ui.common.MagnetDispatchResult
import com.ysn4irix.tpb.ui.common.MagnetIntentHelper
import com.ysn4irix.tpb.ui.common.MultiMagnetHandoffDialog
import com.ysn4irix.tpb.ui.common.SelectionActionBar
import com.ysn4irix.tpb.ui.library.LibraryScreen
import com.ysn4irix.tpb.ui.search.FileInspectorBottomSheet
import com.ysn4irix.tpb.ui.search.SearchScreen
import com.ysn4irix.tpb.ui.settings.SettingsScreen
import com.ysn4irix.tpb.ui.theme.TpbTheme
import kotlinx.coroutines.launch

private enum class TopDestination(
    val route: String,
    val label: String,
) {
    SEARCH("search", "Search"),
    LIBRARY("library", "Library"),
    SETTINGS("settings", "Settings"),
}

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        val app = application as TpbApplication
        val factory = TpbViewModel.Factory(
            apiClient = app.apiClient,
            preferencesRepository = app.preferencesRepository,
        )

        setContent {
            val viewModel: TpbViewModel = viewModel(factory = factory)
            val uiState by viewModel.uiState.collectAsStateWithLifecycle()

            TpbTheme(darkTheme = uiState.settings.darkTheme) {
                TpbAppShell(viewModel = viewModel, uiState = uiState)
            }
        }
    }
}

@Composable
fun TpbAppShell(
    viewModel: TpbViewModel,
    uiState: com.ysn4irix.tpb.ui.TpbUiState,
) {
    val navController = rememberNavController()
    val snackbarHostState = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()
    val context = LocalContext.current

    var showBatchOpenDialog by remember { mutableStateOf(false) }
    var batchStepIndex by remember { mutableStateOf<Int?>(null) }

    val exportLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.CreateDocument("text/plain"),
    ) { uri ->
        if (uri == null) return@rememberLauncherForActivityResult
        val content = MagnetIntentHelper.buildExportContent(uiState.selectedTorrents)
        if (content.isEmpty()) return@rememberLauncherForActivityResult
        runCatching {
            context.contentResolver.openOutputStream(uri)?.bufferedWriter()?.use { writer ->
                writer.write(content)
            }
        }.onSuccess {
            scope.launch {
                snackbarHostState.showSnackbar(
                    "Exported ${uiState.selectedTorrents.size} magnet link(s).",
                )
            }
        }.onFailure { err ->
            scope.launch {
                snackbarHostState.showSnackbar(err.message ?: "Failed to write export file.")
            }
        }
    }

    val backStackEntry by navController.currentBackStackEntryAsState()
    val currentDestination = backStackEntry?.destination

    Scaffold(
        snackbarHost = { SnackbarHost(snackbarHostState) },
        bottomBar = {
            Column {
                SelectionActionBar(
                    selectedCount = uiState.selectedTorrents.size,
                    onCopyAll = {
                        val count = MagnetIntentHelper.copyMagnetsToClipboard(
                            context,
                            uiState.selectedTorrents,
                        )
                        scope.launch {
                            snackbarHostState.showSnackbar("Copied $count magnet link(s).")
                        }
                    },
                    onOpenInClient = {
                        val selected = uiState.selectedTorrents
                        if (selected.size == 1) {
                            when (MagnetIntentHelper.openSingleMagnetInClient(context, selected.first())) {
                                MagnetDispatchResult.OpenedClient -> {
                                    scope.launch { snackbarHostState.showSnackbar("Opened in torrent client.") }
                                }
                                MagnetDispatchResult.CopiedFallbackNoClient -> {
                                    scope.launch {
                                        snackbarHostState.showSnackbar(
                                            "No torrent client installed; magnet copied to clipboard.",
                                        )
                                    }
                                }
                                MagnetDispatchResult.NothingSelected -> Unit
                            }
                        } else if (selected.size > 1) {
                            batchStepIndex = null
                            showBatchOpenDialog = true
                        }
                    },
                    onExportTxt = {
                        exportLauncher.launch(uiState.suggestedExportFilename)
                    },
                    onClearSelection = viewModel::clearSelection,
                )

                NavigationBar {
                    TopDestination.entries.forEach { dest ->
                        val selected = currentDestination?.hierarchy?.any {
                            it.route == dest.route
                        } == true
                        NavigationBarItem(
                            selected = selected,
                            onClick = {
                                navController.navigate(dest.route) {
                                    popUpTo(navController.graph.findStartDestination().id) {
                                        saveState = true
                                    }
                                    launchSingleTop = true
                                    restoreState = true
                                }
                            },
                            icon = {
                                val icon = when (dest) {
                                    TopDestination.SEARCH -> Icons.Outlined.Search
                                    TopDestination.LIBRARY -> Icons.Outlined.Bookmarks
                                    TopDestination.SETTINGS -> Icons.Outlined.Settings
                                }
                                Icon(imageVector = icon, contentDescription = dest.label)
                            },
                            label = { Text(dest.label) },
                        )
                    }
                }
            }
        },
    ) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = TopDestination.SEARCH.route,
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding),
        ) {
            composable(TopDestination.SEARCH.route) {
                SearchScreen(
                    uiState = uiState,
                    onQueryChanged = viewModel::onQueryChanged,
                    onModeSelected = viewModel::onModeSelected,
                    onRunSearch = { viewModel.runSearch() },
                    onCancelSearch = viewModel::cancelSearch,
                    onToggleBookmark = viewModel::toggleCurrentBookmark,
                    onSelectVariantTag = viewModel::selectVariantTag,
                    onSelectSeason = viewModel::selectSeason,
                    onSelectTvSubMode = viewModel::selectTvSubMode,
                    onSelectTvQuality = viewModel::selectTvPreferredQuality,
                    onSelectRecommended = viewModel::selectRecommendedEpisodes,
                    onClearSelection = viewModel::clearSelection,
                    onToggleEpisodeRelease = viewModel::toggleEpisodeReleaseSelection,
                    onToggleListRelease = viewModel::toggleReleaseSelection,
                    onListTextFilterChanged = viewModel::onListTextFilterChanged,
                    onListQualityFilterChanged = viewModel::onListQualityFilterChanged,
                    onCycleSort = {
                        val values = ReleaseSort.entries
                        val next = values[(values.indexOf(uiState.listSort) + 1) % values.size]
                        viewModel.onListSortChanged(next)
                    },
                    onSelectVisibleList = viewModel::selectAllVisibleListReleases,
                    onInspectFiles = viewModel::inspectTorrentFiles,
                )
            }

            composable(TopDestination.LIBRARY.route) {
                LibraryScreen(
                    history = uiState.history,
                    bookmarks = uiState.bookmarks,
                    onSelectSearch = { query, mode ->
                        navController.navigate(TopDestination.SEARCH.route) {
                            popUpTo(navController.graph.findStartDestination().id) {
                                saveState = true
                            }
                            launchSingleTop = true
                            restoreState = true
                        }
                        viewModel.runSearch(explicitQuery = query, explicitMode = mode)
                    },
                    onClearHistory = viewModel::clearHistory,
                    onRemoveBookmark = viewModel::removeBookmark,
                )
            }

            composable(TopDestination.SETTINGS.route) {
                SettingsScreen(
                    settings = uiState.settings,
                    onSaveSettings = viewModel::saveSettings,
                    onClearCache = viewModel::clearApiCache,
                    onShowMessage = { msg ->
                        scope.launch { snackbarHostState.showSnackbar(msg) }
                    },
                )
            }
        }
    }

    val inspected = uiState.inspectedTorrent
    if (inspected != null) {
        FileInspectorBottomSheet(
            torrent = inspected,
            isLoading = uiState.isLoadingFiles,
            files = uiState.inspectedFiles,
            errorMessage = uiState.filesError,
            onRetry = viewModel::retryInspectedFiles,
            onDismiss = viewModel::dismissFileInspector,
        )
    }

    if (showBatchOpenDialog && uiState.selectedTorrents.isNotEmpty()) {
        MultiMagnetHandoffDialog(
            torrents = uiState.selectedTorrents,
            currentStepIndex = batchStepIndex,
            onCopyAll = {
                val count = MagnetIntentHelper.copyMagnetsToClipboard(context, uiState.selectedTorrents)
                showBatchOpenDialog = false
                scope.launch { snackbarHostState.showSnackbar("Copied $count magnet link(s).") }
            },
            onExportTxt = {
                showBatchOpenDialog = false
                exportLauncher.launch(uiState.suggestedExportFilename)
            },
            onSendStep = { stepIdx ->
                val target = uiState.selectedTorrents.getOrNull(stepIdx)
                if (target != null) {
                    val result = MagnetIntentHelper.openSingleMagnetInClient(context, target)
                    if (result == MagnetDispatchResult.CopiedFallbackNoClient) {
                        showBatchOpenDialog = false
                        scope.launch {
                            snackbarHostState.showSnackbar(
                                "No torrent client installed; magnets copied instead.",
                            )
                        }
                    } else if (stepIdx + 1 >= uiState.selectedTorrents.size) {
                        showBatchOpenDialog = false
                    } else {
                        batchStepIndex = stepIdx + 1
                    }
                } else {
                    showBatchOpenDialog = false
                }
            },
            onDismiss = {
                showBatchOpenDialog = false
                batchStepIndex = null
            },
        )
    }
}
