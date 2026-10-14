# -*- coding: utf-8 -*-
"""Stream an actual live Migu track through QMediaPlayer (end-to-end check)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import QUrl, QTimer  # noqa: E402
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


def main():
    d = json.load(open(r"C:/Users/Lenovo/Downloads/e08_朝鲜族.json", encoding="utf-8"))
    url = next(t["_song"]["download_url"] for t in d["tracks"]
               if "migu.cn" in ((t.get("_song") or {}).get("download_url") or ""))
    print("testing:", url[:90])

    app = QApplication(sys.argv)
    player = QMediaPlayer()
    audio = QAudioOutput()
    audio.setVolume(0.1)
    player.setAudioOutput(audio)
    result = {"status": [], "max_pos": 0}

    player.mediaStatusChanged.connect(lambda s: result["status"].append(str(s).split(".")[-1]))
    player.positionChanged.connect(
        lambda p: result.update(max_pos=max(result["max_pos"], p)))
    player.setSource(QUrl(url))
    player.play()

    QTimer.singleShot(8000, app.quit)
    app.exec()
    print("statuses:", result["status"])
    print("max position ms:", result["max_pos"])
    ok = result["max_pos"] > 1000 and "BufferedMedia" in " ".join(result["status"])
    print("MIGU STREAMING", "OK" if ok else "FAILED")
    os._exit(0)


if __name__ == "__main__":
    main()
