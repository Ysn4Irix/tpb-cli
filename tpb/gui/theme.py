"""Dark and Light QSS themes and semantic palette tokens for tpb-cli GUI."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ThemePalette:
    """Semantic colors used both in QSS and custom model/widget painting."""

    name: str
    canvas: str
    surface: str
    surface_alt: str
    border: str
    text: str
    text_muted: str
    accent: str
    accent_hover: str
    accent_subtle: str
    seed_high: str
    seed_mid: str
    seed_low: str
    trusted: str
    badge_bg: str


DARK_PALETTE = ThemePalette(
    name="dark",
    canvas="#0D1117",
    surface="#161B22",
    surface_alt="#1F242C",
    border="#30363D",
    text="#F0F6FC",
    text_muted="#8B949E",
    accent="#0EA5E9",
    accent_hover="#38BDF8",
    accent_subtle="#132A3A",
    seed_high="#22C55E",
    seed_mid="#F59E0B",
    seed_low="#EF4444",
    trusted="#06B6D4",
    badge_bg="#21262D",
)

LIGHT_PALETTE = ThemePalette(
    name="light",
    canvas="#F8FAFC",
    surface="#FFFFFF",
    surface_alt="#F1F5F9",
    border="#CBD5E1",
    text="#0F172A",
    text_muted="#475569",
    accent="#0284C7",
    accent_hover="#0369A1",
    accent_subtle="#E0F2FE",
    seed_high="#15803D",
    seed_mid="#B45309",
    seed_low="#DC2626",
    trusted="#0E7490",
    badge_bg="#E2E8F0",
)


def get_palette(theme_name: str) -> ThemePalette:
    """Return dark or light palette by name."""
    return LIGHT_PALETTE if str(theme_name).lower() == "light" else DARK_PALETTE


def build_stylesheet(theme_name: str) -> str:
    """Build clean technical QSS stylesheet for the active theme."""
    p = get_palette(theme_name)
    return f"""
    QMainWindow, QDialog {{
        background-color: {p.canvas};
        color: {p.text};
        font-family: "Segoe UI", "Inter", sans-serif;
        font-size: 13px;
    }}
    QWidget {{
        color: {p.text};
    }}
    QFrame#HeaderBar, QFrame#ActionBar, QFrame#PanelSurface {{
        background-color: {p.surface};
        border: 1px solid {p.border};
        border-radius: 3px;
    }}
    QLabel#MutedLabel {{
        color: {p.text_muted};
    }}
    QLabel#BannerInfo {{
        background-color: {p.accent_subtle};
        border: 1px solid {p.accent};
        border-radius: 2px;
        padding: 6px 10px;
        color: {p.text};
    }}
    QLineEdit, QComboBox, QSpinBox {{
        background-color: {p.surface_alt};
        border: 1px solid {p.border};
        border-radius: 2px;
        padding: 6px 10px;
        color: {p.text};
        selection-background-color: {p.accent};
        selection-color: #FFFFFF;
    }}
    QLineEdit:focus, QComboBox:focus {{
        border-color: {p.accent};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {p.surface};
        border: 1px solid {p.border};
        selection-background-color: {p.accent_subtle};
        selection-color: {p.text};
    }}
    QPushButton {{
        background-color: {p.surface_alt};
        border: 1px solid {p.border};
        border-radius: 2px;
        padding: 6px 12px;
        color: {p.text};
        font-weight: 500;
    }}
    QPushButton:hover {{
        border-color: {p.accent};
        background-color: {p.badge_bg};
    }}
    QPushButton:disabled {{
        color: {p.text_muted};
        background-color: {p.canvas};
        border-color: {p.border};
    }}
    QPushButton#PrimaryButton {{
        background-color: {p.accent};
        border: 1px solid {p.accent};
        color: #FFFFFF;
        font-weight: 600;
    }}
    QPushButton#PrimaryButton:hover {{
        background-color: {p.accent_hover};
        border-color: {p.accent_hover};
    }}
    QPushButton#PrimaryButton:disabled {{
        background-color: {p.badge_bg};
        border-color: {p.border};
        color: {p.text_muted};
    }}
    QPushButton[checkable="true"]:checked {{
        background-color: {p.accent_subtle};
        border-color: {p.accent};
        color: {p.text};
        font-weight: 600;
    }}
    QTableView, QTreeWidget, QListWidget {{
        background-color: {p.surface};
        alternate-background-color: {p.surface_alt};
        border: 1px solid {p.border};
        border-radius: 2px;
        gridline-color: {p.border};
        selection-background-color: {p.accent_subtle};
        selection-color: {p.text};
    }}
    QHeaderView::section {{
        background-color: {p.surface_alt};
        color: {p.text_muted};
        border: none;
        border-right: 1px solid {p.border};
        border-bottom: 1px solid {p.border};
        padding: 6px 8px;
        font-weight: 600;
        text-transform: uppercase;
        font-size: 11px;
    }}
    QTabWidget::pane {{
        border: 1px solid {p.border};
        background-color: {p.surface};
        border-radius: 2px;
    }}
    QTabBar::tab {{
        background-color: {p.surface_alt};
        border: 1px solid {p.border};
        padding: 6px 14px;
        margin-right: 2px;
        color: {p.text_muted};
    }}
    QTabBar::tab:selected {{
        background-color: {p.surface};
        color: {p.text};
        border-bottom-color: {p.accent};
        font-weight: 600;
    }}
    QSplitter::handle {{
        background-color: {p.border};
    }}
    QStatusBar {{
        background-color: {p.surface};
        border-top: 1px solid {p.border};
        color: {p.text_muted};
    }}
    QProgressBar {{
        background-color: {p.surface_alt};
        border: 1px solid {p.border};
        border-radius: 2px;
        text-align: center;
    }}
    QProgressBar::chunk {{
        background-color: {p.accent};
        border-radius: 1px;
    }}
    QScrollBar:vertical, QScrollBar:horizontal {{
        background-color: {p.canvas};
        width: 10px;
        height: 10px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
        background-color: {p.border};
        border-radius: 2px;
        min-height: 24px;
    }}
    QScrollBar::handle:hover {{
        background-color: {p.text_muted};
    }}
    QScrollBar::add-line, QScrollBar::sub-line {{
        height: 0px;
        width: 0px;
    }}
    """
