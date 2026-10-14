# -*- coding: utf-8 -*-
"""End-to-end test of the web upload + auto-match + local playback path."""
import io
import json
import mimetypes
import os
import urllib.parse
import urllib.request
import uuid

BASE = "http://127.0.0.1:8848"


def get(path):
    return json.loads(urllib.request.urlopen(BASE + path, timeout=30).read())


def make_mp3(seconds=2):
    """Minimal but decodable MP3: silent MPEG frames."""
    frame = b"\xff\xfb\x90\x64" + b"\x00" * 413
    brate = 144000  # 128kbps @44.1k
    n = int(seconds * brate / (len(frame) * 8))
    return frame * max(1, n)


def upload(filename, payload):
    boundary = uuid.uuid4().hex
    ctype = mimetypes.guess_type(filename)[0] or "audio/mpeg"
    parts = [
        f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="audio"; filename="{filename}"\r\n'.encode(),
        f"Content-Type: {ctype}\r\n\r\n".encode(),
        payload, b"\r\n", f"--{boundary}--\r\n".encode(),
    ]
    body = b"".join(parts)
    req = urllib.request.Request(
        BASE + "/api/upload", data=body, method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    return json.loads(urllib.request.urlopen(req, timeout=60).read())


# 1) pull a real track from the online pool, save it under its own name
online = get("/api/tracks?view=online")["tracks"]
t = online[3]
raw = urllib.request.urlopen(
    BASE + "/api/play/" + urllib.parse.quote(t["id"]), timeout=90).read()
print(f"source track: {t['title']} ({len(raw)} bytes)")

name = t["title"].replace("/", "-") + ".mp3"
res = upload(name, raw)
print("upload ->", {k: (len(v) if isinstance(v, list) else v) for k, v in res.items()})
assert name in res["saved"], "file not saved"
assert res["matched"], "no catalog match produced"

# 2) the track must now be flagged local and playable without network
tid = res["matched"][0]["id"]
detail = get("/api/track/" + urllib.parse.quote(tid))
print("matched id:", tid, "| local_file:", detail["local_file"])
print("lyric chars:", len(detail["lyric"] or ""))
assert detail["local_file"] == name

local_view = get("/api/tracks?view=local")["tracks"]
print("local view count:", len(local_view))
assert any(x["id"] == tid for x in local_view)

# 3) cleanup
urllib.request.urlopen(
    BASE + "/api/local-file/delete?name=" + urllib.parse.quote(name),
    data=b"", timeout=30).read()
print("cleaned up", name)
print("UPLOAD_FLOW_OK")