package com.ysn4irix.tpb.ui.theme

import org.junit.Assert.assertFalse
import org.junit.Test
import java.io.File

class TpbThemeColorTest {
    @Test
    fun themeAndLauncherContainZeroPurpleOrVioletHexCodes() {
        val forbidden = Regex(
            "#(?:FF)?(?:7c3aed|8b5cf6|a855f7|9333ea|6366f1|c084fc|d946ef|ec4899|6d28d9|5b21b6)",
            RegexOption.IGNORE_CASE,
        )
        val themeFile = File("src/main/java/com/ysn4irix/tpb/ui/theme/TpbTheme.kt")
        val fgIcon = File("src/main/res/drawable/ic_launcher_foreground.xml")
        val bgIcon = File("src/main/res/drawable/ic_launcher_background.xml")

        listOf(themeFile, fgIcon, bgIcon).forEach { file ->
            if (file.exists()) {
                val content = file.readText()
                assertFalse(
                    "Found forbidden purple hex in ${file.path}",
                    forbidden.containsMatchIn(content),
                )
            }
        }
    }
}
