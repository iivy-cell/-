# -*- coding: utf-8 -*-
"""朝鲜族音乐 — entry point."""
import os
import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from app import art, theme
from app.ui import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("朝鲜族音乐")
    app.setApplicationDisplayName("朝鲜族音乐")
    app.setOrganizationName("EthnosMusic")
    app.setFont(QFont("Microsoft YaHei UI", 9))
    app.setStyleSheet(theme.build_qss())
    app.setWindowIcon(art.logo_icon(256))

    win = MainWindow()
    win.show()
    code = app.exec()
    # Skip Qt teardown (deletion-order crashes produce ugly error dialogs).
    os._exit(code)


if __name__ == "__main__":
    main()
