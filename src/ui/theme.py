"""Theme sombre sobre pour l'interface PySide6.

Palette : fond gris tres fonce, accents cyan/bleu pour les actions,
rouge reserve aux actions destructives (section 10).
"""

from __future__ import annotations

BACKGROUND = "#1e1f22"
SURFACE = "#26282c"
SURFACE_ALT = "#2d2f34"
BORDER = "#3a3d42"
TEXT = "#e6e6e6"
TEXT_MUTED = "#9aa0a6"
ACCENT = "#22b8cf"
ACCENT_HOVER = "#3bc9db"
DANGER = "#e03131"
DANGER_HOVER = "#f03e3e"
SUCCESS = "#2f9e44"

STYLESHEET = f"""
QWidget {{
    background-color: {BACKGROUND};
    color: {TEXT};
    font-family: 'Ubuntu', 'DejaVu Sans', sans-serif;
    font-size: 13px;
}}

QMainWindow, QDialog {{ background-color: {BACKGROUND}; }}

#sidebar {{
    background-color: {SURFACE};
    border-right: 1px solid {BORDER};
}}
#sidebarTitle {{
    font-size: 15px;
    font-weight: bold;
    color: {ACCENT};
    padding: 16px 12px;
}}
#sidebarButton {{
    text-align: left;
    padding: 10px 14px;
    border: none;
    border-radius: 6px;
    background-color: transparent;
    color: {TEXT};
    font-size: 13px;
}}
#sidebarButton:hover {{ background-color: {SURFACE_ALT}; }}
#sidebarButton:checked {{
    background-color: {SURFACE_ALT};
    color: {ACCENT};
    font-weight: bold;
}}

#pageTitle {{
    font-size: 20px;
    font-weight: bold;
    padding: 8px 0 4px 0;
}}
#pageSubtitle {{ color: {TEXT_MUTED}; padding-bottom: 8px; }}

QFrame#card {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 8px;
}}
QLabel#cardTitle {{ color: {TEXT_MUTED}; font-size: 12px; }}
QLabel#cardValue {{ font-size: 22px; font-weight: bold; color: {TEXT}; }}

QPushButton {{
    background-color: {SURFACE_ALT};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 8px 16px;
}}
QPushButton:hover {{ border-color: {ACCENT}; }}
QPushButton:disabled {{ color: {TEXT_MUTED}; background-color: {SURFACE}; }}

QPushButton#primary {{
    background-color: {ACCENT};
    color: #0b0c0e;
    border: none;
    font-weight: bold;
}}
QPushButton#primary:hover {{ background-color: {ACCENT_HOVER}; }}

QPushButton#danger {{
    background-color: {DANGER};
    color: white;
    border: none;
    font-weight: bold;
}}
QPushButton#danger:hover {{ background-color: {DANGER_HOVER}; }}

QLineEdit, QComboBox, QSpinBox, QPlainTextEdit, QTextEdit {{
    background-color: {BACKGROUND};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 8px;
    selection-background-color: {ACCENT};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border-color: {ACCENT}; }}

QTableWidget {{
    background-color: {SURFACE};
    gridline-color: {BORDER};
    border: 1px solid {BORDER};
    border-radius: 6px;
}}
QHeaderView::section {{
    background-color: {SURFACE_ALT};
    color: {TEXT_MUTED};
    padding: 6px;
    border: none;
    border-right: 1px solid {BORDER};
}}
QTableWidget::item:selected {{ background-color: {SURFACE_ALT}; color: {TEXT}; }}

QScrollBar:vertical {{ background: {BACKGROUND}; width: 10px; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 5px; }}

QGroupBox {{
    border: 1px solid {BORDER};
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 8px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: {TEXT_MUTED};
}}
"""
