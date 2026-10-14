# -*- coding: utf-8 -*-
"""Drop one-off debug scaffolding that should not ship in the repo.

Keeps the reusable tooling: clean_build.py, probe_alive.py, test_*.py.
"""
import os

FILES = [
    "Bisect2.spec", "Bisect3.spec", "BisectExe.spec", "SpyExe.spec",
    "MiniGui.spec", "mini_gui.py", "bisect_startup.py", "dbg.spec",
    "soak_test.py", "clean_logs.py", "focus_win.py", "shot_now.py",
    "test_exe_shot.py", "diag_chips.py",
]
DIRS = ["dist_dbg", "build_dbg", "dist_mini", "build_mini",
        "dist_bisect", "build_bisect"]


def rmtree(path: str) -> None:
    if not os.path.isdir(path):
        return
    for root, dirs, files in os.walk(path, topdown=False):
        for f in files:
            os.remove(os.path.join(root, f))
        for d in dirs:
            os.rmdir(os.path.join(root, d))
    os.rmdir(path)
    print("rmdir", path)


for f in FILES:
    if os.path.isfile(f):
        os.remove(f)
        print("rm", f)
for d in DIRS:
    rmtree(d)
print("done")