# -*- coding: utf-8 -*-
"""朝鲜族音乐 · 网页版服务

把曲库(database.json)、本地音频与在线音源统一暴露给浏览器前端。
- 曲库浏览 / 搜索 / 在线可播筛选
- 上传音频 -> 自动匹配曲库条目
- 播放：本地文件直传，其余走在线链接
"""
from __future__ import annotations

import json
import mimetypes
import os
import re
import unicodedata
import urllib.request
import urllib.error

from flask import Flask, jsonify, request, send_file, abort

BASE = os.path.dirname(os.path.abspath(__file__))
MUSIC_DIR = os.path.join(BASE, "music")
DB_PATH = os.path.join(BASE, "database.json")
ALIVE_PATH = os.path.join(BASE, "data", "alive.json")
AUDIO_EXTS = {".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac", ".wma", ".ape"}

os.makedirs(MUSIC_DIR, exist_ok=True)

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 512 * 1024 * 1024  # 单次上传上限 512MB


# ----------------------------------------------------------------- 数据加载
def normalize(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text).lower()
    text = re.sub(r"[（(\[【].*?[)）\]】]", "", text)
    return re.sub(r"[^0-9a-z一-鿿가-힯]+", "", text)


def load_catalog() -> list[dict]:
    with open(DB_PATH, "r", encoding="utf-8") as fh:
        raw = json.load(fh)

    alive_ids = set()
    if os.path.isfile(ALIVE_PATH):
        try:
            with open(ALIVE_PATH, "r", encoding="utf-8") as fh:
                alive_ids = set(json.load(fh).get("alive_ids") or [])
        except (OSError, ValueError):
            pass

    local_map = scan_local()
    tracks = []
    for i, item in enumerate(raw.get("tracks") or []):
        song = item.get("_song") or {}
        tid = item.get("id") or f"#{i}"
        url = song.get("download_url") or ""
        title = (item.get("song_name") or "").strip()
        tracks.append({
            "id": tid,
            "title": title,
            "singers": (item.get("singers") or "").strip(),
            "album": (item.get("album") or "").strip(),
            "duration_s": int(item.get("duration_s") or 0),
            "duration": item.get("duration") or "",
            "ext": (item.get("ext") or "").upper(),
            "file_size": item.get("file_size") or "",
            "cover_url": item.get("cover_url") or "",
            "lyric": item.get("lyric") if isinstance(item.get("lyric"), str) else (song.get("lyric") or ""),
            "source_cn": item.get("source_cn") or "",
            "online_url": url if tid in alive_ids else "",
            "local_file": local_map.get(tid),
            "_sort": normalize(title),
        })
    return tracks


def scan_local() -> dict[str, str]:
    """把 music/ 下的音频按文件名匹配到曲库 id。"""
    files = [
        os.path.join(MUSIC_DIR, n)
        for n in os.listdir(MUSIC_DIR)
        if os.path.splitext(n)[1].lower() in AUDIO_EXTS
    ]
    if not files:
        return {}

    with open(DB_PATH, "r", encoding="utf-8") as fh:
        raw = json.load(fh)

    entries = []
    for i, item in enumerate(raw.get("tracks") or []):
        entries.append((item.get("id") or f"#{i}", item.get("song_name") or ""))

    mapping: dict[str, str] = {}
    used = set()
    for path in sorted(files):
        stem = normalize(os.path.splitext(os.path.basename(path))[0])
        if not stem:
            continue
        for tid, title in entries:
            if tid in used:
                continue
            nt = normalize(title)
            nid = normalize(tid)
            if (nid and nid in stem) or (nt and nt and (nt in stem or (stem in nt and len(stem) >= 4))):
                mapping[tid] = os.path.basename(path)
                used.add(tid)
                break
    return mapping


CATALOG: list[dict] = []
LOCAL_MAP: dict[str, str] = {}


def refresh() -> None:
    global CATALOG, LOCAL_MAP
    LOCAL_MAP = scan_local()
    CATALOG = load_catalog()


@app.before_request
def _ensure_catalog():
    if not CATALOG:
        refresh()


