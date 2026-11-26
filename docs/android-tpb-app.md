# Android Client (`android-tpb-app`) — Project Plan

## Overview
Build a native Android application under `android/` (on the `master` branch) providing full functional parity with the `tpb-cli` Desktop GUI (`v0.3.0`): Apibay TV Series discovery (regional disambiguation, auto-detected seasons, season packs, and multi-quality episode picking), Movies/General filterable & sortable search, torrent file inspection (`/f.php`), tracker-enriched `magnet:` handoff/clipboard/`.txt` SAF export, search history & bookmarks, custom mirror + HTTP/SOCKS5 proxy configuration, and Dark/Light Material 3 styling anchored to the **Cyan Vector Magnet** brand.

- **Project Type:** `MOBILE` (Native Android — Kotlin + Jetpack Compose + Material 3)
- **Locked Decisions:** Native Kotlin/Compose stack (`1A`), `android/` inside `tpb-cli` on `master` (`2A`), full v1 desktop-parity feature suite (`3A`), custom Apibay mirror + HTTP/SOCKS5 proxy support (`4A`).

---

## Success Criteria
- [ ] Regex/parser parity with [tpb/parser.py](tpb/parser.py) & [tpb/models.py](tpb/models.py) verified by JUnit tests (`S01E01`, `S01E01-E04`, `1x02`, season packs, quality/codec extraction, `US`/`UK`/`AU`/`NZ`/`CA` disambiguation, tracker magnet URIs, dummy `id="0"` handling).
- [ ] All interactive search, cancellation, error/retry, file inspection, unchecked-by-default selection, and batch export flows work end-to-end with >= 48dp touch targets and Material 3 OLED Dark (`#0D1117` / `#0EA5E9`) & Light (`#F8FAFC` / `#0284C7`) themes (zero purple/violet hex codes).
- [ ] Custom HTTP/HTTPS mirror URL and HTTP/SOCKS5 proxy routing (`socks5://127.0.0.1:9050`) work via OkHttp `Proxy` with boundary validation and graceful fallback when no `magnet:` handler app is installed.
- [ ] `./gradlew test lintDebug assembleDebug` passes cleanly on Windows against `C:\Android` (`compileSdk 35` / `minSdk 26`), and debug APK installs and boots on the `android-35` emulator via `adb`.

---

## Tech Stack
| Layer | Choice | Rationale |
|---|---|---|
| **Language / Build** | Kotlin + Gradle Kotlin DSL + Version Catalog (`libs.versions.toml`) | Native Android SDK `35`/`36` & Java `21` already installed at `C:\Android` |
| **UI & Navigation** | Jetpack Compose BOM + Material 3 + Navigation Compose | Adaptive 3-tab bottom bar (`Search`, `Library`, `Settings`), predictive back, OLED Dark/Light palette |
| **Networking** | OkHttp 4 + Kotlinx Serialization + Coroutines | Lightweight JSON parsing + clean HTTP / SOCKS5 `java.net.Proxy` routing + cancellation |
| **Persistence** | Jetpack DataStore (Proto/Preferences) + Room (or JSON-backed Store) | Offline settings, recent search history, and pinned bookmarks |
| **Testing / Quality** | JUnit 4/5, Kotlin Coroutines Test, OkHttp MockWebServer, Compose UI Test, Android Lint, ktlint | Fast JVM parser/repo tests + offline API contract tests + device UI verification |

---

