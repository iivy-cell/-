# -*- coding: utf-8 -*-
"""Music catalog loaded from the bundled ethnic-minority database JSON."""
import json
import os
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .paths import resource_path, alive_index_path


def normalize(text: str) -> str:
    """Aggressive normalization used to match filenames to catalog entries."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = text.lower()
    # drop bracketed decorations, punctuation, whitespace
    text = re.sub(r"[（(\[【].*?[)）\]】]", "", text)
    text = re.sub(r"[^0-9a-z一-鿿가-힯]+", "", text)
    return text


@dataclass
class Track:
    index: int
    id: str
    title: str
    singers: str
    album: str
    duration_s: int
    duration: str
    ext: str
    file_size: str
    cover_url: str
    lyric: str
    source_cn: str
    download_url: str
    local_path: Optional[str] = None
    alive: bool = True
    _sort: str = field(default="", repr=False)

    def __post_init__(self):
        self._sort = normalize(self.title)

    @property
    def title_display(self) -> str:
        return self.title or "(未知曲目)"

    @property
    def singer_display(self) -> str:
        return self.singers or "未知歌手"

    @property
    def album_display(self) -> str:
        return self.album or "未知专辑"

    @property
    def has_audio(self) -> bool:
        return bool(self.local_path)

    @property
    def online_alive(self) -> bool:
        """True when the stored CDN link still resolves (not known-expired)."""
        return self.alive and bool(self.download_url)

    @property
    def playable(self) -> bool:
        return bool(self.local_path) or self.online_alive

    def search_blob(self) -> str:
        return normalize(f"{self.title} {self.singers} {self.album}")


class Catalog:
    def __init__(self, json_path: Optional[str] = None):
        path = json_path or resource_path("database.json")
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)

        self.path = path
        self.name: str = raw.get("name", "民族音乐")
        self.group: str = raw.get("group", "")
        self.key: str = raw.get("key", "")
        self.cover_url: str = raw.get("cover") or ""
        self.keywords: List[str] = list(raw.get("kws") or [])
        self.sources: List[str] = [
            s if isinstance(s, str) else str(s) for s in (raw.get("sources") or [])
        ]

        self.tracks: List[Track] = []
        for i, item in enumerate(raw.get("tracks") or []):
            song = item.get("_song") or {}
            lyric = item.get("lyric")
            if not isinstance(lyric, str):
                lyric = song.get("lyric") or ""
            self.tracks.append(
                Track(
                    index=i,
                    id=item.get("id") or f"#{i}",
                    title=(item.get("song_name") or "").strip(),
                    singers=(item.get("singers") or "").strip(),
                    album=(item.get("album") or "").strip(),
                    duration_s=int(item.get("duration_s") or 0),
                    duration=item.get("duration") or "",
                    ext=(item.get("ext") or "").upper(),
                    file_size=item.get("file_size") or "",
                    cover_url=item.get("cover_url") or "",
                    lyric=lyric or "",
                    source_cn=item.get("source_cn") or "",
                    download_url=song.get("download_url") or "",
                )
            )

        self._by_singer: Dict[str, List[Track]] = {}
        self._by_album: Dict[str, List[Track]] = {}
        for t in self.tracks:
            self._by_singer.setdefault(t.singer_display, []).append(t)
            self._by_album.setdefault(t.album_display, []).append(t)

        self.load_alive_index()

    # -- live-source index ------------------------------------------------
    def load_alive_index(self) -> int:
        """Apply data/alive.json (produced by probe_alive.py).

        CDN links in database.json are time-limited signed URLs; most expire
        within days. The index records which ids were verified reachable at
        probe time. Missing file -> everything stays optimistically alive.
        Returns number of tracks currently marked alive.
        """
        path = alive_index_path()
        if not os.path.isfile(path):
            # frozen build: the shipped index lives in read-only _MEIPASS
            path = resource_path("data", "alive.json")
        if not os.path.isfile(path):
            return sum(1 for t in self.tracks if t.download_url)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                blob = json.load(fh)
        except (OSError, ValueError):
            return sum(1 for t in self.tracks if t.download_url)

        alive_ids = set(blob.get("alive_ids") or [])
        self.alive_probed_at = blob.get("probed_at")
        for t in self.tracks:
            if t.download_url:
                t.alive = t.id in alive_ids
        return sum(1 for t in self.tracks if t.online_alive)

    def online_tracks(self) -> List[Track]:
        """Only tracks whose online link verified alive — the fast lane."""
        return [t for t in self.tracks if t.online_alive]

    def playable_tracks(self) -> List[Track]:
        return [t for t in self.tracks if t.playable]

    # -- aggregate stats -------------------------------------------------
    def __len__(self) -> int:
        return len(self.tracks)

    @property
    def singer_count(self) -> int:
        return len(self._by_singer)

    @property
    def album_count(self) -> int:
        return len(self._by_album)

    def total_duration_s(self) -> int:
        return sum(t.duration_s for t in self.tracks)

    @property
    def online_playable_count(self) -> int:
        """Tracks whose download_url points at a currently-live CDN (Migu)."""
        return sum(1 for t in self.tracks if "migu.cn" in (t.download_url or ""))

    def albums(self) -> List[str]:
        return sorted(self._by_album.keys())

    def singers(self) -> List[str]:
        return sorted(self._by_singer.keys())

    def tracks_of_singer(self, singer: str) -> List[Track]:
        return self._by_singer.get(singer, [])

    def tracks_of_album(self, album: str) -> List[Track]:
        return self._by_album.get(album, [])

    # -- searching -------------------------------------------------------
    def search(self, query: str) -> List[Track]:
        q = normalize(query)
        if not q:
            return list(self.tracks)
        exact, loose = [], []
        for t in self.tracks:
            blob = t.search_blob()
            if q in t._sort:
                exact.append(t)
            elif q in blob:
                loose.append(t)
        return exact + loose

    # -- local audio -----------------------------------------------------
    def attach_local_audio(self, music_dir_obj: str) -> int:
        """Scan a folder of audio files and bind them to catalog entries.

        Matching is intentionally forgiving: a track is satisfied when either
        its id, or its normalized title (optionally with singer), appears in
        the normalized filename. Returns how many tracks now have audio.
        """
        if not music_dir_obj or not os.path.isdir(music_dir_obj):
            return 0

        for t in self.tracks:
            t.local_path = None

        exts = (".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac", ".wma", ".ape")
        files: List[str] = []
        for root, _dirs, names in os.walk(music_dir_obj):
            files.extend(
                os.path.join(root, n)
                for n in names
                if os.path.splitext(n)[1].lower() in exts
            )

        unresolved = list(self.tracks)
        for path in files:
            stem = os.path.splitext(os.path.basename(path))[0]
            nstem = normalize(stem)
            if not nstem:
                continue
            for t in list(unresolved):
                nid = normalize(t.id)
                nid_short = normalize(t.id.split("#")[-1])
                ntitle = t._sort
                hit = False
                if nid and nid in nstem:
                    hit = True
                elif nid_short and nstem == nid_short:
                    hit = True
                elif ntitle and ntitle in nstem:
                    hit = True
                elif nstem and nstem in ntitle and len(nstem) >= 4:
                    hit = True
                if hit and not t.local_path:
                    t.local_path = path
                    unresolved.remove(t)

        return sum(1 for t in self.tracks if t.local_path)
