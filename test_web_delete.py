# -*- coding: utf-8 -*-
"""End-to-end test for the local-audio delete flow, including path-traversal guards."""
import json
import mimetypes
import urllib.error
import urllib.parse
import urllib.request
import uuid

BASE = "http://127.0.0.1:8848"


def get(path):
    return json.loads(urllib.request.urlopen(BASE + path, timeout=30).read())


def post(path):
    try:
        return json.loads(urllib.request.urlopen(
            BASE + path, data=b"", timeout=30).read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())


def upload(filename, payload):
    boundary = uuid.uuid4().hex
    ctype = mimetypes.guess_type(filename)[0] or "audio/mpeg"
    body = b"".join([
        f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="audio"; filename="{filename}"\r\n'.encode(),
        f"Content-Type: {ctype}\r\n\r\n".encode(),
        payload, b"\r\n", f"--{boundary}--\r\n".encode(),
    ])
    req = urllib.request.Request(
        BASE + "/api/upload", data=body, method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())


# 1) upload a real track
online = get("/api/tracks?view=online")["tracks"]
t = online[5]
raw = urllib.request.urlopen(
    BASE + "/api/play/" + urllib.parse.quote(t["id"]), timeout=90).read()
name = t["title"].replace("/", "-") + ".mp3"
res = upload(name, raw)
assert name in res["saved"], res
print(f"uploaded: {name} ({len(raw)} bytes), matched={len(res['matched'])}")

local = get("/api/tracks?view=local")["tracks"]
assert any(x["local_file"] == name for x in local), "not visible in local view"
print("local view count:", len(local))

# 2) traversal attempts must be rejected
print("--- guard checks ---")
for evil in ["../database.json", "../../chaoxianzu_music/app/data.py",
             "..%2f..%2fdatabase.json", "not_audio.txt", ""]:
    r = post("/api/local-file/delete?name=" + urllib.parse.quote(evil))
    print(f"  {evil!r:42} -> {r}")
    assert not r.get("ok"), f"guard failed for {evil!r}"

# 3) the real file must still be there after the attack attempts
still = get("/api/tracks?view=local")["tracks"]
assert any(x["local_file"] == name for x in still), "catalog damaged!"
assert get("/api/tracks")["total"] == 724, "catalog.json must be intact"
print("catalog intact after attacks: 724 tracks")

# 4) now delete properly
r = post("/api/local-file/delete?name=" + urllib.parse.quote(name))
print("delete ->", r)
assert r.get("ok"), r

after = get("/api/tracks?view=local")["tracks"]
assert not any(x["local_file"] == name for x in after), "still present"
print("local view after delete:", len(after))

# 5) deleting again is a clean 404, not a crash
r = post("/api/local-file/delete?name=" + urllib.parse.quote(name))
print("delete again ->", r)
assert not r.get("ok")

print("DELETE_FLOW_OK")