## File Structure (`android/`)
```text
android/
├── build.gradle.kts / settings.gradle.kts / gradle/libs.versions.toml / gradlew(.bat)
└── app/src/
    ├── main/
    │   ├── AndroidManifest.xml                   # INTERNET, <queries> for magnet ACTION_VIEW, App icon
    │   ├── res/                                  # Adaptive Cyan Vector Magnet mipmap, strings, themes
    │   └── java/com/ysn4irix/tpb/
    │       ├── TpbApplication.kt
    │       ├── MainActivity.kt                   # Edge-to-edge + 3-tab shell + bottom SelectionActionBar
    │       ├── domain/
    │       │   ├── model/                        # Torrent, TorrentFile, TvSeasonSummary, AppSettings, UiState
    │       │   └── parser/                       # TitleParser.kt (exact parity with tpb/parser.py) & MagnetBuilder.kt
    │       ├── data/
    │       │   ├── remote/                       # ApibayApiClient.kt (/q.php, /f.php, URL/proxy validation, cache)
    │       │   └── local/                        # SettingsRepository.kt & LibraryRepository.kt (DataStore / Room)
    │       └── ui/
    │           ├── theme/                        # TpbTheme.kt (Cyan/Slate Dark & Light tokens, NO dynamic purple)
    │           ├── search/                       # SearchScreen, TvBrowserContent, ReleaseListContent, FileInspectorSheet
    │           ├── library/                      # LibraryScreen (History & Bookmarks 1-tap re-run)
    │           └── settings/                     # SettingsScreen (Mirror, Proxy, Default Quality, Theme, Clear Cache)
    ├── test/...                                  # Unit tests: parser, magnet URI, URL/proxy validation, MockWebServer API
    └── androidTest/...                           # Compose UI & navigation state tests
```

---

## Task Breakdown

- [x] **T1 — Initialize Gradle Android Project & Wrapper** · *Agent:* `mobile-developer` · *Skills:* `clean-code`, `android-cli`
  - *Dependencies:* None
  - *INPUT:* `C:\Android` (`compileSdk 35`, `minSdk 26`, `targetSdk 35`), Java `21`, `libs.versions.toml`
  - *OUTPUT:* Compiling `android/` skeleton with Gradle wrapper (`gradlew.bat`), Compose BOM, Material 3, Navigation, OkHttp, Kotlinx Serialization, DataStore, and Manifest `<queries>` for `magnet:` scheme
  - *VERIFY:* Run `.\gradlew.bat tasks` in `android/` (exits `0`)

- [x] **T2 — Brand Theme & Cyan Vector Magnet Adaptive Icon** · *Agent:* `mobile-developer` · *Skills:* `mobile-design`, `design-spec`
  - *Dependencies:* T1
  - *INPUT:* Desktop palette tokens in [tpb/gui/theme.py](tpb/gui/theme.py) and icon assets in [tpb/gui/assets/](tpb/gui/assets/)
  - *OUTPUT:* `TpbTheme.kt` (`#0D1117` OLED Dark, `#F8FAFC` Light, `#0EA5E9`/`#38BDF8` accents, health colors, zero purple/violet) + Android adaptive launcher icon (`ic_launcher`, `ic_launcher_foreground/background`)
  - *VERIFY:* Color check confirms no purple hex values; Compose Preview/unit screenshot compiles under `assembleDebug`

- [x] **T3 — Port Domain Models, Magnet Builder & TV Parser** · *Agent:* `mobile-developer` · *Skills:* `clean-code`, `tdd-workflow`
  - *Dependencies:* T1
  - *INPUT:* [tpb/models.py](tpb/models.py) & [tpb/parser.py](tpb/parser.py) regexes + `DEFAULT_TRACKERS` + `tests/test_parser.py` / `tests/test_models.py` fixtures
  - *OUTPUT:* `Torrent.kt`, `MagnetBuilder.kt`, `TitleParser.kt`, `Formatters.kt` + comprehensive JVM unit tests
  - *VERIFY:* `.\gradlew.bat :app:testDebugUnitTest --tests "*.parser.*"` and `"*.model.*"` pass 100%

- [x] **T4 — Apibay OkHttp Client, Mirror/Proxy Validation & Cache** · *Agent:* `mobile-developer` · *Skills:* `clean-code`, `vulnerability-scanner`
  - *Dependencies:* T3
  - *INPUT:* [tpb/api.py](tpb/api.py) contract (`/q.php`, `/f.php`, categories `0`/`207`/`208`, dummy `id="0"`, `validate_http_url`, `validate_proxy_url`)
  - *OUTPUT:* `NetworkValidator.kt`, `ApibayApiClient.kt` (HTTP & SOCKS5 `Proxy`, cancellation-safe coroutines, thread-safe in-memory cache, normalized `/f.php` lists) + MockWebServer tests
  - *VERIFY:* `MockWebServer` unit tests verify search fallback (`208->0`, `207->0`), proxy/URL rejection, and timeout/error mapping

