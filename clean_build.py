# -*- coding: utf-8 -*-
"""One-shot cleanup for PyInstaller output dirs (batch-delete safe)."""
import os
import sys

for p in ("build", "dist"):
    if not os.path.isdir(p):
        continue
    for root, dirs, files in os.walk(p, topdown=False):
        for f in files:
            os.remove(os.path.join(root, f))
        for d in dirs:
            os.rmdir(os.path.join(root, d))
    os.rmdir(p)
    print("rm", p)
print("done")