# -*- coding: utf-8 -*-
"""Programmatically drawn Korean-ethnic artwork & icons (no external assets).

Motifs: taegeuk swirl (太极/태극), fan ribs (부채), plum blossom (매화),
hangul/kanji letterforms on hanji-paper covers, all via QPainter.
"""
import hashlib
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QFont, QIcon, QLinearGradient,
                           QPainter, QPainterPath, QPen, QPixmap,
                           QRadialGradient, QTransform)

RED = "#E2543F"
BLUE = "#3E8FB0"
GOLD = "#D9A85E"
CREAM = "#F5EBD8"
INK = "#151110"


def _pm(size: int) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    return pm


def _painter(pm: QPixmap) -> QPainter:
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    return p


# --------------------------------------------------------------------- taegeuk
def taegeuk(size: int, red: str = RED, blue: str = BLUE, bg: str = None) -> QPixmap:
    """Red-top / blue-bottom taegeuk swirl, optionally on a circular ground."""
    pm = _pm(size)
    p = _painter(pm)
    c = size / 2.0
    r = size * 0.48
    if bg:
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(bg))
        p.drawEllipse(QRectF(c - r, c - r, 2 * r, 2 * r))
    r = size * 0.46
    big = QRectF(c - r, c - r, 2 * r, 2 * r)
    up = QRectF(c - r / 2, c - r, r, r)      # circle centred (c, c - r/2)
    low = QRectF(c - r / 2, c, r, r)         # circle centred (c, c + r/2)

    # red half: left semicircle + lower bulge right
    red_path = QPainterPath()
    red_path.moveTo(c, c - r)
    red_path.arcTo(big, 90, 180)
    red_path.arcTo(low, 270, 180)
    red_path.arcTo(up, 270, -180)
    red_path.closeSubpath()

    # blue half: complement
    blue_path = QPainterPath()
    blue_path.moveTo(c, c - r)
    blue_path.arcTo(big, 90, -180)
    blue_path.arcTo(up, 90, 180)
    blue_path.arcTo(low, 90, -180)
    blue_path.closeSubpath()

    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(red))
    p.drawPath(red_path)
    p.setBrush(QColor(blue))
    p.drawPath(blue_path)
    dot = r * 0.17
    p.setBrush(QColor(blue))
    p.drawEllipse(QPointF(c, c - r / 2), dot, dot)
    p.setBrush(QColor(red))
    p.drawEllipse(QPointF(c, c + r / 2), dot, dot)
    p.end()
    return pm


def logo_icon(size: int = 64) -> QIcon:
    return QIcon(taegeuk(size, bg="#F5EBD8"))


# --------------------------------------------------------------- decorations
def fan_ribs(p: QPainter, cx: float, cy: float, radius: float, spread_deg: float,
             count: int, color: QColor, width: float = 1.2, alpha: int = 60) -> None:
    pen = p.pen()
    p.save()
    pen.setWidthF(width)
    col = QColor(color)
    col.setAlpha(alpha)
    pen.setColor(col)
    p.setPen(pen)
    start = 180 - spread_deg / 2
    for i in range(count):
        ang = start + spread_deg * i / max(1, count - 1)
        rad = math.pi * ang / 180.0
        x = cx + radius * -math.cos(rad)
        y = cy + radius * -math.sin(rad)
        p.drawLine(QPointF(cx, cy), QPointF(x, y))
    p.restore()


def plum(p: QPainter, cx: float, cy: float, radius: float, color: QColor,
         petal_alpha: int = 200) -> None:
    p.save()
    col = QColor(color)
    p.setPen(Qt.PenStyle.NoPen)
    col.setAlpha(petal_alpha)
    p.setBrush(col)
    for i in range(5):
        ang = math.pi * 2 * i / 5 - math.pi / 2
        px = cx + radius * 0.62 * math.cos(ang)
        py = cy + radius * 0.62 * math.sin(ang)
        p.drawEllipse(QPointF(px, py), radius * 0.46, radius * 0.46)
    col.setAlpha(255)
    p.setBrush(QColor("#F2C14E"))
    p.drawEllipse(QPointF(cx, cy), radius * 0.24, radius * 0.24)
    p.restore()


