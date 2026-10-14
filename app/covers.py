# -*- coding: utf-8 -*-
"""Async cover loading with an on-disk cache (network covers, graceful fallback)."""
import hashlib
import os
from collections import OrderedDict
from typing import Optional

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from .paths import cover_cache_dir

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


class CoverLoader(QObject):
    loaded = Signal(str)  # url

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._am = QNetworkAccessManager(self)
        self._mem: "OrderedDict[str, QPixmap]" = OrderedDict()
        self._mem_limit = 240
        self._pending: set = set()

    # -- cache -----------------------------------------------------------
    def _cache_path(self, url: str) -> str:
        digest = hashlib.md5(url.encode("utf-8")).hexdigest()
        return os.path.join(cover_cache_dir(), digest + ".img")

    def _remember(self, url: str, pm: QPixmap) -> None:
        self._mem[url] = pm
        self._mem.move_to_end(url)
        while len(self._mem) > self._mem_limit:
            self._mem.popitem(last=False)

    # -- api -------------------------------------------------------------
    def get(self, url: str) -> Optional[QPixmap]:
        """Return a pixmap if immediately available, else start fetching."""
        if not url:
            return None
        if url in self._mem:
            return self._mem[url]
        path = self._cache_path(url)
        if os.path.isfile(path):
            pm = QPixmap(path)
            if not pm.isNull():
                self._remember(url, pm)
                return pm
        if url not in self._pending:
            self._pending.add(url)
            req = QNetworkRequest(QUrl(url))
            req.setHeader(QNetworkRequest.KnownHeaders.UserAgentHeader, _UA)
            req.setTransferTimeout(12000)
            reply = self._am.get(req)
            reply.finished.connect(lambda r=reply, u=url: self._on_done(r, u))
        return None

    def _on_done(self, reply: QNetworkReply, url: str) -> None:
        self._pending.discard(url)
        reply.deleteLater()
        if reply.error() != QNetworkReply.NetworkError.NoError:
            return
        data = bytes(reply.readAll())
        if not data:
            return
        pm = QPixmap()
        if pm.loadFromData(data):
            try:
                with open(self._cache_path(url), "wb") as fh:
                    fh.write(data)
            except OSError:
                pass
            self._remember(url, pm)
            self.loaded.emit(url)
