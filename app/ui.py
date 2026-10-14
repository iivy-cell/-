# -*- coding: utf-8 -*-
"""Main window & custom widgets — QQ-Music-style layout with Korean motifs."""
import json
import os

from PySide6.QtCore import (QEvent, QObject, QPropertyAnimation, QRect, QRectF,
                            QSize, Qt, QThread, QTimer, QUrl, Signal)
from PySide6.QtGui import (QColor, QCursor, QDesktopServices, QFont,
                           QFontMetrics, QPainter, QPainterPath, QPen,
                           QPixmap, QShortcut)
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QButtonGroup,
                               QGraphicsOpacityEffect, QHBoxLayout,
                               QHeaderView, QLabel, QLayout, QLineEdit,
                               QListWidget, QListWidgetItem, QMenu,
                               QPushButton, QScrollArea, QSizePolicy, QSlider,
                               QStackedWidget, QStyledItemDelegate,
                               QTableWidget, QTableWidgetItem, QVBoxLayout,
                               QWidget)

from . import art, theme
from .covers import CoverLoader
from .data import Catalog, Track, normalize
from .lyrics import LyricDoc, parse as parse_lyrics
from .paths import music_dir, user_data_dir, alive_index_path
from .player import Mode, Player


class SourceProbe(QThread):
    """Re-check every stored CDN link and rewrite data/alive.json.

    Signed URLs in database.json expire, so this must be re-runnable on demand
    rather than baked in at build time.
    """
    progress = Signal(str)
    finished_probe = Signal(int)

    def run(self) -> None:  # pragma: no cover - network dependent
        import concurrent.futures as cf
        import ssl
        import urllib.error
        import urllib.request

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 Chrome/126 Safari/537.36",
            "Referer": "https://www.bilibili.com/",
            "Origin": "https://www.bilibili.com",
            "Range": "bytes=0-2047",
            "Accept": "*/*",
        }
        tracks = self.parent().catalog.tracks
        items = [(t.id, t.download_url) for t in tracks if t.download_url]

        def check(url: str) -> bool:
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
                    return r.status in (200, 206)
            except Exception:
                return False

        alive_ids = []
        with cf.ThreadPoolExecutor(max_workers=24) as ex:
            for i, ok in enumerate(ex.map(check, [u for _, u in items])):
                if ok:
                    alive_ids.append(items[i][0])
                if i % 120 == 0:
                    self.progress.emit(f"检测中 {i}/{len(items)}…")

        path = alive_index_path()
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"probed_at": __import__("time").time(),
                           "alive_ids": alive_ids}, fh, ensure_ascii=False)
        except OSError:
            pass
        self.finished_probe.emit(len(alive_ids))


def fmt_ms(ms: int) -> str:
    s = int(ms // 1000)
    return f"{s // 60:02d}:{s % 60:02d}"


def fmt_s(sec: int) -> str:
    s = int(sec)
    return f"{s // 60:02d}:{s % 60:02d}"


_anims = set()


def _fade(effect: QGraphicsOpacityEffect, target: float, ms: int) -> None:
    anim = QPropertyAnimation(effect, b"opacity", effect)
    anim.setDuration(ms)
    anim.setEndValue(target)
    anim.finished.connect(lambda a=anim: _anims.discard(a))
    _anims.add(anim)
    anim.start()


# ===================================================================== Toast
class Toast(QLabel):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setObjectName("Toast")
        self.setWordWrap(True)
        self.setMaximumWidth(480)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hide()
        self._fx = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._fx)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fade_out)

    def show_message(self, text: str, ms: int = 3200) -> None:
        self.setText(text)
        self.adjustSize()
        pw = self.parentWidget().width() if self.parentWidget() else 600
        self.move((pw - self.width()) // 2, 76)
        self._fx.setOpacity(0.0)
        self.show()
        self.raise_()
        _fade(self._fx, 1.0, 160)
        self._timer.start(ms)

    def _fade_out(self) -> None:
        _fade(self._fx, 0.0, 420)
        QTimer.singleShot(460, self.hide)


# ============================================================= TrackTable
class IndexDelegate(QStyledItemDelegate):
    def __init__(self, table: "TrackTable"):
        super().__init__(table)
        self.table = table

    def paint(self, painter: QPainter, option, index) -> None:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        row = index.row()
        is_cur = row == self.table.current_row
        hovered = row == self.table.hover_row
        r = QRectF(option.rect)
        c = r.center()
        if is_cur and self.table.playing:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(theme.ACCENT))
            bar_w, gap = 3.0, 2.0
            heights = (8.0, 13.0, 6.0)
            x0 = c.x() - (bar_w * 3 + gap * 2) / 2
            for i, h in enumerate(heights):
                painter.drawRoundedRect(
                    QRectF(x0 + i * (bar_w + gap), c.y() - h / 2, bar_w, h), 1.5, 1.5)
        elif hovered:
            painter.setPen(QPen(QColor(theme.GOLD), 1.2))
            painter.setBrush(QColor(theme.SURFACE2))
            painter.drawEllipse(c, 11, 11)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(theme.TEXT))
            path = QPainterPath()
            path.moveTo(c.x() - 2.5, c.y() - 5)
            path.lineTo(c.x() + 5.5, c.y())
            path.lineTo(c.x() - 2.5, c.y() + 5)
            path.closeSubpath()
            painter.drawPath(path)
        else:
            f = QFont(option.font)
            f.setPointSize(10)
            painter.setFont(f)
            painter.setPen(QColor(theme.ACCENT) if is_cur else QColor(theme.FAINT))
            painter.drawText(r, Qt.AlignmentFlag.AlignCenter, str(row + 1))
        painter.restore()


