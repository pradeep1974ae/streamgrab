"""
StreamGrab - a modern desktop YouTube downloader.

Architecture:
    main.py         -> Python backend (this file). Owns the pywebview window,
                        talks to yt-dlp, persists presets/history to disk,
                        and exposes an Api class the frontend calls via
                        window.pywebview.api.*
    gui/index.html   -> UI shell
    gui/style.css    -> Visual design (teal/blue glow theme)
    gui/app.js       -> Frontend logic, calls into Api and renders results

Nothing here downloads anything until the user explicitly clicks download.
Respect the platform's Terms of Service and only download content you
have the rights to.
"""

import json
import os
import sys
import threading
import time
from pathlib import Path

import webview
import yt_dlp

APP_NAME = "StreamGrab"
CONFIG_DIR = Path.home() / ".streamgrab"
PRESETS_FILE = CONFIG_DIR / "presets.json"
HISTORY_FILE = CONFIG_DIR / "history.json"
SETTINGS_FILE = CONFIG_DIR / "settings.json"

DEFAULT_DOWNLOAD_DIR = str(Path.home() / "Downloads" / "StreamGrab")

BUILTIN_PRESETS = [
    {
        "name": "Fastest · best quality",
        "builtin": True,
        "description": "Best available video+audio, remuxed only (no re-encode) for max speed.",
        "video_quality": "best",
        "audio_quality": "best",
        "container": "mp4",
        "fast_mode": True,
    },
    {
        "name": "Archive · MKV 4K",
        "builtin": True,
        "description": "Highest quality video+audio packaged into MKV.",
        "video_quality": "2160p",
        "audio_quality": "best",
        "container": "mkv",
        "fast_mode": False,
    },
    {
        "name": "Audio only · MP3",
        "builtin": True,
        "description": "Extracts audio only as a 320kbps MP3.",
        "video_quality": "none",
        "audio_quality": "320",
        "container": "mp3",
        "fast_mode": True,
    },
    {
        "name": "Small file · 720p",
        "builtin": True,
        "description": "720p video, compact size, good for sharing.",
        "video_quality": "720p",
        "audio_quality": "128",
        "container": "mp4",
        "fast_mode": True,
    },
]