# ------------------------------------------------------------------- 接口
@app.get("/api/tracks")
def api_tracks():
    q = normalize(request.args.get("q", ""))
    view = request.args.get("view", "all")

    rows = []
    for t in CATALOG:
        has_local = bool(t["local_file"])
        has_online = bool(t["online_url"])
        if view == "online" and not has_online:
            continue
        if view == "local" and not has_local:
            continue
        if view == "playable" and not (has_local or has_online):
            continue
        if q and q not in (t["_sort"] + normalize(t["singers"]) + normalize(t["album"])):
            continue
        rows.append(t)

    return jsonify({
        "total": len(CATALOG),
        "count": len(rows),
        "stats": {
            "online": sum(1 for t in CATALOG if t["online_url"]),
            "local": sum(1 for t in CATALOG if t["local_file"]),
            "dead": sum(1 for t in CATALOG if not t["online_url"] and not t["local_file"]),
        },
        "tracks": rows,
    })


@app.get("/api/track/<path:tid>")
def api_track(tid):
    for t in CATALOG:
        if t["id"] == tid:
            return jsonify(t)
    abort(404)


@app.get("/api/play/<path:tid>")
def api_play(tid):
    for t in CATALOG:
        if t["id"] != tid:
            continue
        if t["local_file"]:
            path = os.path.join(MUSIC_DIR, t["local_file"])
            if os.path.isfile(path):
                return send_file(path, conditional=True)
        if t["online_url"]:
            try:
                req = urllib.request.Request(
                    t["online_url"],
                    headers={"User-Agent": "Mozilla/5.0", "Referer": "https://music.migu.cn/"},
                )
                with urllib.request.urlopen(req, timeout=20) as resp:
                    data = resp.read()
            except Exception as exc:
                return jsonify({"error": f"音源拉取失败: {exc}"}), 502
            ctype = resp.headers.get("Content-Type") or "audio/mpeg"
            return app.response_class(data, mimetype=ctype)
        return jsonify({"error": "该曲目暂无可用音源，请上传本地音频"}), 404
    abort(404)


@app.post("/api/upload")
def api_upload():
    """上传音频 -> 按文件名自动匹配曲库条目。"""
    saved = []
    unmatched = []
    for f in request.files.getlist("audio"):
        name = os.path.basename(f.filename or "")
        ext = os.path.splitext(name)[1].lower()
        if not name or ext not in AUDIO_EXTS:
            continue
        target = os.path.join(MUSIC_DIR, name)
        f.save(target)
        saved.append(name)

    refresh()
    matched = {tid: fn for tid, fn in LOCAL_MAP.items() if fn in saved}
    for name in saved:
        if name not in matched.values():
            unmatched.append(name)

    return jsonify({
        "saved": saved,
        "matched": [{"id": tid, "file": fn} for tid, fn in matched.items()],
        "unmatched": unmatched,
    })


@app.get("/api/local-files")
def api_local_files():
    return jsonify(sorted(
        n for n in os.listdir(MUSIC_DIR)
        if os.path.splitext(n)[1].lower() in AUDIO_EXTS
    ))


@app.post("/api/local-file/delete")
def api_delete_local():
    """删除 music/ 下的本地音频文件。只接受纯文件名，强制解析后必须仍在 music/ 内。"""
    name = os.path.basename(request.args.get("name", "")).strip()
    if not name or os.path.splitext(name)[1].lower() not in AUDIO_EXTS:
        return jsonify({"ok": False, "error": "非法文件名"}), 400

    path = os.path.realpath(os.path.join(MUSIC_DIR, name))
    root = os.path.realpath(MUSIC_DIR)
    if os.path.commonpath([path, root]) != root:
        return jsonify({"ok": False, "error": "路径越界"}), 400
    if not os.path.isfile(path):
        return jsonify({"ok": False, "error": "文件不存在"}), 404

    os.remove(path)
    refresh()
    return jsonify({"ok": True})


@app.get("/")
def index():
    with open(os.path.join(BASE, "web", "index.html"), "r", encoding="utf-8") as fh:
        return fh.read()


if __name__ == "__main__":
    refresh()
    print(f"catalog={len(CATALOG)} online={sum(1 for t in CATALOG if t['online_url'])} "
          f"local={sum(1 for t in CATALOG if t['local_file'])}", flush=True)
    app.run(host="127.0.0.1", port=8848, debug=False)