class TrackTable(QTableWidget):
    playRequested = Signal(object)
    favoriteToggled = Signal(object)

    def __init__(self, parent: QWidget = None):
        super().__init__(0, 5, parent)
        self.setObjectName("SongTable")
        self.setHorizontalHeaderLabels(["", "歌曲", "歌手", "专辑", "时长"])
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(44)
        self.setShowGrid(False)
        self.setWordWrap(False)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setMouseTracking(True)
        hh = self.horizontalHeader()
        hh.setHighlightSections(False)
        hh.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for col, w in ((0, 54), (2, 180), (3, 210), (4, 68)):
            hh.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            self.setColumnWidth(col, w)
        self.hover_row = -1
        self.current_row = -1
        self.playing = False
        self._tracks: list = []
        self.setItemDelegateForColumn(0, IndexDelegate(self))
        self.cellDoubleClicked.connect(lambda r, c: self.playRequested.emit(self._tracks[r]))
        self.cellClicked.connect(self._on_click)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu)

    # ---------------------------------------------------------------- events
    def _on_click(self, row: int, col: int) -> None:
        if col == 0:
            self.playRequested.emit(self._tracks[row])

    def mouseMoveEvent(self, e) -> None:
        row = self.rowAt(e.position().toPoint().y())
        if row != self.hover_row:
            self.hover_row = row
            self.viewport().update()
        super().mouseMoveEvent(e)

    def leaveEvent(self, e) -> None:
        self.hover_row = -1
        self.viewport().update()
        super().leaveEvent(e)

    def _menu(self, pos) -> None:
        row = self.rowAt(pos)
        if row < 0 or row >= len(self._tracks):
            return
        track = self._tracks[row]
        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu{{background:{theme.SURFACE2};color:{theme.TEXT};"
            f"border:1px solid {theme.LINE};border-radius:8px;padding:6px;}}"
            f"QMenu::item{{padding:6px 22px;border-radius:6px;}}"
            f"QMenu::item:selected{{background:{theme.SELECT};}}")
        act_play = menu.addAction("播放")
        fav = track.id in self._fav_ids()
        act_fav = menu.addAction("取消收藏" if fav else "收藏")
        chosen = menu.exec(self.viewport().mapToGlobal(pos))
        if chosen is act_play:
            self.playRequested.emit(track)
        elif chosen is act_fav:
            self.favoriteToggled.emit(track)

    def _fav_ids(self) -> set:
        w = self.parent()
        while w is not None and not isinstance(w, MainWindow):
            w = w.parentWidget()
        return w.favorites if isinstance(w, MainWindow) else set()

    # ------------------------------------------------------------------ data
    def set_tracks(self, tracks) -> None:
        self._tracks = list(tracks)
        self.setRowCount(len(self._tracks))
        for i, t in enumerate(self._tracks):
            c0 = QTableWidgetItem()
            c0.setData(Qt.ItemDataRole.UserRole + 1, i)
            self.setItem(i, 0, c0)

            title = QTableWidgetItem(t.title_display)
            title.setForeground(QColor(theme.ACCENT if i == self.current_row else theme.TEXT))
            self.setItem(i, 1, title)

            singer = QTableWidgetItem(t.singer_display)
            singer.setForeground(QColor(theme.MUTED))
            self.setItem(i, 2, singer)

            album = QTableWidgetItem(t.album_display)
            album.setForeground(QColor(theme.MUTED))
            self.setItem(i, 3, album)

            dur = QTableWidgetItem(fmt_s(t.duration_s) if t.duration_s else (t.duration or ""))
            dur.setForeground(QColor(theme.FAINT))
            dur.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(i, 4, dur)
            for c in range(5):
                self.item(i, c).setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        self.set_current_row(-1, keep_color=True)

    def tracks(self):
        return list(self._tracks)

    def row_of(self, track: Track) -> int:
        try:
            return self._tracks.index(track)
        except ValueError:
            return -1

    def set_current_row(self, row: int, keep_color: bool = False) -> None:
        old = self.current_row
        self.current_row = row
        if not keep_color:
            for r in {old, row}:
                if 0 <= r < len(self._tracks):
                    it = self.item(r, 1)
                    if it:
                        it.setForeground(QColor(theme.ACCENT if r == row else theme.TEXT))
        self.viewport().update()


# =========================================================== RotatingCover
class RotatingCover(QWidget):
    def __init__(self, parent=None, diameter: int = 200):
        super().__init__(parent)
        self._d = diameter
        self.setFixedSize(diameter + 30, diameter + 30)
        self._pm: QPixmap = QPixmap()
        self._angle = 0.0
        self._playing = False
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._tick)

    def _tick(self) -> None:
        self._angle = (self._angle + 0.7) % 360.0
        self.update()

    def set_playing(self, on: bool) -> None:
        if on != self._playing:
            self._playing = on
            self._timer.start() if on else self._timer.stop()

    def set_pixmap(self, pm: QPixmap) -> None:
        self._pm = pm
        self.update()

    def paintEvent(self, e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        w = self.width()
        c = w / 2.0
        d = float(self._d)
        outer = d / 2 + 9

        # rotating dashed ring (fan-rib inspired)
        pen = QPen(QColor(theme.GOLD))
        pen.setWidthF(1.3)
        pen.setDashPattern([2.0, 3.6])
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.save()
        p.translate(c, c)
        p.rotate(self._angle)
        p.drawArc(QRectF(-outer, -outer, outer * 2, outer * 2), 0, 360 * 16)
        p.restore()

        # spinning disc
        p.save()
        p.translate(c, c)
        p.rotate(self._angle)
        path = QPainterPath()
        path.addEllipse(QRectF(-d / 2, -d / 2, d, d))
        p.setClipPath(path)
        pm = self._pm if not self._pm.isNull() else art.default_cover(int(d), "朝鲜族")
        p.drawPixmap(QRectF(-d / 2, -d / 2, d, d).toRect(), pm)
        p.setClipping(False)
        p.setPen(QPen(QColor(0, 0, 0, 70), 1.0))
        for rr in (0.34, 0.46):
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QRectF(-d / 2 * rr, -d / 2 * rr, d * rr, d * rr))
        p.restore()

        # rim
        _gold = QColor(theme.GOLD)
        _gold.setAlpha(110)
        p.setPen(QPen(_gold, 1.1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(c - d / 2 - 1, c - d / 2 - 1, d + 2, d + 2))
        # centre hole
        hole = d * 0.085
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(theme.BG2))
        p.drawEllipse(QRectF(c - hole, c - hole, hole * 2, hole * 2))
        p.setPen(QPen(QColor(theme.LINE), 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(c - hole, c - hole, hole * 2, hole * 2))
        p.end()


# ============================================================== LyricsView
class LyricsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._doc = LyricDoc([])
        self._cur = -1
        self._scroll = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._ease)
        self._line_h = 32

    def set_doc(self, doc: LyricDoc) -> None:
        self._doc = doc or LyricDoc([])
        self._cur = -1
        self._scroll = 0.0
        self._timer.stop()
        self.update()

    def set_position(self, seconds: float) -> None:
        if not self._doc.timed:
            return
        idx = self._doc.index_at(seconds)
        if idx != self._cur:
            self._cur = idx
            self._timer.start()
            self.update()

    def _ease(self) -> None:
        target = float(max(0, self._cur))
        d = target - self._scroll
        if abs(d) < 0.02:
            self._scroll = target
            self._timer.stop()
            self.update()
            return
        self._scroll += d * 0.13
        self.update()

    def paintEvent(self, e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        w, h = self.width(), self.height()
        if not self._doc.has_text:
            f = QFont("Microsoft YaHei", 12)
            p.setFont(f)
            p.setPen(QColor(theme.FAINT))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       "♪  纯音乐 · 请欣赏  ♪")
            p.end()
            return
        if not self._doc.timed:
            lines = [l.text for l in self._doc.lines if l.text]
            f = QFont("Microsoft YaHei", 12)
            p.setFont(f)
            p.setPen(QColor(theme.MUTED))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                       "\n".join(lines[:60]))
            p.end()
            return
        lh = self._line_h
        base = h / 2.0
        first = max(0, int(self._scroll) - h // lh // 2 - 1)
        last = min(len(self._doc.lines), first + h // lh + 4)
        for i in range(first, last):
            text = self._doc.lines[i].text
            if not text:
                continue
            y = base + (i - self._scroll) * lh - lh / 2.0
            if y < -lh or y > h + lh:
                continue
            if i == self._cur:
                f = QFont("Microsoft YaHei", 14)
                f.setBold(True)
                col = QColor(theme.GOLD)
            else:
                f = QFont("Microsoft YaHei", 12)
                col = QColor(theme.MUTED)
                col.setAlpha(max(56, int(220 - abs(i - self._scroll) * 34)))
            p.setFont(f)
            p.setPen(col)
            p.drawText(QRectF(14, y, w - 28, lh),
                       Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                       text)
        p.end()


# ============================================================== FlowLayout
class FlowLayout(QLayout):
    """Standard wrapping layout for keyword chips."""

    def __init__(self, parent=None, spacing: int = 8):
        super().__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)
        self._spacing = spacing
        self._items: list = []

    def addItem(self, item) -> None:  # noqa: N802
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, i):
        return self._items[i] if 0 <= i < len(self._items) else None

    def takeAt(self, i):
        return self._items.pop(i) if 0 <= i < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientations(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, w: int) -> int:
        return self._do_layout(QRect(0, 0, w, 0), True)

    def setGeometry(self, rect) -> None:
        try:
            super().setGeometry(rect)
        except NotImplementedError:
            # C++ may invoke this before the Python subclass is fully bound
            pass
        self._do_layout(rect, False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        s = QSize()
        for it in self._items:
            s = s.expandedTo(it.minimumSize())
        m = self.contentsMargins()
        s += QSize(m.left() + m.right(), m.top() + m.bottom())
        return s

    def _do_layout(self, rect: "QRect", test_only: bool) -> int:
        m = self.contentsMargins()
        x, y = rect.x() + m.left(), rect.y() + m.top()
        line_h = 0
        right = rect.right() - m.right()
        for it in self._items:
            w = it.sizeHint().width()
            h = it.sizeHint().height()
            nx = x + w + self._spacing
            if nx - self._spacing > right and line_h > 0:
                x = rect.x() + m.left()
                y = y + line_h + self._spacing
                nx = x + w + self._spacing
                line_h = 0
            if not test_only:
                it.setGeometry(QRect(x, y, w, h))
            x = nx
            line_h = max(line_h, h)
        return y + line_h + m.bottom() - rect.y()


# =============================================================== TitleBar
class TitleBar(QWidget):
    searchChanged = Signal(str)
    minimizeClicked = Signal()
    maximizeClicked = Signal()
    closeClicked = Signal()

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setObjectName("TitleBar")
        self.setFixedHeight(56)
        self._maximized = False

        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 2, 0)
        lay.setSpacing(10)

        logo = QLabel()
        logo.setPixmap(art.taegeuk(30, bg=art.CREAM))
        logo.setFixedSize(30, 30)
        logo.setScaledContents(True)
        lay.addWidget(logo)

        brand = QVBoxLayout()
        brand.setSpacing(0)
        name = QLabel("朝鲜族音乐")
        name.setObjectName("BrandName")
        sub = QLabel("CHAOXIANZU  ·  ETHNIC MUSIC")
        sub.setObjectName("BrandSub")
        brand.addWidget(name)
        brand.addWidget(sub)
        lay.addLayout(brand)

        lay.addStretch(1)

        self.search = QLineEdit()
        self.search.setObjectName("SearchEdit")
        self.search.setPlaceholderText("搜索歌曲 / 歌手 / 专辑")
        self.search.setFixedSize(300, 32)
        self.search.addAction(art.icon("search", color=theme.MUTED, size=15),
                              QLineEdit.ActionPosition.LeadingPosition)
        self.search.setClearButtonEnabled(True)
        lay.addWidget(self.search)

        lay.addStretch(1)

        self.btn_min = self._win_btn("minimize", "minimize")
        self.btn_max = self._win_btn("maximize", "maximize")
        self.btn_close = self._win_btn("close", "close")
        self.btn_min.clicked.connect(self.minimizeClicked)
        self.btn_max.clicked.connect(self.maximizeClicked)
        self.btn_close.clicked.connect(self.closeClicked)
        lay.addWidget(self.btn_min)
        lay.addWidget(self.btn_max)
        lay.addWidget(self.btn_close)

        self.search.textChanged.connect(self.searchChanged)

    def _win_btn(self, icon: str, kind: str) -> QPushButton:
        b = QPushButton()
        b.setObjectName("WinBtn")
        b.setProperty("kind", kind)
        b.setIcon(art.icon(icon, color=theme.MUTED, size=15, width=1.4))
        b.setIconSize(QSize(15, 15))
        b.setFixedSize(44, 34)
        b.setToolTip({"minimize": "最小化", "maximize": "最大化", "close": "关闭"}[kind])
        return b

    def set_maximized(self, on: bool) -> None:
        self._maximized = on
        self.btn_max.setIcon(art.icon("restore" if on else "maximize",
                                      color=theme.MUTED, size=14, width=1.4))

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            child = self.childAt(e.position().toPoint())
            if not isinstance(child, (QLineEdit, QPushButton)) and child is not None:
                pass
            if not isinstance(child, (QLineEdit, QPushButton)):
                self.window().windowHandle().startSystemMove()
                return
        super().mousePressEvent(e)

    def mouseDoubleClickEvent(self, e) -> None:
        self.maximizeClicked.emit()


