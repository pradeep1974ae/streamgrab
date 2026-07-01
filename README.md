# StreamGrab

A modern desktop YouTube downloader with a premium, glowing teal-blue UI.

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## Features

- Paste a URL → auto-fetch title, thumbnail, duration, and available formats
- Video quality and audio quality selectors (populated from what the source actually offers)
- Container formats: MP4, MKV, WEBM, or MP3 (audio-only)
- Built-in presets: **Fastest · best quality**, **Archive · MKV 4K**, **Audio only · MP3**, **Small file · 720p**
- Save your own custom presets
- Playlist support
- Live download progress with speed and ETA
- Download history
- Configurable download folder

## Tech Stack

- **Backend:** Python, [yt-dlp](https://github.com/yt-dlp/yt-dlp), [pywebview](https://pywebview.flowrl.com/)
- **Frontend:** HTML, CSS, JavaScript (rendered natively via pywebview, no browser needed)

## Setup

```bash
git clone https://github.com/YOUR_USERNAME/streamgrab.git
cd streamgrab
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**FFmpeg is required** for merging video/audio streams and audio extraction. Install it and make sure it's on your PATH:
- Windows: [ffmpeg.org/download](https://ffmpeg.org/download.html)
- macOS: `brew install ffmpeg`
- Linux: `sudo apt install ffmpeg`

## Run

```bash
python main.py
```

## Build a standalone executable

```bash
pyinstaller --noconsole --onefile --add-data "gui;gui" --name StreamGrab main.py
```

(On macOS/Linux, use `--add-data "gui:gui"` — colon instead of semicolon.)

## Disclaimer

This tool is for downloading content you own or have the rights to. Respect YouTube's Terms of Service and applicable copyright law.

## License

MIT — see [LICENSE](LICENSE).
