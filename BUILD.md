# Building StreamGrab as a Standalone Windows Executable

This guide walks you through packaging StreamGrab into a single-file `.exe` using PyInstaller.

## Prerequisites

1. **Python 3.8+** installed
2. **Dependencies installed:**
   ```bash
   pip install -r requirements.txt
   ```
3. **FFmpeg binary** downloaded and placed in the project root (see below)

## Step 1: Download FFmpeg

StreamGrab needs FFmpeg to merge video/audio streams and convert formats. We bundle it with the app so users don't need to install it separately.

1. Visit https://www.gyan.dev/ffmpeg/builds/ or https://ffmpeg.org/download.html
2. Download the **"essentials" static build** for Windows (smallest download, ~50 MB)
3. Extract the `.zip` file
4. Copy **`ffmpeg.exe`** from the extracted folder to your project root (same folder as `main.py`)

Your project structure should now be:
```
main.py
ffmpeg.exe          ← Just added
requirements.txt
gui/
  index.html
  style.css
  app.js
```

## Step 2: Build the Executable

From your project root, run this command:

```bash
pyinstaller --onefile --windowed --add-data "gui:gui" --add-binary "ffmpeg.exe:." main.py --name StreamGrab
```

**What each flag does:**
- `--onefile` — Create a single `.exe` file (not a folder with many DLLs)
- `--windowed` — Don't show a console window when the app runs
- `--add-data "gui:gui"` — Bundle the `gui/` folder with the executable
- `--add-binary "ffmpeg.exe:."` — Bundle `ffmpeg.exe` at the root of the bundle
- `--name StreamGrab` — Name the output `.exe` as `StreamGrab.exe`

**Build output:**
After a minute or two, you'll find:
```
dist/StreamGrab.exe   ← Your standalone executable
```

## Step 3: Test the Executable

The real test: run the `.exe` from somewhere completely separate from your project folder.

1. **Copy `dist/StreamGrab.exe` to your Desktop** (or any other folder)

2. **Open a command prompt and navigate there:**
   ```bash
   cd Desktop
   ```

3. **Run the exe:**
   ```bash
   StreamGrab.exe
   ```

4. **Try these actions to verify everything works:**
   - Paste a YouTube URL and click "Fetch" → Should show video info
   - Try downloading with different quality settings → Should complete without FFmpeg errors
   - Check Settings → Open the downloads folder
   - Test History and Presets features

If all of these work, your app is truly standalone!

## Troubleshooting

### "ffmpeg not found" error during download

The bundled `ffmpeg.exe` wasn't found. Make sure:
1. You actually placed `ffmpeg.exe` in your project root before building
2. You included the `--add-binary "ffmpeg.exe:."` flag in your PyInstaller command

### "gui/index.html not found" error on startup

The `gui/` folder wasn't bundled. Make sure:
1. You included the `--add-data "gui:gui"` flag in your PyInstaller command
2. The `gui/` folder contains `index.html`, `style.css`, and `app.js`

### App crashes on startup

Check that:
1. All dependencies are installed: `pip install -r requirements.txt`
2. The build completed without errors (check the PyInstaller output log)
3. You're testing the exe from a folder outside your project directory

### File size is huge (>500 MB)

This is normal for Python apps with many dependencies. PyInstaller bundles the entire Python runtime plus all libraries. You can reduce size with UPX (advanced), but a few hundred MB is typical.

## Optional: Add a Custom Icon

If you want to customize the app icon:

1. Create or download a `.ico` file (recommended tool: https://convertio.co/png-ico/)
2. Place it in your project root as `icon.ico`
3. Add the `--icon=icon.ico` flag to your PyInstaller command:
   ```bash
   pyinstaller --onefile --windowed --icon=icon.ico --add-data "gui:gui" --add-binary "ffmpeg.exe:." main.py --name StreamGrab
   ```

## Cleaning Up After Builds

PyInstaller creates temporary files. To clean up:

```bash
rmdir /s build
rmdir /s __pycache__
del StreamGrab.spec
```

Then build again if needed.

## How the Bundling Works (Technical Details)

When you run `python main.py` normally, the app finds files relative to the script location. But PyInstaller's `--onefile` mode extracts bundled files to a temporary folder at runtime.

The `resource_path()` function in `main.py` handles this automatically:
- **In development:** Returns paths relative to `main.py`
- **In the .exe:** Returns paths relative to the temporary bundle folder (`sys._MEIPASS`)

This means the exact same code works both ways without any changes needed. The `--add-data` and `--add-binary` flags tell PyInstaller what to include in the bundle.
