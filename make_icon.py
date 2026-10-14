# -*- coding: utf-8 -*-
"""Render the taegeuk logo into a multi-size Windows .ico (needs Pillow)."""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image  # noqa: E402
from PySide6.QtCore import QBuffer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from app import art  # noqa: E402


def main():
    app = QApplication([])
    sizes = (256, 128, 64, 48, 32, 16)
    base = None
    for s in sizes:
        pm = art.taegeuk(s, bg="#F5EBD8")
        buf = QBuffer()
        buf.open(QBuffer.OpenModeFlag.ReadWrite)
        pm.save(buf, "PNG")
        img = Image.open(io.BytesIO(bytes(buf.data()))).convert("RGBA")
        if base is None:
            base = img
    out = os.path.join("assets", "app.ico")
    base.save(out, format="ICO", sizes=[(s, s) for s in sizes])
    print("saved", out, os.path.getsize(out), "bytes")
    os._exit(0)


if __name__ == "__main__":
    main()
