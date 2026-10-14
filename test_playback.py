# -*- coding: utf-8 -*-
"""Verify QMediaPlayer (FFmpeg backend) can actually decode & play audio."""
import math
import os
import struct
import sys
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import QUrl, QTimer  # noqa: E402
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

WAV = os.path.join("build", "tone_test.wav")

# 3-second 440 Hz sine test tone
with wave.open(WAV, "w") as f:
    f.setnchannels(1)
    f.setsampwidth(2)
    f.setframerate(44100)
    frames = bytearray()
    for i in range(44100 * 3):
        v = int(12000 * math.sin(2 * math.pi * 440 * i / 44100))
        frames += struct.pack("<h", v)
    f.writeframes(bytes(frames))


def main():
    app = QApplication(sys.argv)
    player = QMediaPlayer()
    audio = QAudioOutput()
    audio.setVolume(0.1)
    player.setAudioOutput(audio)
    result = {"status": [], "positions": []}

    player.mediaStatusChanged.connect(lambda s: result["status"].append(str(s)))
    player.positionChanged.connect(lambda p: result["positions"].append(p) if p > 0 else None)
    player.setSource(QUrl.fromLocalFile(os.path.abspath(WAV)))
    player.play()

    QTimer.singleShot(4000, app.quit)
    app.exec()
    print("statuses:", result["status"])
    print("positions seen:", result["positions"][:5], "max:", max(result["positions"], default=0))
    ok = any("PlayingState" in s or "BufferedMedia" in s or "LoadedMedia" in s
             for s in result["status"])
    print("PLAYBACK", "OK" if ok and max(result["positions"], default=0) > 500 else "FAILED")
    os._exit(0)


if __name__ == "__main__":
    main()
