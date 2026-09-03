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
