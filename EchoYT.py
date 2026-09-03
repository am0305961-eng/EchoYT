import os
import pickle
import subprocess
import shutil
import sys

from pathlib import Path

import requests
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

#============================================================
# TOOLS CHECK
# ============================================================
def detect_package_manager():
    """Detect the system's package manager."""
    if shutil.which("apt"):
        return "apt", ["sudo", "apt", "update"], ["sudo", "apt", "install", "-y", "ffmpeg"]
    elif shutil.which("pacman"):
        return "pacman", [], ["sudo", "pacman", "-S", "--noconfirm", "ffmpeg"]
    elif shutil.which("dnf"):
        return "dnf", [], ["sudo", "dnf", "install", "-y", "ffmpeg"]
    elif shutil.which("zypper"):
        return "zypper", [], ["sudo", "zypper", "install", "-y", "ffmpeg"]
    return None, [], []


def check_tools():
    """Check for yt-dlp and ffmpeg, with interactive installation options."""
    missing = []

    if not shutil.which("yt-dlp"):
        missing.append("yt-dlp")

    if not shutil.which("ffmpeg"):
        missing.append("ffmpeg")

    if not missing:
        print("✓ yt-dlp")
        print("✓ ffmpeg")
        return True

    print("\nMissing tools detected:")
    for tool in missing:
        print(f"  ✗ {tool}")

    pkg_mgr, update_cmd, install_cmd = detect_package_manager()

    print("\nHow would you like to install the missing tools?")
    print("1. Try auto-installing via script (may prompt for sudo password)")
    print("2. I will run the commands manually in terminal")

    choice = input("\nEnter your choice (1/2): ").strip()

    if choice == "1":
        print("\nStarting installation process...")

        # 1. Install ffmpeg via system package manager if missing
        if "ffmpeg" in missing:
            if install_cmd:
                try:
                    if update_cmd:
                        subprocess.run(update_cmd, check=True)
                    subprocess.run(install_cmd, check=True)
                    print("✓ Installed ffmpeg successfully.")
                except subprocess.CalledProcessError:
                    print("✗ Failed to install ffmpeg automatically.")
            else:
                print("Could not detect package manager. Please install ffmpeg manually.")

        # 2. Install yt-dlp via pip/pipx or download binary if missing
        if "yt-dlp" in missing:
            yt_dlp_installed = False

            # Try pip/pipx
            if shutil.which("pip") or shutil.which("pip3"):
                pip_cmd = [sys.executable, "-m", "pip", "install", "yt-dlp"]
                try:
                    subprocess.run(pip_cmd, check=True)
                    yt_dlp_installed = True
                    print("✓ Installed yt-dlp successfully via pip.")
                except subprocess.CalledProcessError:
                    pass

            # Fallback for Linux binary download if pip failed/absent
            if not yt_dlp_installed:
                try:
                    binary_url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"
                    target_path = "/usr/local/bin/yt-dlp"
                    print(f"Downloading yt-dlp binary to {target_path} (requires sudo)...")
                    curl_cmd = ["sudo", "curl", "-L", binary_url, "-o", target_path]
                    chmod_cmd = ["sudo", "chmod", "a+rx", target_path]
                    
                    subprocess.run(curl_cmd, check=True)
                    subprocess.run(chmod_cmd, check=True)
                    yt_dlp_installed = True
                    print("✓ Installed yt-dlp successfully.")
                except subprocess.CalledProcessError:
                    print("✗ Failed to download yt-dlp.")

        # Re-check after attempting auto-install
        if shutil.which("yt-dlp") and shutil.which("ffmpeg"):
            print("\nAll missing tools were successfully installed!")
            return True
        else:
            print("\nSome tools could not be installed automatically.")

    # Option 2 or Fallback instructions
    print("\n--- Manual Installation Commands ---")
    if "ffmpeg" in missing:
        if pkg_mgr == "apt":
            print("  ffmpeg: sudo apt update && sudo apt install ffmpeg")
        elif pkg_mgr == "pacman":
            print("  ffmpeg: sudo pacman -S ffmpeg")
        elif pkg_mgr == "dnf":
            print("  ffmpeg: sudo dnf install ffmpeg")
        else:
            print("  ffmpeg: Install via your distribution's package manager")

    if "yt-dlp" in missing:
        print("  yt-dlp: pip install yt-dlp   OR   sudo curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp && sudo chmod a+rx /usr/local/bin/yt-dlp")

    print("\nPlease run the commands above in your terminal and rerun this script.")
    return False