# ================================================================ Sidebar
class Sidebar(QWidget):
    navChanged = Signal(int)
    keywordSelected = Signal(str)
    scanRequested = Signal()
    openDirRequested = Signal()

    def __init__(self, keywords, parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(226)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 10, 0, 12)
        root.setSpacing(4)

        self.nav = QListWidget()
        self.nav.setObjectName("NavList")
        for icon_name, text in (("music", "全部歌曲"),
                                ("play", "在线可播"),
                                ("singer", "歌手"),
                                ("album", "专辑"), ("heart_fill", "我的收藏"),
                                ("list", "最近播放")):
            item = QListWidgetItem(art.icon(icon_name, color=theme.GOLD, size=16), text)
            self.nav.addItem(item)
        self.nav.item(1).setToolTip("仅显示在线链接当前仍可用的曲目")
        self.nav.setCurrentRow(0)
        # pin height so adding a nav row never squeezes the list into a scrollbox
        self.nav.setFixedHeight(self.nav.count() * 44 + 8)
        self.nav.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.nav.currentRowChanged.connect(self.navChanged)
        root.addWidget(self.nav)

        title = QLabel("民 乐 关 键 词")
        title.setObjectName("SideTitle")
        root.addWidget(title)

        holder = QWidget()
        flow = FlowLayout(holder)
        self.chip_group = QButtonGroup(self)
        self.chip_group.setExclusive(True)
        first = self._chip("全部", flow)
        first.setChecked(True)
        for kw in keywords[:10]:
            self._chip(kw, flow)
        root.addWidget(holder)
        root.addStretch(1)

        scan = QPushButton(art.icon("refresh", color=theme.MUTED, size=14), "扫描本地音乐")
        scan.setObjectName("GhostBtn")
        scan.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        scan.clicked.connect(self.scanRequested)
        root.addWidget(scan, 0, Qt.AlignmentFlag.AlignHCenter)

        tip = QLabel("把音频放入 music 文件夹")
        tip.setObjectName("EmptyLabel")
        tip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(tip)

        self.chip_group.buttonClicked.connect(
            lambda b: self.keywordSelected.emit(b.text() if b.text() != "全部" else ""))

    def _chip(self, text: str, flow: FlowLayout) -> QPushButton:
        b = QPushButton(text)
        b.setObjectName("Chip")
        b.setCheckable(True)
        b.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        flow.addWidget(b)
        self.chip_group.addButton(b)
        return b


