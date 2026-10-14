# -*- coding: utf-8 -*-
"""Path helpers: work both in dev mode and inside a PyInstaller bundle."""
import os
import sys

IS_FROZEN = getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")

_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_PKG_DIR)


def resource_dir() -> str:
    """Where bundled read-only data lives (database.json, etc.)."""
    if IS_FROZEN:
        return sys._MEIPASS
    return _PROJECT_DIR


def resource_path(*parts: str) -> str:
    return os.path.join(resource_dir(), *parts)


def app_dir() -> str:
    """Directory containing the executable (writable side-by-side data)."""
    if IS_FROZEN:
        return os.path.dirname(sys.executable)
    return _PROJECT_DIR


def music_dir() -> str:
    """Folder the user drops local audio files into."""
    return os.path.join(app_dir(), "music")


def alive_index_path() -> str:
    """Where the source-probe index lives.

    Must be writable: the app refreshes it from the "在线可播" page, so in a
    frozen build it goes next to the exe (not into the read-only _MEIPASS).
    """
    return os.path.join(app_dir(), "data", "alive.json")


def user_data_dir() -> str:
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    path = os.path.join(base, "ChaoxianzuMusic")
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        pass
    return path


def cover_cache_dir() -> str:
    path = os.path.join(user_data_dir(), "covers")
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        pass
    return path