if not check_tools():
    sys.exit(1)



# ============================================================
# CONFIG
# ============================================================

YOUTUBE_API_KEY = "PUT YOUR API HERE"

SEARCH_RESULTS = 5

DRIVE_FOLDER_NAME = "Music"

SCOPES = [
    "https://www.googleapis.com/auth/drive.file"
]


# ============================================================
# GOOGLE DRIVE AUTHENTICATION
# ============================================================

def authenticate_drive():
    """Authenticate with Google Drive."""

    creds = None

    # Reuse previous login
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)

    # Refresh expired credentials
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    # First login
    if not creds or not creds.valid:

        if not os.path.exists("credentials.json"):
            print("\nERROR: credentials.json was not found!")
            print("Put credentials.json next to this Python file.")
            return None

        flow = InstalledAppFlow.from_client_secrets_file(
            "credentials.json",
            SCOPES
        )

        creds = flow.run_local_server(port=0)

        # Save login for next time
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

    print("Google Drive authentication successful!")

    return build(
        "drive",
        "v3",
        credentials=creds
    )


# ============================================================
# GOOGLE DRIVE MUSIC FOLDER
# ============================================================

def get_drive_music_folder(service):
    """Find the Music folder or create it."""

    query = (
        f"name = '{DRIVE_FOLDER_NAME}' "
        f"and mimeType = 'application/vnd.google-apps.folder' "
        f"and trashed = false"
    )

    results = service.files().list(
        q=query,
        spaces="drive",
        fields="files(id, name)"
    ).execute()

    folders = results.get("files", [])

    if folders:
        print("Found Google Drive Music folder.")
        return folders[0]["id"]

    # Folder doesn't exist → create it
    folder_metadata = {
        "name": DRIVE_FOLDER_NAME,
        "mimeType": "application/vnd.google-apps.folder"
    }

    folder = service.files().create(
        body=folder_metadata,
        fields="id"
    ).execute()

    print("Created Google Drive Music folder.")

    return folder["id"]


# ============================================================
# YOUTUBE SEARCH
# ============================================================

def search_youtube():
    """Search YouTube and let the user choose a video."""

    query = input("\nEnter the song/video name: ").strip()

    if not query:
        print("Search can't be empty!")
        return None

    params = {
        "key": YOUTUBE_API_KEY,
        "q": query,
        "part": "snippet",
        "type": "video",
        "maxResults": SEARCH_RESULTS
    }

    response = requests.get(
        "https://www.googleapis.com/youtube/v3/search",
        params=params
    )

    if response.status_code != 200:
        print("YouTube API error:")
        print(response.text)
        return None

    data = response.json()

    items = data.get("items", [])

    if not items:
        print("No results found.")
        return None

    videos = {}

    print("\nResults:\n")

    for i, item in enumerate(items, start=1):

        video_id = item["id"]["videoId"]
        title = item["snippet"]["title"]

        url = f"https://www.youtube.com/watch?v={video_id}"

        videos[i] = {
            "title": title,
            "url": url
        }

        print(f"{i}. {title}")
        print(f"   {url}\n")

    while True:

        try:
            choice = int(input("Choose the video: "))

            if choice in videos:
                return videos[choice]

            print(f"Please choose a number from 1-{len(videos)}.")

        except ValueError:
            print("Please enter a number.")


# ============================================================
# DOWNLOAD
# ============================================================