# ============================================================= HeroHeader
class HeroHeader(QWidget):
    playAllRequested = Signal()
    scanRequested = Signal()
    openDirRequested = Signal()

    def __init__(self, catalog: Catalog, loader: CoverLoader, parent=None):
        super().__init__(parent)
        self.setObjectName("HeroCard")
        self._loader = loader
        self._url = catalog.cover_url

        lay = QHBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 8)
        lay.setSpacing(20)

        self.cover = QLabel()
        self.cover.setFixedSize(148, 148)
        self.cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.cover)

        right = QVBoxLayout()
        right.setSpacing(8)
        top = QHBoxLayout()
        self.title = QLabel(catalog.name)
        self.title.setObjectName("HeroTitle")
        top.addWidget(self.title)
        badge = QLabel("民族音乐")
        badge.setObjectName("HeroBadge")
        top.addWidget(badge)
        top.addStretch(1)
        right.addLayout(top)

        hours = catalog.total_duration_s() / 3600.0
        self.meta = QLabel(
            f"{len(catalog.tracks)} 首 · {catalog.singer_count} 位歌手 · "
            f"{catalog.album_count} 张专辑 · 总时长约 {hours:.1f} 小时")
        self.meta.setObjectName("HeroMeta")
        right.addWidget(self.meta)

        kws = "  ·  ".join(catalog.keywords) if catalog.keywords else ""
        fm = QFontMetrics(self.font())
        self.desc = QLabel(fm.elidedText(f"关键词：{kws}", Qt.TextElideMode.ElideRight, 560))
        self.desc.setObjectName("HeroDesc")
        right.addWidget(self.desc)

        btns = QHBoxLayout()
        btns.setSpacing(12)
        play = QPushButton("  播放全部")
        play.setObjectName("PrimaryBtn")
        play.setIcon(art.icon("play", color="#FFF7EC", size=14))
        play.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        play.clicked.connect(self.playAllRequested)
        btns.addWidget(play)

        scan = QPushButton("  扫描本地音乐")
        scan.setObjectName("GhostBtn")
        scan.setIcon(art.icon("refresh", color=theme.MUTED, size=14))
        scan.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        scan.clicked.connect(self.scanRequested)
        btns.addWidget(scan)

        folder = QPushButton("  打开 music 文件夹")
        folder.setObjectName("GhostBtn")
        folder.setIcon(art.icon("folder", color=theme.MUTED, size=14))
        folder.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        folder.clicked.connect(self.openDirRequested)
        btns.addWidget(folder)
        btns.addStretch(1)
        right.addLayout(btns)
        right.addStretch(1)
        lay.addLayout(right, 1)

        self.set_cover(self._load_cover())

    def _load_cover(self) -> QPixmap:
        pm = self._loader.get(self._url)
        if pm is None:
            pm = art.default_cover(148, "朝鲜族", seed=self._url or "hero")
        return art.rounded(pm.scaled(148, 148,
                                     Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation), 10)

    def on_cover_loaded(self, url: str) -> None:
        if url == self._url:
            self.set_cover(self._load_cover())

    def set_cover(self, pm: QPixmap) -> None:
        self.cover.setPixmap(pm)


# =============================================================== NowPanel
class NowPanel(QWidget):
    closeRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("NowPanel")
        self.setFixedWidth(324)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 12, 18, 14)
        root.setSpacing(6)

        head = QHBoxLayout()
        label = QLabel("正 在 播 放")
        label.setObjectName("SideTitle")
        head.addWidget(label)
        head.addStretch(1)
        close = QPushButton()
        close.setObjectName("RoundBtn")
        close.setIcon(art.icon("chevron_right", color=theme.MUTED, size=16))
        close.setFixedSize(28, 28)
        close.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close.clicked.connect(self.closeRequested)
        head.addWidget(close)
        root.addLayout(head)

        self.cover = RotatingCover(diameter=196)
        root.addWidget(self.cover, 0, Qt.AlignmentFlag.AlignHCenter)

        self.title = QLabel("朝鲜族音乐")
        self.title.setObjectName("NowTitle")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title.setWordWrap(True)
        self.artist = QLabel("选择一首歌曲开始聆听")
        self.artist.setObjectName("NowArtist")
        self.artist.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.title)
        root.addWidget(self.artist)

        self.hint = QLabel(
            "未找到可播放音源。\n\n将 mp3 / flac 等音频文件放入程序旁的 music 文件夹，"
            "文件名包含歌曲名即可自动匹配，然后点击「扫描本地音乐」。")
        self.hint.setObjectName("NowHint")
        self.hint.setWordWrap(True)
        self.hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint.hide()
        root.addWidget(self.hint)

        self.lyrics = LyricsView()
        root.addWidget(self.lyrics, 1)

    def set_track(self, track: Track, cover: QPixmap) -> None:
        self.title.setText(track.title_display)
        self.artist.setText(f"{track.singer_display}  ·  {track.album_display}")
        self.cover.set_pixmap(cover)
        self.set_lyrics(track.lyric)
        self.set_hint(None)

    def set_idle(self) -> None:
        self.title.setText("朝鲜族音乐")
        self.artist.setText("选择一首歌曲开始聆听")
        self.cover.set_pixmap(QPixmap())
        self.set_lyrics("")
        self.set_hint(None)

    def set_lyrics(self, text: str) -> None:
        self.lyrics.set_doc(parse_lyrics(text))

    def set_position_ms(self, ms: int) -> None:
        self.lyrics.set_position(ms / 1000.0)

    def set_playing(self, on: bool) -> None:
        self.cover.set_playing(on)

    def set_hint(self, text: str = None) -> None:
        """Show the default guidance when called with no argument."""
        if text is None:
            self.hint.setText(
                "该曲目的音源已失效。\n\n曲库中 66 首咪咕源歌曲可直接在线播放；"
                "其余曲目可将音频文件（mp3 / flac 等）放入程序旁的 music 文件夹，"
                "文件名包含歌曲名即可自动匹配，然后点击「扫描本地音乐」。")
            self.hint.show()
        elif text:
            self.hint.setText(text)
            self.hint.show()
        else:
            self.hint.hide()


