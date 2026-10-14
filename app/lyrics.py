# -*- coding: utf-8 -*-
"""LRC lyrics parsing."""
import re
from dataclasses import dataclass
from typing import List, Optional

_TIME = re.compile(r"\[(\d{1,3}):(\d{1,2})(?:[.:](\d{1,3}))?\]")


@dataclass
class Line:
    time: Optional[float]  # seconds; None = untimed
    text: str


class LyricDoc:
    def __init__(self, lines: List[Line]):
        self.lines = lines

    @property
    def has_text(self) -> bool:
        return any(l.text for l in self.lines)

    @property
    def timed(self) -> bool:
        return any(l.time is not None for l in self.lines)

    def index_at(self, seconds: float) -> int:
        """Index of the active line at `seconds` (-1 before first stamp)."""
        best = -1
        for i, ln in enumerate(self.lines):
            if ln.time is not None and ln.time <= seconds and ln.text:
                best = i
        return best


def parse(text: str) -> LyricDoc:
    lines: List[Line] = []
    if not text:
        return LyricDoc(lines)
    for raw in text.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        stamps = list(_TIME.finditer(raw))
        content = _TIME.sub("", raw).strip()
        if not stamps:
            lines.append(Line(None, content))
            continue
        for m in stamps:
            minutes = int(m.group(1))
            seconds = int(m.group(2))
            frac = m.group(3)
            t = minutes * 60 + seconds
            if frac:
                t += int(frac) / (10 ** len(frac))
            lines.append(Line(t, content))
    lines.sort(key=lambda l: (l.time is None, l.time if l.time is not None else 0.0))
    return LyricDoc(lines)
