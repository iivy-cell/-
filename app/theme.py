# -*- coding: utf-8 -*-
"""Visual theme: hanji-ink dark UI with Korean obangsaek accents."""

BG = "#120F0D"        # deep ink
BG2 = "#181310"
SURFACE = "#1E1813"
SURFACE2 = "#28201A"
ELEV = "#31261E"
LINE = "#3A2D23"
LINE_SOFT = "#2C221A"

TEXT = "#F2E9DA"      # hanji white
MUTED = "#A79781"
FAINT = "#6F6252"

ACCENT = "#E2543F"    # Korean red
ACCENT_HOVER = "#EF6B55"
BLUE = "#3E8FB0"      # Korean blue
GOLD = "#D9A85E"
SELECT = "#3A2A22"


def build_qss() -> str:
    return f"""
* {{
    outline: none;
}}
QWidget {{
    background: {BG};
    color: {TEXT};
    font-family: "Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC", sans-serif;
    font-size: 13px;
}}
QMainWindow, #RootWindow {{
    background: {BG};
}}

/* ------------------------------------------------- title bar */
#TitleBar {{
    background: {BG};
    border-bottom: 1px solid {LINE_SOFT};
}}
#BrandName {{
    color: {TEXT};
    font-size: 16px;
    font-weight: 600;
}}
#BrandSub {{
    color: {FAINT};
    font-size: 10px;
    letter-spacing: 2px;
}}
#SearchEdit {{
    background: {SURFACE2};
    border: 1px solid {LINE};
    border-radius: 16px;
    padding: 5px 14px 5px 32px;
    color: {TEXT};
    selection-background-color: {ACCENT};
}}
#SearchEdit:focus {{
    border: 1px solid {GOLD};
    background: {ELEV};
}}
#SearchIcon {{
    color: {MUTED};
    background: transparent;
}}
QPushButton#WinBtn {{
    background: transparent;
    border: none;
    border-radius: 0px;
    width: 44px; height: 34px;
}}
QPushButton#WinBtn:hover {{ background: {SURFACE2}; }}
QPushButton#WinBtn[kind="close"]:hover {{ background: #C0392B; }}

/* ------------------------------------------------- sidebar */
#Sidebar {{
    background: {BG2};
    border-right: 1px solid {LINE_SOFT};
}}
#NavList {{
    background: transparent;
    border: none;
    color: {MUTED};
    font-size: 14px;
}}
#NavList::item {{
    height: 40px;
    padding-left: 14px;
    border-radius: 8px;
    margin: 2px 10px;
}}
#NavList::item:hover {{ background: {SURFACE2}; color: {TEXT}; }}
#NavList::item:selected {{
    background: {SELECT};
    color: {TEXT};
    font-weight: 600;
}}
#SideTitle {{
    color: {FAINT};
    font-size: 11px;
    padding: 10px 22px 4px 22px;
    letter-spacing: 3px;
}}
QPushButton#Chip {{
    background: {SURFACE2};
    color: {MUTED};
    border: 1px solid {LINE};
    border-radius: 12px;
    padding: 3px 12px;
    font-size: 12px;
}}
QPushButton#Chip:hover {{ color: {TEXT}; border-color: {GOLD}; }}
QPushButton#Chip:checked {{
    background: {SELECT};
    color: {GOLD};
    border-color: {GOLD};
    font-weight: 600;
}}

/* ------------------------------------------------- hero */
#HeroCard {{ background: transparent; }}
#HeroCover {{ border-radius: 10px; }}
#HeroTitle {{
    color: {TEXT};
    font-size: 26px;
    font-weight: 700;
}}
#HeroMeta {{ color: {MUTED}; font-size: 12px; }}
#HeroDesc {{ color: {FAINT}; font-size: 12px; }}
#HeroBadge {{
    color: {GOLD};
    border: 1px solid {GOLD};
    border-radius: 4px;
    padding: 1px 8px;
    font-size: 11px;
    background: transparent;
}}
QPushButton#PrimaryBtn {{
    background: {ACCENT};
    color: #FFF7EC;
    border: none;
    border-radius: 19px;
    padding: 9px 26px;
    font-size: 14px;
    font-weight: 600;
}}
QPushButton#PrimaryBtn:hover {{ background: {ACCENT_HOVER}; }}
QPushButton#PrimaryBtn:pressed {{ background: #C7432F; }}
QPushButton#GhostBtn {{
    background: transparent;
    color: {MUTED};
    border: 1px solid {LINE};
    border-radius: 17px;
    padding: 8px 20px;
    font-size: 13px;
}}
QPushButton#GhostBtn:hover {{ color: {TEXT}; border-color: {MUTED}; }}

/* ------------------------------------------------- table */
#SongTable {{
    background: transparent;
    border: none;
    gridline-color: transparent;
    selection-background-color: {SELECT};
    selection-color: {TEXT};
}}
#SongTable::item {{ border: none; }}
#SongTable QHeaderView::section {{
    background: transparent;
    color: {FAINT};
    border: none;
    border-bottom: 1px solid {LINE_SOFT};
    padding: 6px 8px;
    font-size: 12px;
}}
#SongTable QTableCornerButton::section {{ background: transparent; border: none; }}
QScrollBar:vertical {{
    background: transparent; width: 8px; margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {LINE}; border-radius: 4px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {MUTED}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 8px; }}
QScrollBar::handle:horizontal {{
    background: {LINE}; border-radius: 4px; min-width: 30px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ------------------------------------------------- lists */
#SimpleList {{
    background: transparent;
    border: none;
    color: {TEXT};
    font-size: 13px;
}}
#SimpleList::item {{
    height: 52px;
    border-radius: 8px;
    margin: 2px 12px;
    padding-left: 10px;
}}
#SimpleList::item:hover {{ background: {SURFACE2}; }}
#SimpleList::item:selected {{ background: {SELECT}; color: {TEXT}; }}

/* ------------------------------------------------- now playing */
#NowPanel {{
    background: {BG2};
    border-left: 1px solid {LINE_SOFT};
}}
#NowTitle {{ color: {TEXT}; font-size: 17px; font-weight: 600; background: transparent; }}
#NowArtist {{ color: {MUTED}; font-size: 12px; background: transparent; }}
#NowHint {{
    color: {FAINT};
    font-size: 12px;
    background: {SURFACE};
    border: 1px dashed {LINE};
    border-radius: 10px;
    padding: 14px;
}}

/* ------------------------------------------------- transport */
#TransportBar {{
    background: {SURFACE};
    border-top: 1px solid {LINE_SOFT};
}}
#TrackTitle {{ color: {TEXT}; font-size: 13px; font-weight: 600; background: transparent; }}
#TrackArtist {{ color: {MUTED}; font-size: 11px; background: transparent; }}
#TimeLabel {{ color: {FAINT}; font-size: 11px; background: transparent; }}

QPushButton#RoundBtn {{
    background: transparent;
    border: none;
    border-radius: 17px;
}}
QPushButton#RoundBtn:hover {{ background: {SURFACE2}; }}
QPushButton#BigPlay {{
    background: {ACCENT};
    border: none;
    border-radius: 23px;
}}
QPushButton#BigPlay:hover {{ background: {ACCENT_HOVER}; }}

QSlider#SeekSlider {{
    background: transparent;
    height: 18px;
}}
QSlider#SeekSlider::groove:horizontal {{
    height: 4px;
    border-radius: 2px;
    background: {LINE};
}}
QSlider#SeekSlider::sub-page:horizontal {{
    background: {ACCENT};
    border-radius: 2px;
}}
QSlider#SeekSlider::handle:horizontal {{
    background: {TEXT};
    width: 11px; height: 11px;
    margin: -4px 0;
    border-radius: 5.5px;
}}
QSlider#VolumeSlider {{
    background: transparent; width: 80px; height: 18px;
}}
QSlider#VolumeSlider::groove:horizontal {{
    height: 3px; border-radius: 1.5px; background: {LINE};
}}
QSlider#VolumeSlider::sub-page:horizontal {{
    background: {GOLD}; border-radius: 1.5px;
}}
QSlider#VolumeSlider::handle:horizontal {{
    background: {TEXT}; width: 9px; height: 9px;
    margin: -3px 0; border-radius: 4.5px;
}}

/* ------------------------------------------------- misc */
#Toast {{
    background: {ELEV};
    color: {TEXT};
    border: 1px solid {GOLD};
    border-radius: 8px;
    padding: 9px 18px;
    font-size: 12px;
}}
#PageTitle {{ color: {TEXT}; font-size: 20px; font-weight: 700; }}
#PageSub {{ color: {FAINT}; font-size: 12px; }}
#CountLabel {{ color: {FAINT}; font-size: 12px; }}
#EmptyLabel {{ color: {FAINT}; font-size: 13px; background: transparent; }}
"""
