# -*- coding: utf-8 -*-
"""Launch the packaged exe, wait, screenshot the screen, then kill it."""
import os
import subprocess
import sys
import time

EXE = os.path.join("dist", "ChaoxianzuMusic", "ChaoxianzuMusic.exe")

proc = subprocess.Popen([os.path.abspath(EXE)], cwd=os.path.abspath("dist/ChaoxianzuMusic"))
print("launched pid", proc.pid)
time.sleep(10)

alive = proc.poll() is None
print("still running after 10s:", alive)

from PIL import ImageGrab  # noqa: E402

shot = ImageGrab.grab()
shot.save("build", "exe_shot.png") if False else shot.save(os.path.join("build", "exe_shot.png"))
print("screenshot saved", shot.size)

if alive:
    proc.kill()
    print("killed test instance")
os._exit(0)
