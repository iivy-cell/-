@echo off
REM 朝鲜族音乐 · 网页版一键启动
cd /d "%~dp0"
start "" http://127.0.0.1:8848
".venv\Scripts\python.exe" -u web_server.py
pause