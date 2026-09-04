# EchoYT

A lightweight Python CLI application that automates searching for music on YouTube, downloading high-quality audio with embedded cover art and metadata, and syncing tracks directly to your Google Drive `Music` folder, lightweight Python CLI tool that searches YouTube, downloads high-quality audio with embedded cover art, and automatically syncs your music library to Google Drive.

---

## Features

* **In-Terminal YouTube Search:** Search and preview YouTube tracks without leaving your command line using YouTube Data API v3.
* **High-Quality Audio Downloads:** Automated audio extraction converted to `.mp3` via `yt-dlp` and `ffmpeg`.
* **Embedded Cover Art & Metadata:** Automatically fetches video thumbnails, converts them, and embeds them directly into ID3 tags along with track metadata.
* **Google Drive Cloud Sync:** Authenticates safely via OAuth 2.0 to stream or organize tracks in a dedicated `Music` folder.
* **Duplicate Detection:** Queries your Google Drive storage before uploading to prevent duplicate file transfers and save space.
* **Local Space Cleanup:** Automatically cleans up local temporary MP3 files after a successful upload while keeping them safe if an upload fails.
* **Smart Tool Inspector:** Automatically checks for required tools (`yt-dlp` and `ffmpeg`) with interactive auto-installation or manual setup instructions.
* **Google OAuth Authentication:** Single sign-on for both YouTube API (`youtube.readonly`) and Google Drive integration using `credentials.json` and session caching (`token.pickle`).
* **Automated Environment Setup:** On Windows systems, missing dependencies (`yt-dlp`, `FFmpeg`, `WinFsp`, and a portable `Rclone` binary) are detected and configured automatically without manual user setup.
* **Seamless Cloud Mounting:** Automatically generates the required Rclone configuration using your existing OAuth credentials and mounts your full Google Drive root directory to drive letter **`G:`**.
* **Smart Storage Sync:** Converts downloads locally into MP3 format, moves them into your targeted cloud folder (e.g., `G:\Music`), and safely purges local temporary files only after verified transfers.
---

## Prerequisites

