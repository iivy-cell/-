# -*- coding: utf-8 -*-
"""Playback engine on top of QMediaPlayer (FFmpeg backend: MP3/FLAC/OGG/M4A)."""
import random
from enum import Enum
from typing import List, Optional

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from .data import Track


class Mode(Enum):
    ORDER = 0      # sequential, stops at end
    LOOP_ALL = 1   # wraps around
    LOOP_ONE = 2   # repeat current
    SHUFFLE = 3


class Player(QObject):
    positionChanged = Signal(int)
    durationChanged = Signal(int)
    playingChanged = Signal(bool)
    trackChanged = Signal(object)        # Track
    sourceMissing = Signal(object)       # Track (no local file & no usable url)
    playbackError = Signal(str)
    finishedQueue = Signal()

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.media = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.audio.setVolume(0.85)
        self.media.setAudioOutput(self.audio)

        self.queue: List[Track] = []
        self.pos = -1
        self.mode: Mode = Mode.LOOP_ALL
        self._fail_streak = 0

        self.media.positionChanged.connect(
            lambda v: self.positionChanged.emit(int(v)))
        self.media.durationChanged.connect(
            lambda v: self.durationChanged.emit(int(v)))
        self.media.playbackStateChanged.connect(self._on_state)
        self.media.mediaStatusChanged.connect(self._on_status)
        self.media.errorOccurred.connect(self._on_error)

    # ------------------------------------------------------------------ queue
    def set_queue(self, tracks: List[Track], start: Optional[Track] = None) -> None:
        self.queue = list(tracks)
        self.pos = self.queue.index(start) if start in self.queue else (-1 if not self.queue else 0)

    def current(self) -> Optional[Track]:
        if 0 <= self.pos < len(self.queue):
            return self.queue[self.pos]
        return None

    # ------------------------------------------------------------------ play
    def play_index(self, idx: int) -> None:
        if not (0 <= idx < len(self.queue)):
            return
        self.pos = idx
        self._start(self.queue[idx])

    def play_track(self, track: Track, context: Optional[List[Track]] = None) -> None:
        if context and track in context:
            self.queue = list(context)
            self.pos = self.queue.index(track)
        elif track not in self.queue:
            self.queue.append(track)
            self.pos = len(self.queue) - 1
        else:
            self.pos = self.queue.index(track)
        self._start(track)

    def _start(self, track: Track) -> None:
        src = None
        if track.local_path:
            src = QUrl.fromLocalFile(track.local_path)
        elif track.download_url:
            src = QUrl(track.download_url)
        if src is None or src.isEmpty():
            self.sourceMissing.emit(track)
            self.trackChanged.emit(track)
            return
        self.trackChanged.emit(track)
        self.media.setSource(src)
        self.media.play()

    def toggle(self) -> None:
        if self.media.source().isEmpty():
            return
        if self.media.isPlaying():
            self.media.pause()
        else:
            self.media.play()

    def stop(self) -> None:
        self.media.stop()
        self.media.setSource(QUrl())

    # ------------------------------------------------------------------ nav
    @staticmethod
    def _has_source(t: Track) -> bool:
        return bool(t.local_path or t.download_url)

    def next(self, auto: bool = False) -> None:
        if not self.queue:
            return
        if auto and self.mode == Mode.LOOP_ONE and self._has_source(self.current()):
            self.media.setPosition(0)
            self.media.play()
            return
        n = len(self.queue)
        idx = self.pos
        for _ in range(n):  # bounded search for the next playable track
            if self.mode == Mode.SHUFFLE and n > 1:
                choices = [i for i in range(n) if i != idx]
                idx = random.choice(choices)
            else:
                idx += 1
                if idx >= n:
                    if auto and self.mode == Mode.ORDER:
                        self.playingChanged.emit(False)
                        self.finishedQueue.emit()
                        return
                    idx = 0
            if self._has_source(self.queue[idx]):
                self.play_index(idx)
                return
        # nothing playable in the whole queue
        self.finishedQueue.emit()

    def prev(self) -> None:
        if not self.queue:
            return
        if self.media.position() > 4000:
            self.media.setPosition(0)
            return
        n = len(self.queue)
        for step in range(1, n + 1):
            idx = (self.pos - step) % n
            if self._has_source(self.queue[idx]):
                self.play_index(idx)
                return

    def seek(self, ms: int) -> None:
        self.media.setPosition(max(0, ms))

    def set_volume(self, v: float) -> None:
        self.audio.setVolume(max(0.0, min(1.0, v)))

    def volume(self) -> float:
        return self.audio.volume()

    def is_playing(self) -> bool:
        return self.media.isPlaying()

    # ------------------------------------------------------------------ slots
    def _on_state(self, state) -> None:
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        if playing:
            self._fail_streak = 0
        self.playingChanged.emit(playing)

    def _on_status(self, status) -> None:
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.next(auto=True)
        elif status == QMediaPlayer.MediaStatus.InvalidMedia:
            self._source_failed("音源已失效")

    def _on_error(self, err, err_str: str) -> None:
        if err == QMediaPlayer.Error.NoError:
            return
        self._source_failed("在线音源不可用" if (self.current() and not self.current().local_path)
                            else "本地文件无法解码")

    def _source_failed(self, reason: str) -> None:
        cur = self.current()
        label = cur.title_display if cur else "曲目"
        self._fail_streak += 1
        if cur and self._fail_streak < 10 and len(self.queue) > 1:
            # skip dead sources automatically (keeps 播放全部 working)
            self.next(auto=True)
        else:
            self.playingChanged.emit(False)
            self.playbackError.emit(f"{reason}：{label}")
