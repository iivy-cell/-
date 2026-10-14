# 朝鲜族音乐 ChaoxianzuMusic

一款收录 **朝鲜族民族音乐** 的原生桌面音乐播放器（PySide6/Qt6 编写），
界面参考 QQ 音乐布局，并融入朝鲜族民族元素：太极纹 Logo、扇面 · 梅花装饰封面、
韩纸暗色主题、五方色（红/蓝/金）点缀、한글与汉字混排。

## 功能

- **曲库浏览**：724 首朝鲜族歌曲 · 351 位歌手 · 424 张专辑，全部来自 `database.json`
- **在线可播**：只列出当前链接仍有效的曲目，一键重新检测全部音源
- **搜索 / 关键词筛选**：标题栏搜索框 + 侧栏「民乐关键词」标签（阿里郎、盘索里、연변 민요…）
- **歌手 / 专辑页**：双击进入曲目详情
- **播放引擎**：Qt FFmpeg 后端，支持 MP3 / FLAC / OGG / M4A 等本地格式
- **正在播放面板**：旋转唱片封面（含民族纹样描边）、逐行滚动歌词（LRC 解析）
- **收藏 / 最近播放**：记录保存在 `%LOCALAPPDATA%\ChaoxianzuMusic`
- 快捷键：`空格` 播放/暂停，`←` / `→` 快退/快进 5 秒

## 关于音源（重要）

曲库 `database.json` 里存的在线地址大多是**平台签发的临时链接**（含 md5 签名与时间戳），
采集后数天即会过期。实测状态：

| 来源 | 曲目数 | 实测结果 |
|---|---|---|
| 咪咕 | 66 | **HTTP 206，全部可播**（静态 CDN，无时效 token） |
| 酷我 | 290 | HTTP 410 Gone |
| B站 | 263 | HTTP 403（m4s 分片需登录态鉴权） |
| MyFreeMP3 | 48 | HTTP 403 |
| 音乐库（酷我系） | 56 | HTTP 410 / 403 |
| 酷狗 | 1 | HTTP 403 |

### 「在线可播」页面

侧栏第二项 **在线可播** 只列出当前链接仍然有效的曲目（实测 66 首），
点开双击即可播放，不会遇到失效音源。右上角 **「重新检测音源」** 会联网复查全部
724 条链接并刷新列表（结果写入 `data/alive.json`），建议每隔几天点一次。

### 添加本地音频

其余曲目的在线链接已失效，请用本地文件补齐：

1. 在程序目录（安装目录）下找到 **`music`** 文件夹；
2. 将音频文件（mp3 / flac / wav / ogg / m4a…）放入其中，
   **文件名包含歌曲名** 即可自动匹配（如 `红太阳照边疆.mp3`）；
3. 回到应用点击侧栏底部「扫描本地音乐」，匹配成功的曲目即可播放。

匹配规则：文件名包含完整歌名、或包含曲库编号（如 `Ethnos#12`）。

## 安装与运行

- **安装版**：双击 `ChaoxianzuMusic_Setup.exe`（约 36 MB），按向导安装，
  自动创建桌面 / 开始菜单快捷方式，自带卸载器（卸载保留 music 文件夹）。
- **绿色版**：直接运行 `dist/ChaoxianzuMusic/ChaoxianzuMusic.exe`。

## 重新构建

```bash
# 环境：Python 3.13 + PySide6 + PyInstaller
python -m venv .venv
.venv\Scripts\pip install PySide6-Essentials PySide6-Addons pyinstaller Pillow

# 打包 exe
.venv\Scripts\pyinstaller --noconfirm --clean --windowed --name ChaoxianzuMusic ^
    --icon assets/app.ico --add-data "database.json;." main.py

# 生成安装包（需 NSIS 3，winget install NSIS.NSIS）
cd packaging && makensis installer.nsi
```

辅助脚本：`smoke_test.py`（界面自检 + 截图）、`test_playback.py`（播放引擎自检）、
`make_icon.py`（生成图标）、`test_exe.py`（打包产物启动自检）。

## 目录结构

```
chaoxianzu_music/
├─ main.py                入口
├─ app/                   应用代码（ui / player / data / art / covers / lyrics / theme）
├─ database.json          朝鲜族曲库（724 首）
├─ probe_alive.py         音源存活检测（生成 data/alive.json）
├─ data/alive.json        在线可播索引（可用「重新检测音源」刷新）
├─ assets/app.ico         太极纹应用图标
├─ packaging/installer.nsi  NSIS 安装包脚本
└─ dist/ChaoxianzuMusic/   绿色版可执行程序
```