def resource_path(relative_path):
    """
    Resolve a path to a bundled resource.
    
    When running normally (python main.py):
        Returns: <project_root>/relative_path
    
    When running as a PyInstaller --onefile executable:
        PyInstaller extracts bundled files to a temporary folder stored in sys._MEIPASS.
        Returns: <temp_bundle_folder>/relative_path
    
    This allows the same code to find gui files and ffmpeg.exe regardless of how the app is run.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # Running as a bundled .exe (PyInstaller --onefile mode)
        return Path(sys._MEIPASS) / relative_path
    else:
        # Running normally from source (python main.py)
        return Path(__file__).parent / relative_path


def _ensure_config():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not PRESETS_FILE.exists():
        PRESETS_FILE.write_text(json.dumps({"custom": []}, indent=2))
    if not HISTORY_FILE.exists():
        HISTORY_FILE.write_text(json.dumps([], indent=2))
    if not SETTINGS_FILE.exists():
        SETTINGS_FILE.write_text(json.dumps({"download_dir": DEFAULT_DOWNLOAD_DIR}, indent=2))
    Path(DEFAULT_DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)


def _read_json(path, fallback):
    try:
        return json.loads(path.read_text())
    except Exception:
        return fallback


def _write_json(path, data):
    path.write_text(json.dumps(data, indent=2))


def _format_bytes(n):
    if not n:
        return "?"
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.0f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


class Api:
    """Exposed to the frontend as window.pywebview.api"""

    def __init__(self):
        _ensure_config()
        self.window = None
        self._cancel_flag = threading.Event()

    def set_window(self, window):
        self.window = window

    # ---------- settings ----------

    def get_settings(self):
        return _read_json(SETTINGS_FILE, {"download_dir": DEFAULT_DOWNLOAD_DIR})

    def choose_folder(self):
        result = self.window.create_file_dialog(webview.FOLDER_DIALOG)
        if result:
            folder = result[0]
            settings = self.get_settings()
            settings["download_dir"] = folder
            _write_json(SETTINGS_FILE, settings)
            return folder
        return None

    # ---------- presets ----------

    def get_presets(self):
        custom = _read_json(PRESETS_FILE, {"custom": []}).get("custom", [])
        return {"builtin": BUILTIN_PRESETS, "custom": custom}

    def save_preset(self, preset):
        data = _read_json(PRESETS_FILE, {"custom": []})
        custom = [p for p in data.get("custom", []) if p["name"] != preset["name"]]
        preset["builtin"] = False
        custom.append(preset)
        data["custom"] = custom
        _write_json(PRESETS_FILE, data)
        return self.get_presets()

    def delete_preset(self, name):
        data = _read_json(PRESETS_FILE, {"custom": []})
        data["custom"] = [p for p in data.get("custom", []) if p["name"] != name]
        _write_json(PRESETS_FILE, data)
        return self.get_presets()

    # ---------- history ----------

    def get_history(self):
        return _read_json(HISTORY_FILE, [])

    def _add_history(self, entry):
        history = _read_json(HISTORY_FILE, [])
        history.insert(0, entry)
        _write_json(HISTORY_FILE, history[:100])

    def clear_history(self):
        _write_json(HISTORY_FILE, [])
        return []

    def open_downloads_folder(self):
        folder = self.get_settings().get("download_dir", DEFAULT_DOWNLOAD_DIR)
        if sys.platform == "win32":
            os.startfile(folder)  # noqa
        elif sys.platform == "darwin":
            os.system(f'open "{folder}"')
        else:
            os.system(f'xdg-open "{folder}"')

    # ---------- fetch info ----------

    def fetch_info(self, url):
        ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True}
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as e:
            return {"error": str(e)}

        if "entries" in info:
            # playlist
            entries = [e for e in info["entries"] if e]
            return {
                "is_playlist": True,
                "title": info.get("title", "Playlist"),
                "count": len(entries),
                "thumbnail": (entries[0].get("thumbnail") if entries else None),
                "url": url,
            }

        formats = info.get("formats", [])
        video_heights = sorted(
            {f.get("height") for f in formats if f.get("vcodec") not in (None, "none") and f.get("height")},
            reverse=True,
        )
        audio_bitrates = sorted(
            {round(f.get("abr")) for f in formats if f.get("acodec") not in (None, "none") and f.get("abr")},
            reverse=True,
        )

        return {
            "is_playlist": False,
            "title": info.get("title"),
            "uploader": info.get("uploader"),
            "duration": info.get("duration"),
            "thumbnail": info.get("thumbnail"),
            "url": url,
            "video_qualities": [f"{h}p" for h in video_heights] or ["best"],
            "audio_qualities": [str(b) for b in audio_bitrates] or ["best"],
        }

    # ---------- download ----------

    def cancel_download(self):
        self._cancel_flag.set()

    def start_download(self, payload):
        """payload: {url, video_quality, audio_quality, container, fast_mode, is_playlist}"""
        self._cancel_flag.clear()
        thread = threading.Thread(target=self._run_download, args=(payload,), daemon=True)
        thread.start()
        return {"started": True}

    def _emit(self, event, data):
        if not self.window:
            return
        safe = json.dumps(data)
        self.window.evaluate_js(f"window.onBackendEvent('{event}', {safe})")

    def _run_download(self, payload):
        url = payload["url"]
        video_q = payload.get("video_quality", "best")
        audio_q = payload.get("audio_quality", "best")
        container = payload.get("container", "mp4")
        fast_mode = payload.get("fast_mode", False)
        download_dir = self.get_settings().get("download_dir", DEFAULT_DOWNLOAD_DIR)
        Path(download_dir).mkdir(parents=True, exist_ok=True)

        audio_only = video_q == "none" or container == "mp3"

        # Build a yt-dlp format selector string
        if audio_only:
            fmt = "bestaudio/best"
        else:
            if video_q in ("best", None):
                height_filter = ""
            else:
                height = "".join(ch for ch in video_q if ch.isdigit())
                height_filter = f"[height<={height}]" if height else ""

            if audio_q in ("best", None):
                fmt = f"bestvideo{height_filter}+bestaudio/best{height_filter}"
            else:
                fmt = f"bestvideo{height_filter}+bestaudio[abr<={audio_q}]/best{height_filter}"

        def progress_hook(d):
            if self._cancel_flag.is_set():
                raise yt_dlp.utils.DownloadError("Cancelled by user")
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes", 0)
                pct = round(downloaded / total * 100, 1) if total else 0
                self._emit("progress", {
                    "status": "downloading",
                    "percent": pct,
                    "speed": _format_bytes(d.get("speed") or 0) + "/s",
                    "eta": d.get("eta"),
                    "title": d.get("info_dict", {}).get("title", ""),
                })
            elif d["status"] == "finished":
                self._emit("progress", {"status": "merging", "percent": 99})

        ydl_opts = {
            "format": fmt,
            "outtmpl": os.path.join(download_dir, "%(title)s.%(ext)s"),
            "progress_hooks": [progress_hook],
            "quiet": True,
            "no_warnings": True,
            "noplaylist": not payload.get("is_playlist", False),
            "ffmpeg_location": str(resource_path("ffmpeg.exe")),
        }

        if audio_only:
            ydl_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": audio_q if audio_q not in ("best", None) else "320",
            }]
        elif not fast_mode:
            ydl_opts["merge_output_format"] = container
        else:
            # fast mode: prefer mp4-compatible streams so no re-encode is needed
            ydl_opts["merge_output_format"] = "mp4"

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
            title = info.get("title", url)
            self._add_history({
                "title": title,
                "url": url,
                "container": "mp3" if audio_only else container,
                "video_quality": video_q,
                "audio_quality": audio_q,
                "timestamp": time.strftime("%Y-%m-%d %H:%M"),
                "folder": download_dir,
            })
            self._emit("progress", {"status": "done", "percent": 100, "title": title})
        except Exception as e:
            self._emit("progress", {"status": "error", "message": str(e)})


def main():
    api = Api()
    gui_dir = resource_path("gui")
    window = webview.create_window(
        APP_NAME,
        str(gui_dir / "index.html"),
        js_api=api,
        width=880,
        height=760,
        min_size=(720, 620),
        background_color="#0a0e14",
        frameless=False,
        easy_drag=False,
    )
    api.set_window(window)
    webview.start(debug=False)


if __name__ == "__main__":
    main()