# ============================================================ TransportBar
class TransportBar(QWidget):
    seekDragged = Signal(int)
    prevClicked = Signal()
    nextClicked = Signal()
    toggleClicked = Signal()
    modeClicked = Signal()
    volumeChanged = Signal(float)
    favClicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TransportBar")
        self.setFixedHeight(92)
        self._dragging = False
        self._fav = False

        root = QHBoxLayout(self)
        root.setContentsMargins(18, 8, 18, 10)
        root.setSpacing(14)

        # -- left: track info
        left = QHBoxLayout()
        left.setSpacing(12)
        self.thumb = QLabel()
        self.thumb.setFixedSize(46, 46)
        self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left.addWidget(self.thumb)
        info = QVBoxLayout()
        info.setSpacing(2)
        self.title = QLabel("未在播放")
        self.title.setObjectName("TrackTitle")
        self.artist = QLabel("朝鲜族 · 民族音乐")
        self.artist.setObjectName("TrackArtist")
        info.addWidget(self.title)
        info.addWidget(self.artist)
        left.addLayout(info)
        self.fav_btn = QPushButton()
        self.fav_btn.setObjectName("RoundBtn")
        self.fav_btn.setIcon(art.icon("heart", color=theme.MUTED, size=16))
        self.fav_btn.setFixedSize(30, 30)
        self.fav_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.fav_btn.setToolTip("收藏")
        self.fav_btn.clicked.connect(self.favClicked)
        left.addWidget(self.fav_btn)
        root.addLayout(left, 0)

        # -- centre: progress + controls
        centre = QVBoxLayout()
        centre.setSpacing(4)
        seek_row = QHBoxLayout()
        self.t_cur = QLabel("00:00")
        self.t_cur.setObjectName("TimeLabel")
        self.t_cur.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.t_cur.setFixedWidth(44)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setObjectName("SeekSlider")
        self.slider.setRange(0, 0)
        self.slider.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.t_tot = QLabel("00:00")
        self.t_tot.setObjectName("TimeLabel")
        self.t_tot.setFixedWidth(44)
        seek_row.addWidget(self.t_cur)
        seek_row.addWidget(self.slider, 1)
        seek_row.addWidget(self.t_tot)
        centre.addLayout(seek_row)

        ctrl = QHBoxLayout()
        ctrl.addStretch(1)
        self.mode_btn = QPushButton()
        self.mode_btn.setObjectName("RoundBtn")
        self.mode_btn.setFixedSize(32, 32)
        self.mode_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.mode_btn.clicked.connect(self.modeClicked)
        ctrl.addWidget(self.mode_btn)

        self.prev_btn = QPushButton()
        self.prev_btn.setObjectName("RoundBtn")
        self.prev_btn.setIcon(art.icon("prev", color=theme.TEXT, size=17, width=1.4))
        self.prev_btn.setIconSize(QSize(17, 17))
        self.prev_btn.setFixedSize(32, 32)
        self.prev_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.prev_btn.clicked.connect(self.prevClicked)
        ctrl.addWidget(self.prev_btn)
        ctrl.addSpacing(6)

        self.play_btn = QPushButton()
        self.play_btn.setObjectName("BigPlay")
        self.play_btn.setIcon(art.icon("play", color="#FFF7EC", size=20))
        self.play_btn.setIconSize(QSize(20, 20))
        self.play_btn.setFixedSize(46, 46)
        self.play_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.play_btn.clicked.connect(self.toggleClicked)
        ctrl.addWidget(self.play_btn)
        ctrl.addSpacing(6)

        self.next_btn = QPushButton()
        self.next_btn.setObjectName("RoundBtn")
        self.next_btn.setIcon(art.icon("next", color=theme.TEXT, size=17, width=1.4))
        self.next_btn.setIconSize(QSize(17, 17))
        self.next_btn.setFixedSize(32, 32)
        self.next_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.next_btn.clicked.connect(self.nextClicked)
        ctrl.addWidget(self.next_btn)
        ctrl.addStretch(1)
        centre.addLayout(ctrl)
        root.addLayout(centre, 1)

        # -- right: volume
        right = QHBoxLayout()
        right.setSpacing(8)
        self.vol_btn = QPushButton()
        self.vol_btn.setObjectName("RoundBtn")
        self.vol_btn.setIcon(art.icon("volume", color=theme.MUTED, size=16))
        self.vol_btn.setFixedSize(30, 30)
        self.vol_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.vol_btn.clicked.connect(self._mute_toggle)
        right.addWidget(self.vol_btn)
        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setObjectName("VolumeSlider")
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(85)
        self.vol_slider.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.vol_slider.valueChanged.connect(
            lambda v: self.volumeChanged.emit(v / 100.0))
        right.addWidget(self.vol_slider)
        root.addLayout(right, 0)

        self.slider.sliderPressed.connect(lambda: setattr(self, "_dragging", True))
        self.slider.sliderReleased.connect(self._slider_released)
        self.slider.sliderMoved.connect(self.seekDragged)
        self.slider.sliderMoved.connect(lambda v: self.t_cur.setText(fmt_ms(v)))
        self._muted = False
        self.set_mode(Mode.LOOP_ALL)

    # ------------------------------------------------------------------ api
    def _slider_released(self) -> None:
        self._dragging = False
        self.seekDragged.emit(self.slider.value())

    def set_duration(self, ms: int) -> None:
        if not self._dragging:
            self.slider.setRange(0, int(ms))
            self.t_tot.setText(fmt_ms(ms))

    def set_position(self, ms: int) -> None:
        if not self._dragging:
            self.slider.setValue(int(ms))
            self.t_cur.setText(fmt_ms(ms))

    def set_track_info(self, title: str, artist: str, pm: QPixmap) -> None:
        self.title.setText(title)
        self.artist.setText(artist)
        if pm.isNull():
            pm = art.default_cover(46, title[:1] or "民")
        self.thumb.setPixmap(art.rounded(
            pm.scaled(46, 46, Qt.AspectRatioMode.KeepAspectRatio,
                      Qt.TransformationMode.SmoothTransformation), 7))

    def set_playing(self, on: bool) -> None:
        self.play_btn.setIcon(art.icon("pause" if on else "play",
                                       color="#FFF7EC", size=20))

    def set_mode(self, mode: Mode) -> None:
        icons = {Mode.ORDER: "list", Mode.LOOP_ALL: "loop",
                 Mode.LOOP_ONE: "loop_one", Mode.SHUFFLE: "shuffle"}
        tips = {Mode.ORDER: "顺序播放", Mode.LOOP_ALL: "列表循环",
                Mode.LOOP_ONE: "单曲循环", Mode.SHUFFLE: "随机播放"}
        self.mode_btn.setIcon(art.icon(icons[mode], color=theme.MUTED, size=16))
        self.mode_btn.setToolTip(tips[mode])

    def set_fav(self, on: bool) -> None:
        self._fav = on
        self.fav_btn.setIcon(art.icon("heart_fill" if on else "heart",
                                      color=theme.ACCENT if on else theme.MUTED, size=16))

    def _mute_toggle(self) -> None:
        self._muted = not self._muted
        if self._muted:
            self.vol_btn.setIcon(art.icon("volume_off", color=theme.MUTED, size=16))
            self.volumeChanged.emit(0.0)
        else:
            self.vol_btn.setIcon(art.icon("volume", color=theme.MUTED, size=16))
            self.volumeChanged.emit(self.vol_slider.value() / 100.0)


