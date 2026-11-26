package com.ysn4irix.tpb.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color

@Immutable
data class TpbSemanticColors(
    val seedHealthy: Color,
    val seedModerate: Color,
    val seedLow: Color,
    val trustedBadge: Color,
    val accentSubtle: Color,
    val surfaceAlt: Color,
    val mutedText: Color,
)

val LocalTpbSemanticColors = staticCompositionLocalOf {
    TpbSemanticColors(
        seedHealthy = Color(0xFF22C55E),
        seedModerate = Color(0xFFF59E0B),
        seedLow = Color(0xFFEF4444),
        trustedBadge = Color(0xFF06B6D4),
        accentSubtle = Color(0xFF132A3A),
        surfaceAlt = Color(0xFF1F242C),
        mutedText = Color(0xFF8B949E),
    )
}

private val TpbDarkColorScheme = darkColorScheme(
    primary = Color(0xFF0EA5E9),
    onPrimary = Color(0xFFFFFFFF),
    primaryContainer = Color(0xFF132A3A),
    onPrimaryContainer = Color(0xFF38BDF8),
    secondary = Color(0xFF06B6D4),
    onSecondary = Color(0xFF0D1117),
    secondaryContainer = Color(0xFF1F242C),
    onSecondaryContainer = Color(0xFFF0F6FC),
    tertiary = Color(0xFF22C55E),
    onTertiary = Color(0xFF0D1117),
    background = Color(0xFF0D1117),
    onBackground = Color(0xFFF0F6FC),
    surface = Color(0xFF161B22),
    onSurface = Color(0xFFF0F6FC),
    surfaceVariant = Color(0xFF1F242C),
    onSurfaceVariant = Color(0xFF8B949E),
    outline = Color(0xFF30363D),
    outlineVariant = Color(0xFF21262D),
    error = Color(0xFFEF4444),
    onError = Color(0xFFFFFFFF),
)

private val TpbLightColorScheme = lightColorScheme(
    primary = Color(0xFF0284C7),
    onPrimary = Color(0xFFFFFFFF),
    primaryContainer = Color(0xFFE0F2FE),
    onPrimaryContainer = Color(0xFF0369A1),
    secondary = Color(0xFF0E7490),
    onSecondary = Color(0xFFFFFFFF),
    secondaryContainer = Color(0xFFF1F5F9),
    onSecondaryContainer = Color(0xFF0F172A),
    tertiary = Color(0xFF15803D),
    onTertiary = Color(0xFFFFFFFF),
    background = Color(0xFFF8FAFC),
    onBackground = Color(0xFF0F172A),
    surface = Color(0xFFFFFFFF),
    onSurface = Color(0xFF0F172A),
    surfaceVariant = Color(0xFFF1F5F9),
    onSurfaceVariant = Color(0xFF475569),
    outline = Color(0xFFCBD5E1),
    outlineVariant = Color(0xFFE2E8F0),
    error = Color(0xFFDC2626),
    onError = Color(0xFFFFFFFF),
)

private val DarkSemantics = TpbSemanticColors(
    seedHealthy = Color(0xFF22C55E),
    seedModerate = Color(0xFFF59E0B),
    seedLow = Color(0xFFEF4444),
    trustedBadge = Color(0xFF06B6D4),
    accentSubtle = Color(0xFF132A3A),
    surfaceAlt = Color(0xFF1F242C),
    mutedText = Color(0xFF8B949E),
)

private val LightSemantics = TpbSemanticColors(
    seedHealthy = Color(0xFF15803D),
    seedModerate = Color(0xFFB45309),
    seedLow = Color(0xFFDC2626),
    trustedBadge = Color(0xFF0E7490),
    accentSubtle = Color(0xFFE0F2FE),
    surfaceAlt = Color(0xFFF1F5F9),
    mutedText = Color(0xFF475569),
)

@Composable
fun TpbTheme(
    darkTheme: Boolean = true,
    content: @Composable () -> Unit,
) {
    val colorScheme = if (darkTheme) TpbDarkColorScheme else TpbLightColorScheme
    val semantics = if (darkTheme) DarkSemantics else LightSemantics

    CompositionLocalProvider(LocalTpbSemanticColors provides semantics) {
        MaterialTheme(
            colorScheme = colorScheme,
            typography = Typography(),
            content = content,
        )
    }
}
