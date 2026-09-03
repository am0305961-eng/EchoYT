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

---

## Prerequisites

* **Python 3.8+**
* **Google Cloud Console Credentials:**
  1. Create a project in [Google Cloud Console](https://console.cloud.google.com/).
  2. Enable **YouTube Data API v3** and **Google Drive API**.
  3. Create **OAuth 2.0 Client ID** credentials (Desktop app) and save the file as `credentials.json` in the project root.
  4. Generate a YouTube API key and assign it to your environment/script configuration.

---

## Installation

1. **Clone the Repository:**
   ```bash
   git clone [https://github.com/your-username/EchoYT.git](https://github.com/your-username/EchoYT.git)
   cd EchoYT