* **Python 3.8+**
* **Google Cloud Console Credentials:**
  1. Create a project in [Google Cloud Console](https://console.cloud.google.com/).
  2. Enable **YouTube Data API v3** and **Google Drive API**.
  3. Create **OAuth 2.0 Client ID** credentials (Desktop app) and save the file as `credentials.json` in the project root.
  4. Generate a YouTube API key and assign it to your environment/script configuration.

---

## Installation LUNIX
Prerequisites & Google API Setup
Before running EchoYT, you need to set up your own API credentials in the Google Cloud Console:

1. Enable APIs
Create a new project in Google Cloud Console.

Go to APIs & Services > Library.

Search for and enable both YouTube Data API v3 and Google Drive API.

2. Get a YouTube API Key
Go to APIs & Services > Credentials.

Click + Create Credentials > API Key.

Copy your new key, open EchoYT.py, and paste it into the YOUTUBE_API_KEY configuration variable near the top of the file:

Python
YOUTUBE_API_KEY = "YOUR_YOUTUBE_API_KEY_HERE"
3. Configure OAuth Consent & Add Yourself as a Tester
Go to APIs & Services > OAuth consent screen.

Select External and click Create.

Fill in the app name and user support email.

Under Test users, click + ADD USERS.

IMPORTANT: Enter the Google email address you plan to use with EchoYT. (Since the app is in "Testing" mode, only explicitly added test users are allowed to log in).

Save and finish.

4. Download user secrets.json
Go back to APIs & Services > Credentials.

Click + Create Credentials > OAuth client ID.

Select Desktop app as the Application type.

Download the generated JSON credentials file.

Rename the file to credentials.json and place it in the same directory as main.py.

Quick Installation
Clone the Repository:

Bash
git clone https://github.com/am0305961-eng/EchoYT.git
cd EchoYT
Install Python Dependencies:

Bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib requests
Run the Application:

Bash
python main.py

---

Streaming Cloud Music on Linux (with Rclone & Strawberry) now after you done with setting up the API and codes now you need to stream your Google Drive music library directly inside a native Linux music player without downloading local files by mounting your cloud Music folder with Rclone and playing it through Strawberry Music Player.
1. Install Rclone & Strawberry

# Ubuntu / Debian / Zorin OS
sudo apt install rclone strawberry

# Arch Linux / Hyprland
sudo pacman -S rclone strawberry

2. Configure Rclone with Your Credentials
To avoid Google security blocks and rate limits, connect Rclone using the same Client ID and Client Secret you generated for EchoYT:

3. Run the Rclone setup wizard: rclone config

4. Press n (New remote) and name it gdrive.

Select Google Drive (Option often number 18).

Paste your client_id and client_secret when prompted.

Choose scope 1 (Full access).

Press y for Auto-Config to open your browser, sign in with your Google Account, and grant permissions.

5. Create a Local Mount Point & Mount
Create a local directory for your cloud library and mount the Google Drive Music folder:

mkdir -p ~/CloudMusic
rclone mount gdrive:Music ~/CloudMusic --vfs-cache-mode full --poll-interval 10s &

6. Auto-Mount on System Boot
To keep ~/CloudMusic mounted automatically every time your PC starts:

Desktop GUI (Startup Applications): Open Startup Applications in your desktop settings, add a new entry, and set the command to:
  rclone mount gdrive:Music /home/YOUR_USERNAME/CloudMusic --vfs-cache-mode full --poll-interval 10s

7. Lastly use Strawberry Music Player To run Your Music and Enojy!

---

---
### Windows

## Prerequisites & Google Cloud Setup

EchoYT requires a Google Cloud OAuth 2.0 client ID to communicate with YouTube and Google Drive.

1. Go to the **[Google Cloud Console](https://console.cloud.google.com/)**.
2. Create a project and enable the **Google Drive API**.
3. Configure the OAuth Consent Screen and add the **`drive`** scopes.
4. Create an **OAuth 2.0 Client ID** credential (Application type: *Desktop App*).
5. Download the credentials JSON file, rename it to **`credentials.json`**, and place it directly inside the EchoYT root directory.

---

## Installation & Setup
On Windows, EchoYT manages system packages using `winget` and `pip` automatically.

1. Clone the repository and navigate into the project folder:
```cmd
git clone https://github.com/your-username/EchoYT.git
cd EchoYT

```


2. Place your downloaded **`credentials.json`** inside the folder.
3. Install Python dependencies:
```cmd
pip install -r requirements.txt

```


4. Run EchoYT:
```cmd
python echoyt.py

```


> **Note:** On first launch, EchoYT will download `yt-dlp`, install `FFmpeg` and `WinFsp` via `winget`, download portable `Rclone`, mount your Google Drive root to `G:`, and open a web browser to complete the Google OAuth login.



---

## Usage

1. Start EchoYT using the command line interface.
2. Complete the initial browser-based OAuth prompt if `token.pickle` is not present.
3. Search for a song title or paste a YouTube URL.
4. EchoYT downloads, converts, mounts `G:`, copies the file to `G:\Music`, and cleans up local temporary MP3 files upon success.

---
Mobile Playback (Android Setup)
You can automatically stream your synced Google Drive music library on your phone without manually transferring files:

Download Spiral Player from the play store (or any cloud-supported music player) from the Google Play Store on your Android device.

Open Spiral Player, go to Storage / Sources, and select Google Drive.

Sign in with the same Google Account you used for EchoYT.

Select your Music folder.

Result: Every time you download a song on your PC using EchoYT, it will instantly show up in Spiral Player on your phone ready to stream or download for offline listening!
---

Security & Privacy FAQ
Why do I need to create my own credentials.json?
EchoYT runs 100% locally on your machine. To ensure complete privacy, protect your bandwidth, and prevent API rate limiting, EchoYT uses your own personal Google Cloud API quota instead of routing your traffic through a third-party server.

Is my Google account data safe?
Zero External Data Transfer: Your credentials (credentials.json) and session tokens (token.pickle) never leave your local computer.

Minimal Permission Scopes: EchoYT only requests two specific permissions:

youtube.readonly: Read-only access to search for tracks and metadata.

drive: File operations restricted to mounting and syncing your target music folder.

Transparent Source Code: EchoYT is fully open-source. You can inspect echoyt.py directly to verify how Google OAuth authentication and API calls are handled and enjoy :3 