def download_song(url):
    """Download a YouTube video as MP3 with thumbnail metadata embedded."""

    music_dir = Path.home() / "Music"

    # Create ~/Music if it doesn't exist
    music_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    output_template = str(
        music_dir / "%(title)s.%(ext)s"
    )

    command = [
        "yt-dlp",

        "--extract-audio",
        "--audio-format",
        "mp3",
        "--audio-quality",
        "0",

        # --- COVER ART & METADATA ---
        "--write-thumbnail",        # Fetch the video thumbnail
        "--convert-thumbnails", "jpg", # Convert thumbnail to JPG format
        "--embed-thumbnail",        # Embed thumbnail into the MP3 ID3 tag
        "--add-metadata",           # Embed title/artist metadata into the file
        # ----------------------------------------

        "-o",
        output_template,

        url
    ]

    print("\nDownloading song, cover art, and embedding metadata...")
    print("Please wait...\n")

    try:
        subprocess.run(
            command,
            check=True
        )

    except subprocess.CalledProcessError:
        print("\nDownload failed.")
        return None

    except FileNotFoundError:
        print("\nyt-dlp was not found!")
        print("Make sure yt-dlp and ffmpeg are installed.")
        return None

    # Find the newest MP3 in Music
    mp3_files = list(
        music_dir.glob("*.mp3")
    )

    if not mp3_files:
        print("Download finished, but MP3 wasn't found.")
        return None

    newest_file = max(
        mp3_files,
        key=lambda file: file.stat().st_mtime
    )

    print(f"Downloaded & Tagged: {newest_file.name}")

    return newest_file

# ============================================================
# CHECK IF FILE ALREADY EXISTS ON GOOGLE DRIVE
# ============================================================

def find_file_on_drive(
    service,
    folder_id,
    filename
):
    """Check whether a file already exists in Drive."""

    # Escape apostrophes for Drive query
    safe_filename = filename.replace("'", "\\'")

    query = (
        f"name = '{safe_filename}' "
        f"and '{folder_id}' in parents "
        f"and trashed = false"
    )

    results = service.files().list(
        q=query,
        spaces="drive",
        fields="files(id, name)"
    ).execute()

    files = results.get("files", [])

    if files:
        return files[0]

    return None


# ============================================================
# UPLOAD
# ============================================================

def upload_file(
    service,
    file_path,
    folder_id
):
    """Upload a file to Google Drive."""

    file_metadata = {
        "name": file_path.name,
        "parents": [folder_id]
    }

    media = MediaFileUpload(
        str(file_path),
        resumable=True
    )

    uploaded = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, name"
    ).execute()

    return uploaded


# ============================================================
# MAIN
# ============================================================

def main():

    print("================================")
    print("      YouTube → Drive Music")
    print("================================")

    # --------------------------------------------------------
    # Authenticate
    # --------------------------------------------------------

    service = authenticate_drive()

    if service is None:
        return

    # --------------------------------------------------------
    # Get Drive Music folder
    # --------------------------------------------------------

    drive_folder_id = get_drive_music_folder(
        service
    )

    # --------------------------------------------------------
    # Search YouTube
    # --------------------------------------------------------

    video = search_youtube()

    if video is None:
        return

    print(f"\nSelected: {video['title']}")

    # --------------------------------------------------------
    # Download
    # --------------------------------------------------------

    local_file = download_song(
        video["url"]
    )

    if local_file is None:
        return

    # --------------------------------------------------------
    # Check Drive for duplicate
    # --------------------------------------------------------

    print("\nChecking Google Drive...")

    existing_file = find_file_on_drive(
        service,
        drive_folder_id,
        local_file.name
    )

    if existing_file:

        print(
            f"Already exists on Drive: "
            f"{existing_file['name']}"
        )

        print("Deleting local copy...")

        local_file.unlink()

        print("Done! No duplicate uploaded.")
        return

    # --------------------------------------------------------
    # Upload
    # --------------------------------------------------------

    print("\nUploading to Google Drive...")

    try:

        uploaded = upload_file(
            service,
            local_file,
            drive_folder_id
        )

        print(
            f"Uploaded successfully: "
            f"{uploaded['name']}"
        )

    except Exception as e:

        print("\nUpload failed!")
        print(e)

        # IMPORTANT:
        # Don't delete the local file if upload failed.
        print(
            "\nThe local MP3 was kept so "
            "you don't lose it."
        )

        return

    # --------------------------------------------------------
    # Delete local copy
    # --------------------------------------------------------

    print("\nDeleting local MP3...")

    try:
        local_file.unlink()
        print("Local file deleted.")

    except Exception as e:
        print(f"Couldn't delete local file: {e}")

    print("\n================================")
    print("             DONE!")
    print("================================")


if __name__ == "__main__":
    main()
