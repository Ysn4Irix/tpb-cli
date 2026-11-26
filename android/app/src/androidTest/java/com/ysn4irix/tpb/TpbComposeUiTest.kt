package com.ysn4irix.tpb

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextReplacement
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class TpbComposeUiTest {
    @get:Rule
    val composeRule = createAndroidComposeRule<MainActivity>()

    @Test
    fun navigationTabsAndSettingsValidationWorkOnDevice() {
        composeRule.onNodeWithText("TPB / Apibay Mobile").assertIsDisplayed()

        composeRule.onNodeWithText("Movies").performClick()
        composeRule.onNodeWithText("Search movie title...").assertIsDisplayed()

        composeRule.onNodeWithText("Library").performClick()
        composeRule.onNodeWithText("History (0)").assertIsDisplayed()
        composeRule.onNodeWithText("Bookmarks (0)").performClick()

        composeRule.onNodeWithText("Settings").performClick()
        composeRule.onNodeWithText("Network & Appearance").assertIsDisplayed()

        composeRule.onNodeWithText("https://apibay.org").performTextReplacement("ftp://invalid-mirror")
        composeRule.onNodeWithText("Save Settings").performClick()
        composeRule.onNodeWithText("API URL must start with http:// or https:// and include a hostname.")
            .assertIsDisplayed()

        composeRule.onNodeWithText("ftp://invalid-mirror").performTextReplacement("https://apibay.org")
        composeRule.onNodeWithText("Optional Proxy (HTTP / SOCKS5)").performTextReplacement("ftp://badproxy")
        composeRule.onNodeWithText("Save Settings").performClick()
        composeRule.onNodeWithText(
            "Proxy URL must use http://, https://, socks5://, or socks5h:// and include a host.",
        ).assertIsDisplayed()
    }
}
