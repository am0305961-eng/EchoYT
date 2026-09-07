# EchoYT

**YouTube → Drive Music** — a tool that searches YouTube, downloads high-quality audio (MP3) with embedded cover art and metadata, and syncs the tracks to your Google Drive `Music` folder.

No YouTube API key required.

---

## Features

* **YouTube Search without an API key:** Search is powered by `yt-dlp` — no Google Cloud API key, no quota, no signups.
* **High-Quality Audio Downloads:** Automated audio extraction converted to `.mp3` via `yt-dlp` and `ffmpeg`.
* **Embedded Cover Art & Metadata:** Automatically fetches video thumbnails, converts them, and embeds them into the MP3 ID3 tags along with track metadata.
* **Google Drive Cloud Sync:** Authenticates via OAuth 2.0 and uploads tracks to a dedicated `Music` folder in your Drive.
* **Duplicate Detection:** Checks your Drive before uploading to avoid duplicate files.
* **Local Space Cleanup:** Deletes the local MP3 after a successful upload, but keeps it if the upload fails.
* **Guided one-time setup:** If `credentials.json` is missing, the app walks you through creating it (step-by-step, opens the Google Cloud Console for you).
* **Windows GUI:** A desktop app (double-click launcher) with search box, results list, and live status log — no terminal needed.
* **Automated Environment Setup (Windows):** Missing dependencies (`yt-dlp`, `FFmpeg`, `WinFsp`, and a portable `Rclone`) are detected and configured automatically.
* **Seamless Cloud Mounting (Windows):** Mounts your Google Drive to drive letter `G:` via Rclone.

---

## Installation — Linux

### 1. Install Python tools

Ensure `yt-dlp` and `ffmpeg` are installed. The script tries to auto-install them and prints manual commands if it can't:

```bash
sudo apt install ffmpeg
python3 -m pip install yt-dlp
```

### 2. Install the Python dependencies

```bash
pip install google-api-python-client google-auth-oauthlib google-auth requests
```

### 3. Run

```bash
python3 EchoYT.py
```

On first run, if `credentials.json` is missing, the app guides you through creating it — it opens the Google Cloud Console and gives you numbered steps. You only do this once; afterward it stays logged in via `token.pickle`.

---

## Installation — Windows

1. Install **Python 3.10+** from [python.org](https://www.python.org/downloads/). **Tick "Add Python to PATH" during install.**
2. Unzip/clone this repository.
3. Double-click **`Start EchoYT.bat`**.

That's it. The launcher:
- checks Python is installed,
- installs the required libraries on first run,
- launches the EchoYT **GUI** (no console window).

If anything goes wrong, double-click **`Start EchoYT (console).bat`** instead — it keeps the console open so you can see/share the error.

On first launch the app prompts for `credentials.json` (same guided flow as Linux), then opens a browser to authorize your Google Drive.

---

## How the Google Drive login works

EchoYT uses Google OAuth 2.0 (Desktop app flow):

1. You need a `credentials.json` (your app's client ID/secret) — **the app guides you through creating it** if it's missing.
2. The first time you run it, a browser opens asking you to sign in to Google and allow access.
3. The script saves a `token.pickle` so you don't re-login every time.

> ⚠️ **Never share `credentials.json` or `token.pickle`.** They identify your app and grant access to your Google account. Both are gitignored. If you ever shared one, regenerate the credentials in the Google Cloud Console and delete the old files.

---

## Usage

1. Start EchoYT (Linux: `python3 EchoYT.py` / Windows: double-click `Start EchoYT.bat`).
2. Type a song name and search.
3. Select a result.
4. EchoYT downloads it as a tagged MP3, checks for duplicates on Drive, uploads it to your `Music` folder, and deletes the local copy.

---

## Stream your synced library on your phone

1. Install **Spiral Player** (or any Google-Drive-compatible player) from the Play Store.
2. Open it, go to **Storage/Sources** → **Google Drive**, sign in with the same account.
3. Select your **Music** folder.

Every song you download with EchoYT shows up on your phone instantly, ready to stream or download for offline listening.