# --------------------------------------------------------------- cover making
def default_cover(size: int, title: str, seed: str = "") -> QPixmap:
    """Generated Korean-folk cover used when a real cover URL is dead."""
    pm = _pm(size)
    p = _painter(pm)
    h = int(hashlib.md5((seed or title or "x").encode("utf-8")).hexdigest(), 16)
    palettes = [
        ("#7E2A22", "#3A120E"),   # deep red
        ("#27536B", "#0F2430"),   # indigo blue
        ("#6B4A21", "#2A1C0C"),   # ochre gold
        ("#4A3A63", "#1D1528"),   # plum violet
        ("#2E5240", "#12241C"),   # pine green
    ]
    top, bottom = palettes[h % len(palettes)]
    grad = QLinearGradient(0, 0, 0, size)
    grad.setColorAt(0.0, QColor(top))
    grad.setColorAt(1.0, QColor(bottom))
    p.fillRect(pm.rect(), QBrush(grad))

    # moon-gate ring
    ring = QColor(CREAM)
    ring.setAlpha(38)
    p.setPen(QPen(ring, size * 0.012))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(QRectF(size * 0.14, size * 0.12, size * 0.72, size * 0.72))

    # fan ribs from the bottom centre
    fan_ribs(p, size / 2.0, size * 1.06, size * 0.78, 150, 13, QColor(CREAM),
             width=size * 0.006, alpha=46)

    # taegeuk watermark
    swirl = taegeuk(int(size * 0.34))
    swirl_s = swirl.scaled(int(size * 0.34), int(size * 0.34),
                           Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
    p.setOpacity(0.16)
    p.drawPixmap(int(size * 0.60), int(size * 0.10), swirl_s)
    p.setOpacity(1.0)

    # plum blossoms
    plum(p, size * 0.20, size * 0.78, size * 0.075, QColor(RED), petal_alpha=150)
    plum(p, size * 0.31, size * 0.86, size * 0.05, QColor(CREAM), petal_alpha=90)

    # big first letter
    ch = (title or "民").strip()
    ch = ch[0] if ch else "民"
    f = QFont("Microsoft YaHei", int(size * 0.30))
    f.setBold(True)
    p.setFont(f)
    p.setPen(QColor(CREAM))
    p.drawText(QRectF(0, size * 0.10, size, size * 0.72),
               Qt.AlignmentFlag.AlignCenter, ch)
    p.end()
    return pm


def circle_crop(pm: QPixmap) -> QPixmap:
    if pm.isNull():
        return pm
    side = min(pm.width(), pm.height())
    out = _pm(side)
    p = _painter(out)
    path = QPainterPath()
    path.addEllipse(0, 0, side, side)
    p.setClipPath(path)
    src = pm.scaled(side, side, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation)
    p.drawPixmap(0, 0, src)
    p.end()
    return out


def rounded(pm: QPixmap, radius: int) -> QPixmap:
    if pm.isNull():
        return pm
    out = QPixmap(pm.size())
    out.fill(Qt.GlobalColor.transparent)
    p = _painter(out)
    path = QPainterPath()
    path.addRoundedRect(0, 0, pm.width(), pm.height(), radius, radius)
    p.setClipPath(path)
    p.drawPixmap(0, 0, pm)
    p.end()
    return out


# --------------------------------------------------------------------- icons
def icon(name: str, color: str = "#EFE6D6", size: int = 18, width: float = 1.6) -> QIcon:
    pm = _pm(size)
    p = _painter(pm)
    col = QColor(color)
    pen = QPen(col, width)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    s = size
    m = size * 0.10  # margin

    def tri(pts, fill=True):
        path = QPainterPath()
        path.moveTo(*pts[0])
        for pt in pts[1:]:
            path.lineTo(*pt)
        path.closeSubpath()
        if fill:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(col)
        p.drawPath(path)
        if fill:
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)

    if name == "play":
        tri([(s * .32, s * .20), (s * .82, s * .5), (s * .32, s * .80)])
    elif name == "pause":
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col)
        p.drawRoundedRect(QRectF(s * .28, s * .20, s * .14, s * .60), 2, 2)
        p.drawRoundedRect(QRectF(s * .58, s * .20, s * .14, s * .60), 2, 2)
        p.setPen(pen)
    elif name == "prev":
        p.drawLine(QPointF(s * .26, s * .22), QPointF(s * .26, s * .78))
        tri([(s * .78, s * .22), (s * .38, s * .5), (s * .78, s * .78)])
    elif name == "next":
        p.drawLine(QPointF(s * .74, s * .22), QPointF(s * .74, s * .78))
        tri([(s * .22, s * .22), (s * .62, s * .5), (s * .22, s * .78)])
    elif name == "search":
        p.drawEllipse(QRectF(s * .18, s * .18, s * .46, s * .46))
        p.drawLine(QPointF(s * .58, s * .58), QPointF(s * .82, s * .82))
    elif name == "heart":
        path = QPainterPath()
        path.moveTo(s * .5, s * .78)
        path.cubicTo(s * .12, s * .52, s * .22, s * .18, s * .5, s * .38)
        path.cubicTo(s * .78, s * .18, s * .88, s * .52, s * .5, s * .78)
        p.drawPath(path)
    elif name == "heart_fill":
        path = QPainterPath()
        path.moveTo(s * .5, s * .78)
        path.cubicTo(s * .12, s * .52, s * .22, s * .18, s * .5, s * .38)
        path.cubicTo(s * .78, s * .18, s * .88, s * .52, s * .5, s * .78)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col)
        p.drawPath(path)
        p.setPen(pen)
    elif name == "volume":
        path = QPainterPath()
        path.moveTo(s * .16, s * .42)
        path.lineTo(s * .32, s * .42)
        path.lineTo(s * .50, s * .24)
        path.lineTo(s * .50, s * .76)
        path.lineTo(s * .32, s * .58)
        path.lineTo(s * .16, s * .58)
        path.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col)
        p.drawPath(path)
        p.setPen(pen)
        p.drawArc(QRectF(s * .50, s * .34, s * .22, s * .32), -60 * 16, 120 * 16)
        p.drawArc(QRectF(s * .50, s * .24, s * .34, s * .52), -60 * 16, 120 * 16)
    elif name == "volume_off":
        path = QPainterPath()
        path.moveTo(s * .16, s * .42)
        path.lineTo(s * .32, s * .42)
        path.lineTo(s * .50, s * .24)
        path.lineTo(s * .50, s * .76)
        path.lineTo(s * .32, s * .58)
        path.lineTo(s * .16, s * .58)
        path.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(col)
        p.drawPath(path)
        p.setPen(pen)
        p.drawLine(QPointF(s * .58, s * .38), QPointF(s * .82, s * .62))
        p.drawLine(QPointF(s * .82, s * .38), QPointF(s * .58, s * .62))
    elif name in ("loop", "loop_one", "shuffle"):
        if name == "shuffle":
            p.drawLine(QPointF(s * .18, s * .30), QPointF(s * .40, s * .30))
            p.drawLine(QPointF(s * .40, s * .30), QPointF(s * .66, s * .68))
            p.drawLine(QPointF(s * .18, s * .68), QPointF(s * .40, s * .68))
            p.drawLine(QPointF(s * .40, s * .68), QPointF(s * .66, s * .30))
            p.drawLine(QPointF(s * .66, s * .30), QPointF(s * .80, s * .30))
            p.drawLine(QPointF(s * .66, s * .68), QPointF(s * .80, s * .68))
            tri([(s * .74, s * .22), (s * .86, s * .30), (s * .74, s * .38)])
            tri([(s * .74, s * .60), (s * .86, s * .68), (s * .74, s * .76)])
        else:
            r = QRectF(s * .20, s * .20, s * .60, s * .60)
            p.drawArc(r, 40 * 16, 280 * 16)
            tri([(s * .74, s * .12), (s * .88, s * .26), (s * .68, s * .32)])
            if name == "loop_one":
                f = QFont("Microsoft YaHei", int(s * 0.30))
                f.setBold(True)
                p.setFont(f)
                p.drawText(QRectF(0, 0, s, s), Qt.AlignmentFlag.AlignCenter, "1")
    elif name == "list":
        for i, y in enumerate((.26, .5, .74)):
            p.drawEllipse(QPointF(s * .22, s * y), s * .045, s * .045)
            p.drawLine(QPointF(s * .34, s * y), QPointF(s * .80, s * y))
    elif name == "lyrics":
        p.drawRoundedRect(QRectF(s * .18, s * .16, s * .64, s * .68), 3, 3)
        p.drawLine(QPointF(s * .30, s * .36), QPointF(s * .70, s * .36))
        p.drawLine(QPointF(s * .30, s * .52), QPointF(s * .70, s * .52))
        p.drawLine(QPointF(s * .30, s * .68), QPointF(s * .56, s * .68))
    elif name == "close":
        p.drawLine(QPointF(s * .26, s * .26), QPointF(s * .74, s * .74))
        p.drawLine(QPointF(s * .74, s * .26), QPointF(s * .26, s * .74))
    elif name == "minimize":
        p.drawLine(QPointF(s * .28, s * .5), QPointF(s * .72, s * .5))
    elif name == "maximize":
        p.drawRect(QRectF(s * .26, s * .26, s * .48, s * .48))
    elif name == "restore":
        p.drawRect(QRectF(s * .30, s * .22, s * .44, s * .44))
        p.drawRect(QRectF(s * .22, s * .34, s * .44, s * .44))
    elif name == "music":
        p.drawEllipse(QPointF(s * .36, s * .68), s * .13, s * .10)
        p.drawLine(QPointF(s * .49, s * .68), QPointF(s * .49, s * .22))
        p.drawLine(QPointF(s * .49, s * .22), QPointF(s * .72, s * .30))
        p.drawEllipse(QPointF(s * .66, s * .40), s * .11, s * .085)
    elif name == "folder":
        path = QPainterPath()
        path.moveTo(s * .16, s * .74)
        path.lineTo(s * .16, s * .30)
        path.lineTo(s * .40, s * .30)
        path.lineTo(s * .46, s * .38)
        path.lineTo(s * .84, s * .38)
        path.lineTo(s * .84, s * .74)
        path.closeSubpath()
        p.drawPath(path)
    elif name == "refresh":
        r = QRectF(s * .22, s * .22, s * .56, s * .56)
        p.drawArc(r, 40 * 16, 280 * 16)
        tri([(s * .72, s * .14), (s * .86, s * .28), (s * .66, s * .34)])
    elif name == "singer":
        p.drawEllipse(QPointF(s * .5, s * .36), s * .16, s * .16)
        p.drawArc(QRectF(s * .20, s * .46, s * .60, s * .60), 20 * 16, 140 * 16)
    elif name == "album":
        p.drawEllipse(QRectF(s * .20, s * .20, s * .60, s * .60))
        p.drawEllipse(QPointF(s * .5, s * .5), s * .08, s * .08)
    elif name == "chevron_left":
        p.drawLine(QPointF(s * .58, s * .24), QPointF(s * .38, s * .5))
        p.drawLine(QPointF(s * .38, s * .5), QPointF(s * .58, s * .76))
    elif name == "chevron_right":
        p.drawLine(QPointF(s * .42, s * .24), QPointF(s * .62, s * .5))
        p.drawLine(QPointF(s * .62, s * .5), QPointF(s * .42, s * .76))
    p.end()
    return QIcon(pm)