- [x] **T5 — Persistent Settings, History & Bookmarks Store** · *Agent:* `mobile-developer` · *Skills:* `mobile-design`, `testing-patterns`
  - *Dependencies:* T3, T4
  - *INPUT:* Mirror/proxy/theme/quality prefs + search history (deduped cap 25) & bookmarks model
  - *OUTPUT:* `TpbPreferencesRepository.kt` (DataStore) + repository unit tests
  - *VERIFY:* Unit tests verify save/reload, deduplication, clearing history, and toggling bookmarks

- [x] **T6 — Search Screen: TV Series Browser, Movies/General & Loading/Error States** · *Agent:* `mobile-developer` · *Skills:* `mobile-design`
  - *Dependencies:* T2, T4, T5
  - *INPUT:* Unchecked-by-default UX, TV regional disambiguation chips (`US`/`UK`/`All`), season tabs/chips, Episodes vs Season Packs vs All Releases segments, `Select Recommended`, resolution/text filters, indeterminate search progress + Cancel + Retry
  - *OUTPUT:* `TpbViewModel.kt`, `SearchScreen.kt`, `ReleaseComponents.kt` (`LazyColumn` with stable ID keys, >= 48dp touch targets)
  - *VERIFY:* StateFlow ViewModel tests + Compose UI compilation pass

- [x] **T7 — File Inspector Sheet, Magnet Action Bar & Android Export/Intent Handoff** · *Agent:* `mobile-developer` · *Skills:* `mobile-design`
  - *Dependencies:* T6
  - *INPUT:* `/f.php` file list API + selected `Torrent` batch state
  - *OUTPUT:* `FileInspectorBottomSheet.kt`, `SelectionActionBar.kt`, `MultiMagnetHandoffDialog.kt`, `MagnetIntentHelper.kt` (`ACTION_VIEW` `magnet:` single-tap & stepped multi-magnet handoff + SAF `.txt` export)
  - *VERIFY:* Formatter/magnet export unit tests + `assembleDebug` pass cleanly

- [x] **T8 — Library & Settings Screens + Navigation Integration** · *Agent:* `mobile-developer` · *Skills:* `mobile-design`
  - *Dependencies:* T5, T6
  - *INPUT:* 3-destination Material 3 `NavigationBar` (`Search`, `Library`, `Settings`), saved-tab state preservation, inline URL/proxy error display
  - *OUTPUT:* `LibraryScreen.kt`, `SettingsScreen.kt`, `MainActivity.kt` (`TpbAppShell`) + Compose UI `androidTest` coverage
  - *VERIFY:* `assembleAndroidTest` compiles `TpbComposeUiTest.kt` and `lintDebug` reports 0 errors

- [x] **T9 — CI/CD, Changelog & Root Docs Integration** · *Agent:* `mobile-developer` · *Skills:* `lint-and-validate`, `documentation-templates`
  - *Dependencies:* T1–T8
  - *INPUT:* Existing [AGENTS.md](AGENTS.md), [README.md](README.md), [CHANGELOG.md](CHANGELOG.md), `.github/workflows/`
  - *OUTPUT:* Path-filtered `.github/workflows/android-ci.yml`, updated `CHANGELOG.md` + `README.md`, bumped `0.4.0` version
  - *VERIFY:* `yaml.safe_load` passes and Gradle tasks mirror CI commands verbatim

---

## Phase X — Final Verification Checklist
- [x] Unit + MockWebServer suite: `.\gradlew.bat :app:testDebugUnitTest` passes cleanly (12 tests, 0 failures)
- [x] Android Lint & Kotlin compilation: `.\gradlew.bat lintDebug` passes with 0 errors
- [x] Debug APK build: `.\gradlew.bat assembleDebug` produces `app-debug.apk`
- [x] AndroidTest APK compilation: `.\gradlew.bat assembleAndroidTest` compiles `TpbComposeUiTest.kt`
- [x] Zero purple/violet hex codes verified by `TpbThemeColorTest`
- [ ] Live emulator verification (`android-35` + `connectedDebugAndroidTest`): skipped by explicit user request (`"Do not use emulator skip"`)

## ✅ PHASE X COMPLETE
- Status: Complete within scope (`testDebugUnitTest`, `lintDebug`, `assembleDebug`, and `assembleAndroidTest` verified without emulator execution).
- Skipped Gate: Live Android emulator boot and `connectedDebugAndroidTest` runtime execution skipped per explicit user directive (`"Do not use emulator skip"`).