# ============================================================== MainWindow
class MainWindow(QWidget):
    _LIB_FILE = "library.json"

    def __init__(self):
        super().__init__()
        self.setObjectName("RootWindow")
        self.setWindowTitle("朝鲜族音乐")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setMinimumSize(QSize(1060, 660))
        self.resize(1240, 800)

        try:
            self.catalog = Catalog()
        except Exception as exc:  # database missing/corrupt
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(None, "朝鲜族音乐", f"曲库加载失败：{exc}")
            raise

        self.loader = CoverLoader(self)
        self.favorites: set = set()
        self.recent: list = []
        self._keyword = ""
        self._search_text = ""
        self._search_debounce = QTimer(self)
        self._search_debounce.setSingleShot(True)
        self._search_debounce.setInterval(220)
        self._search_debounce.timeout.connect(self._apply_search)
        self._load_library()

        self.player = Player(self)
        self._build_ui()
        self._wire()
        self._install_shortcuts()
        self.scan_local(silent=True)
        self.sidebar.nav.setCurrentRow(0)
        self.now_panel.set_idle()

    # ------------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.title_bar = TitleBar(self)
        outer.addWidget(self.title_bar)

        body_row = QHBoxLayout()
        body_row.setContentsMargins(0, 0, 0, 0)
        body_row.setSpacing(0)

        self.sidebar = Sidebar(self.catalog.keywords)
        body_row.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._make_songs_page())       # 0
        self.stack.addWidget(self._make_online_page())# 1 在线可播
        self.stack.addWidget(self._make_list_page("singer"))  # 2
        self.stack.addWidget(self._make_list_page("album"))   # 3
        self.stack.addWidget(self._make_lib_page("我的收藏"))   # 4
        self.stack.addWidget(self._make_lib_page("最近播放"))   # 5
        self.stack.addWidget(self._make_detail_page())        # 6
        body_row.addWidget(self.stack, 1)

        self.now_panel = NowPanel()
        body_row.addWidget(self.now_panel)
        outer.addLayout(body_row, 1)

        self.bar = TransportBar()
        outer.addWidget(self.bar)

        self.toast = Toast(self)

    def _make_songs_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.hero = HeroHeader(self.catalog, self.loader)
        lay.addWidget(self.hero)

        strip = QHBoxLayout()
        strip.setContentsMargins(26, 2, 26, 6)
        self.count_label = QLabel()
        self.count_label.setObjectName("CountLabel")
        strip.addWidget(self.count_label)
        strip.addStretch(1)
        lay.addLayout(strip)

        self.songs_table = TrackTable()
        lay.addWidget(self.songs_table, 1)
        return page

    def _make_list_page(self, kind: str) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(26, 18, 26, 16)
        lay.setSpacing(8)
        title = QLabel("歌手" if kind == "singer" else "专辑")
        title.setObjectName("PageTitle")
        lay.addWidget(title)
        sub = QLabel("双击查看曲目" )
        sub.setObjectName("PageSub")
        lay.addWidget(sub)
        lst = QListWidget()
        lst.setObjectName("SimpleList")
        lst.setMouseTracking(True)
        if kind == "album":
            lst.setIconSize(QSize(40, 40))
        lay.addWidget(lst, 1)
        if kind == "singer":
            self.singer_list = lst
        else:
            self.album_list = lst
        lst.itemDoubleClicked.connect(
            lambda item, k=kind: self._open_detail(k, item.data(Qt.ItemDataRole.UserRole)))
        return page

    def _make_lib_page(self, title: str) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(26, 18, 26, 16)
        lay.setSpacing(8)
        head = QHBoxLayout()
        t = QLabel(title)
        t.setObjectName("PageTitle")
        head.addWidget(t)
        head.addStretch(1)
        lay.addLayout(head)
        table = TrackTable()
        lay.addWidget(table, 1)
        empty = QLabel("暂无内容")
        empty.setObjectName("EmptyLabel")
        empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(empty)
        empty.hide()
        if title == "我的收藏":
            self.fav_table, self.fav_empty = table, empty
        else:
            self.recent_table, self.recent_empty = table, empty
        return page

    def _make_online_page(self) -> QWidget:
        """Fast lane: only tracks whose CDN link verified alive."""
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(26, 14, 26, 16)
        lay.setSpacing(8)
        head = QHBoxLayout()
        t = QLabel("在线可播")
        t.setObjectName("PageTitle")
        head.addWidget(t)
        self.online_count_label = QLabel()
        self.online_count_label.setObjectName("CountLabel")
        head.addWidget(self.online_count_label)
        head.addStretch(1)
        recheck = QPushButton("  重新检测音源")
        recheck.setObjectName("GhostBtn")
        recheck.setIcon(art.icon("refresh", color=theme.MUTED, size=15))
        recheck.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        recheck.setToolTip("重新联网检查所有音源链接，可用数量会立即更新")
        recheck.clicked.connect(self._recheck_sources)
        head.addWidget(recheck)
        lay.addLayout(head)

        hint = QLabel("曲库里的在线链接多为带时效的临时地址，过期后会失效。"
                      "这里只列出当前仍可播放的曲目；其余曲目可把音频文件放进 music 文件夹自动匹配。")
        hint.setObjectName("EmptyLabel")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        self.online_table = TrackTable()
        lay.addWidget(self.online_table, 1)
        self.online_empty = QLabel("当前没有在线可用音源，请把本地音频放入 music 文件夹")
        self.online_empty.setObjectName("EmptyLabel")
        self.online_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.online_empty)
        self.online_empty.hide()
        return page

    def _fill_online(self) -> None:
        tracks = self.catalog.online_tracks()
        self.online_table.set_tracks(tracks)
        self.online_count_label.setText(f"{len(tracks)} 首可播")
        self.online_empty.setVisible(not tracks)
        self.online_table.setVisible(bool(tracks))

    def _recheck_sources(self) -> None:
        self._toast("正在重新检测音源，请稍候…", 12000)
        worker = SourceProbe(self)
        worker.progress.connect(self._toast)
        worker.finished_probe.connect(self._on_probe_done)
        worker.finished.connect(worker.deleteLater)
        self._probe_worker = worker
        worker.start()

    def _on_probe_done(self, count: int) -> None:
        self.catalog.load_alive_index()
        self._fill_online()
        self._toast(f"检测完成：{count} 首在线可播")

    def _make_detail_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(26, 14, 26, 16)
        lay.setSpacing(8)
        head = QHBoxLayout()
        back = QPushButton("  返回")
        back.setObjectName("GhostBtn")
        back.setIcon(art.icon("chevron_left", color=theme.MUTED, size=15))
        back.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        back.clicked.connect(lambda: self.stack.setCurrentIndex(self._prev_page))
        head.addWidget(back)
        self.detail_title = QLabel("")
        self.detail_title.setObjectName("PageTitle")
        head.addSpacing(10)
        head.addWidget(self.detail_title)
        head.addStretch(1)
        lay.addLayout(head)
        self.detail_table = TrackTable()
        lay.addWidget(self.detail_table, 1)
        return page

    # -------------------------------------------------------------- wiring
    def _wire(self) -> None:
        self.title_bar.searchChanged.connect(self._on_search_changed)
        self.title_bar.minimizeClicked.connect(self.showMinimized)
        self.title_bar.maximizeClicked.connect(self._toggle_max)
        self.title_bar.closeClicked.connect(self.close)

        self.sidebar.navChanged.connect(self._on_nav)
        self.sidebar.keywordSelected.connect(self._on_keyword)
        self.sidebar.scanRequested.connect(lambda: self.scan_local(False))

        self.hero.playAllRequested.connect(self._play_all)
        self.hero.scanRequested.connect(lambda: self.scan_local(False))
        self.hero.openDirRequested.connect(self._open_music_dir)
        self.loader.loaded.connect(self.hero.on_cover_loaded)

        for table in self._all_tables():
            table.playRequested.connect(self._play)
            table.favoriteToggled.connect(self._toggle_fav)

        self.bar.seekDragged.connect(self.player.seek)
        self.bar.prevClicked.connect(self.player.prev)
        self.bar.nextClicked.connect(lambda: self.player.next(auto=False))
        self.bar.toggleClicked.connect(self.player.toggle)
        self.bar.modeClicked.connect(self._cycle_mode)
        self.bar.volumeChanged.connect(self.player.set_volume)
        self.bar.favClicked.connect(self._fav_current)

        self.player.positionChanged.connect(self._on_position)
        self.player.durationChanged.connect(self.bar.set_duration)
        self.player.playingChanged.connect(self._on_playing)
        self.player.trackChanged.connect(self._on_track_changed)
        self.player.sourceMissing.connect(self._on_source_missing)
        self.player.playbackError.connect(self._on_playback_error)

        self.now_panel.closeRequested.connect(self._toggle_now_panel)

    def _all_tables(self):
        return (self.songs_table, self.detail_table,
                self.fav_table, self.recent_table, self.online_table)

    def _install_shortcuts(self) -> None:
        sc_space = QShortcut(Qt.Key.Key_Space, self)
        sc_space.activated.connect(self.player.toggle)
        sc_right = QShortcut(Qt.Key.Key_Right, self)
        sc_right.activated.connect(
            lambda: self.player.seek(self.player.media.position() + 5000))
        sc_left = QShortcut(Qt.Key.Key_Left, self)
        sc_left.activated.connect(
            lambda: self.player.seek(max(0, self.player.media.position() - 5000)))

    # ------------------------------------------------------------ navigation
    _prev_page = 0

    def _on_nav(self, row: int) -> None:
        if row < 0:
            return
        if self.stack.currentIndex() != 6:
            self._prev_page = self.stack.currentIndex()
        self.stack.setCurrentIndex(row)
        if row == 1:
            self._fill_online()
        elif row == 2:
            self._fill_singers()
        elif row == 3:
            self._fill_albums()
        elif row == 4:
            self._fill_fav()
        elif row == 5:
            self._fill_recent()

    def _open_detail(self, kind: str, key: str) -> None:
        if self.stack.currentIndex() != 6:
            self._prev_page = self.stack.currentIndex()
        if kind == "singer":
            self.detail_title.setText(f"歌手 · {key}")
            tracks = self.catalog.tracks_of_singer(key)
        else:
            self.detail_title.setText(f"专辑 · {key}")
            tracks = self.catalog.tracks_of_album(key)
        self.detail_table.set_tracks(tracks)
        self._sync_highlight()
        self.stack.setCurrentIndex(5)

    # ------------------------------------------------------------- filtering
    def visible_tracks(self):
        tracks = (self.catalog.search(self._search_text)
                  if self._search_text else self.catalog.tracks)
        if self._keyword:
            kw = normalize(self._keyword)
            tracks = [t for t in tracks if kw in t.search_blob()]
        return tracks

    def _refresh_songs(self) -> None:
        tracks = self.visible_tracks()
        self.songs_table.set_tracks(tracks)
        self._sync_highlight()
        local = sum(1 for t in tracks if t.has_audio)
        online = sum(1 for t in tracks if "migu.cn" in (t.download_url or ""))
        self.count_label.setText(
            f"共 {len(tracks)} 首 · 在线可播 {online} 首 · 已匹配本地音源 {local} 首"
            f"{'  ·  关键词「%s」' % self._keyword if self._keyword else ''}"
            f"{'  ·  搜索「%s」' % self._search_text if self._search_text else ''}")

    def _on_search_changed(self, text: str) -> None:
        self._search_text = text.strip()
        self._search_debounce.start()

    def _apply_search(self) -> None:
        self.stack.setCurrentIndex(0)
        self._refresh_songs()

    def _on_keyword(self, kw: str) -> None:
        self._keyword = kw
        self.stack.setCurrentIndex(0)
        self._refresh_songs()

    # ---------------------------------------------------------------- lists
    def _fill_singers(self) -> None:
        self.singer_list.clear()
        for name in self.catalog.singers():
            tracks = self.catalog.tracks_of_singer(name)
            item = QListWidgetItem(f"{name}    ·    {len(tracks)} 首")
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.singer_list.addItem(item)

    def _fill_albums(self) -> None:
        self.album_list.clear()
        for name in self.catalog.albums():
            tracks = self.catalog.tracks_of_album(name)
            pm = art.default_cover(40, name[:1] or "专", seed=name)
            item = QListWidgetItem(pm, f"{name}    ·    {len(tracks)} 首")
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.album_list.addItem(item)

    def _fill_fav(self) -> None:
        tracks = [self.catalog.tracks[i] for i in range(len(self.catalog.tracks))
                  if self.catalog.tracks[i].id in self.favorites]
        self.fav_table.set_tracks(tracks)
        self.fav_empty.setVisible(not tracks)
        self.fav_table.setVisible(bool(tracks))
        self._sync_highlight()

    def _fill_recent(self) -> None:
        by_id = {t.id: t for t in self.catalog.tracks}
        tracks = [by_id[i] for i in self.recent if i in by_id]
        self.recent_table.set_tracks(tracks)
        self.recent_empty.setVisible(not tracks)
        self.recent_table.setVisible(bool(tracks))
        self._sync_highlight()

    # ------------------------------------------------------------- playback
    def _play(self, track: Track) -> None:
        table = self.sender() if isinstance(self.sender(), TrackTable) else None
        context = table.tracks() if table else None
        if track.has_audio or track.download_url:
            self.player.play_track(track, context)
        else:
            self._on_source_missing(track)

    def _play_all(self) -> None:
        tracks = self.visible_tracks()
        playable = [t for t in tracks if t.has_audio or t.download_url]
        if not playable:
            self._toast("未检测到可用音源：请将音频文件放入 music 文件夹后点击「扫描本地音乐」")
            self.now_panel.set_hint()
            return
        # prefer a locally matched track, otherwise start on the first online source
        start = next((t for t in playable if t.has_audio), playable[0])
        self.player.set_queue(tracks, start)
        self.player.play_index(self.player.pos)

    def _cycle_mode(self) -> None:
        order = [Mode.ORDER, Mode.LOOP_ALL, Mode.LOOP_ONE, Mode.SHUFFLE]
        nxt = order[(order.index(self.player.mode) + 1) % len(order)]
        self.player.mode = nxt
        self.bar.set_mode(nxt)

    def _on_position(self, ms: int) -> None:
        self.bar.set_position(ms)
        self.now_panel.set_position_ms(ms)

    def _on_playing(self, on: bool) -> None:
        self.bar.set_playing(on)
        self.now_panel.set_playing(on)
        for t in self._all_tables():
            t.playing = on
            t.viewport().update()

    def _on_track_changed(self, track: Track) -> None:
        pm = self.loader.get(track.cover_url)
        if pm is None:
            pm = art.default_cover(196, track.title_display[:1] or "民", seed=track.id)
        else:
            pm = pm.scaled(196, 196, Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
        self.now_panel.set_track(track, pm)
        self.bar.set_track_info(track.title_display, track.singer_display, pm)
        self.bar.set_fav(track.id in self.favorites)
        self._remember_recent(track)
        self._sync_highlight(track)

    def _on_source_missing(self, track: Track) -> None:
        self.now_panel.set_track(
            track, art.default_cover(196, track.title_display[:1] or "民", seed=track.id))
        self.now_panel.set_hint()
        self._toast(f"《{track.title_display}》暂无可用音源，请放入本地音频文件")

    def _on_playback_error(self, msg: str) -> None:
        self._toast(msg)
        self.now_panel.set_hint()

    def _sync_highlight(self, track: Track = None) -> None:
        cur = track or self.player.current()
        for table in self._all_tables():
            row = table.row_of(cur) if cur else -1
            table.set_current_row(row)

    # ------------------------------------------------------------- favourites
    def _toggle_fav(self, track: Track) -> None:
        if track.id in self.favorites:
            self.favorites.discard(track.id)
            self._toast(f"已取消收藏《{track.title_display}》")
        else:
            self.favorites.add(track.id)
            self._toast(f"已收藏《{track.title_display}》")
        self._save_library()
        self.bar.set_fav(track.id in self.favorites)
        if self.stack.currentIndex() == 3:
            self._fill_fav()

    def _fav_current(self) -> None:
        cur = self.player.current()
        if cur:
            self._toggle_fav(cur)

    def _remember_recent(self, track: Track) -> None:
        if track.id in self.recent:
            self.recent.remove(track.id)
        self.recent.insert(0, track.id)
        del self.recent[200:]
        self._save_library()

    # ------------------------------------------------------------ local files
    def scan_local(self, silent: bool = False) -> None:
        found = self.catalog.attach_local_audio(music_dir())
        self._refresh_songs()
        self._sync_highlight()
        if self.stack.currentIndex() == 3:
            self._fill_fav()
        if self.stack.currentIndex() == 4:
            self._fill_recent()
        if not silent:
            if found:
                self._toast(f"扫描完成：已匹配 {found} 首本地音源")
            else:
                self._toast(f"在 {music_dir()} 未找到音频文件")

    def _open_music_dir(self) -> None:
        os.makedirs(music_dir(), exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(music_dir()))

    # ---------------------------------------------------------------- panel
    def _toggle_now_panel(self) -> None:
        self.now_panel.setVisible(not self.now_panel.isVisible())

    def _toggle_max(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        self.title_bar.set_maximized(self.isMaximized())

    # --------------------------------------------------------------- library
    def _lib_path(self) -> str:
        return os.path.join(user_data_dir(), self._LIB_FILE)

    def _load_library(self) -> None:
        try:
            with open(self._lib_path(), "r", encoding="utf-8") as fh:
                data = json.load(fh)
            self.favorites = set(data.get("favorites") or [])
            self.recent = list(data.get("recent") or [])
        except (OSError, ValueError):
            pass

    def _save_library(self) -> None:
        try:
            with open(self._lib_path(), "w", encoding="utf-8") as fh:
                json.dump({"favorites": sorted(self.favorites),
                           "recent": self.recent}, fh, ensure_ascii=False)
        except OSError:
            pass

    # ----------------------------------------------------------------- misc
    def _toast(self, msg: str) -> None:
        self.toast.show_message(msg)

    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        self.toast._reposition()

    # frameless edge-resize via global event filter
    def install_resize_filter(self) -> None:
        QApplication.instance().installEventFilter(self)

    def eventFilter(self, obj: QObject, ev: QEvent) -> bool:  # noqa: N802
        if ev.type() != QEvent.Type.MouseButtonPress or self.isMaximized():
            return super().eventFilter(obj, ev)

        w = self.windowHandle()
        if w is None or not self.isVisible():
            return super().eventFilter(obj, ev)

        local = self.mapFromGlobal(QCursor.pos())
        m = 6
        left = local.x() <= m
        right = local.x() >= self.width() - m
        top = local.y() <= m
        bottom = local.y() >= self.height() - m
        # Only act on a genuine press inside the window. Without this guard a
        # stale/offscreen cursor yields opposing edges (or a negative frame),
        # which makes startSystemResize fault the window (0xC000041D).
        if not (-m <= local.x() <= self.width() + m
                and -m <= local.y() <= self.height() + m):
            return super().eventFilter(obj, ev)

        edges = Qt.Edge(0)
        if left:
            edges |= Qt.Edge.LeftEdge
        if right:
            edges |= Qt.Edge.RightEdge
        if top:
            edges |= Qt.Edge.TopEdge
        if bottom:
            edges |= Qt.Edge.BottomEdge
        # Resizing needs exactly one axis; a corner carries two adjacent edges.
        horiz = int(bool(edges & Qt.Edge.LeftEdge)) + int(bool(edges & Qt.Edge.RightEdge))
        vert = int(bool(edges & Qt.Edge.TopEdge)) + int(bool(edges & Qt.Edge.BottomEdge))
        if horiz > 1 or vert > 1:
            return super().eventFilter(obj, ev)
        if not edges:
            return super().eventFilter(obj, ev)

        w.startSystemResize(edges)
        return True
