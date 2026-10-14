# -*- coding: utf-8 -*-
"""Smoke test: launch the full window, exercise pages, capture screenshots."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication  # noqa: E402

from app import theme  # noqa: E402


def snap(widget, path):
    widget.grab().save(path)
    print("saved", path)


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(theme.build_qss())

    from app.ui import MainWindow
    win = MainWindow()
    win.resize(1240, 800)
    win.show()
    app.processEvents()
    app.processEvents()
    snap(win, os.path.join("build", "shot_songs.png"))

    # search filter
    win.title_bar.search.setText("阿里郎")
    app.processEvents()
    win._search_debounce.start()
    win._search_debounce.timeout.emit() if False else None
    import time
    deadline = time.time() + 3
    while win._search_debounce.isActive() and time.time() < deadline:
        app.processEvents()
        time.sleep(0.05)
    snap(win, os.path.join("build", "shot_search.png"))
    win.title_bar.search.setText("")
    win._search_debounce.stop()

    # singers / albums / favorites
    win._on_nav(1)
    app.processEvents()
    snap(win, os.path.join("build", "shot_singers.png"))

    win._on_nav(2)
    app.processEvents()
    snap(win, os.path.join("build", "shot_albums.png"))

    # open a detail page (first album)
    if win.album_list.count():
        win._open_detail("album", win.album_list.item(0).data(0x0100))
        app.processEvents()
        snap(win, os.path.join("build", "shot_detail.png"))

    # now-playing panel with a track (no audio expected -> hint)
    t = win.catalog.tracks[3]
    win._on_track_changed(t)
    app.processEvents()
    snap(win, os.path.join("build", "shot_nowpanel.png"))

    # keywords chip filter
    win._on_keyword("阿里郎")
    app.processEvents()
    snap(win, os.path.join("build", "shot_keyword.png"))

    print("catalog:", len(win.catalog), "tracks;",
          win.catalog.singer_count, "singers;", win.catalog.album_count, "albums")
    print("SMOKE OK")
    os._exit(0)  # skip Qt teardown segfault at interpreter shutdown


if __name__ == "__main__":
    main()
