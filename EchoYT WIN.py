import gc
import importlib.util
import json
import os
import pickle
import platform
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import requests
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Force UTF-8 terminal output for Windows compatibility
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

SCRIPT_DIR = Path(__file__).parent.resolve()

# Scopes covering both Google Drive and YouTube Read-Only Access
SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/youtube.readonly"
]

SEARCH_RESULTS = 5
DRIVE_FOLDER_NAME = "Music"


# ============================================================
# TOOLS CHECK & AUTOMATED SETUP
# ============================================================

def check_tools():
    """Check and auto-install yt-dlp, FFmpeg, WinFsp, and Rclone."""
    missing = []

    yt_dlp_ok = importlib.util.find_spec("yt_dlp") is not None
    if not yt_dlp_ok:
        missing.append("yt-dlp")

    ffmpeg_ok = shutil.which("ffmpeg") is not None
    if not ffmpeg_ok:
        missing.append("ffmpeg")

    rclone_exe = SCRIPT_DIR / "rclone.exe"
    rclone_ok = rclone_exe.exists() or (shutil.which("rclone") is not None)

    if yt_dlp_ok and ffmpeg_ok and rclone_ok:
        print("✓ yt-dlp installed")
        print("✓ ffmpeg installed")
        print("✓ rclone installed")
        return True

    print("\nMissing or unconfigured tools detected. Setting up dependencies...")

    if platform.system() == "Windows":
        # 1. Install yt-dlp via pip
        if not yt_dlp_ok:
            print("Installing yt-dlp via pip...")
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", "yt-dlp"], check=True)
                print("✓ yt-dlp installed.")
            except subprocess.CalledProcessError:
                print("Failed to install yt-dlp via pip.")

        # 2. Install FFmpeg via winget
        if not ffmpeg_ok and shutil.which("winget"):
            print("Installing FFmpeg via winget...")
            try:
                subprocess.run(
                    ["winget", "install", "Gyan.FFmpeg", "--accept-source-agreements", "--accept-package-agreements"],
                    check=True
                )
                print("✓ FFmpeg installed.")
            except subprocess.CalledProcessError:
                print("Failed to auto-install FFmpeg via winget.")

        # 3. Install WinFsp (Required for mounting drives on Windows)
        if shutil.which("winget"):
            print("Ensuring WinFsp is installed for drive mounting...")
            try:
                subprocess.run(
                    ["winget", "install", "WinFsp.WinFsp", "--accept-source-agreements", "--accept-package-agreements"],
                    check=False
                )
            except Exception:
                pass

        # 4. Download portable Rclone if missing
        if not rclone_ok:
            print("Downloading portable Rclone for Windows...")
            rclone_url = "https://downloads.rclone.org/rclone-current-windows-amd64.zip"
            zip_path = SCRIPT_DIR / "rclone.zip"
            
            res = requests.get(rclone_url, stream=True)
            with open(zip_path, "wb") as f:
                f.write(res.content)

            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                for file_info in zip_ref.infolist():
                    if file_info.filename.endswith("rclone.exe"):
                        file_info.filename = "rclone.exe"
                        zip_ref.extract(file_info, SCRIPT_DIR)
                        break

            zip_path.unlink(missing_ok=True)
            print("✓ Portable Rclone configured.")

    return True


# ============================================================
# GOOGLE OAUTH AUTHENTICATION (DRIVE & YOUTUBE)
# ============================================================

def authenticate_google():
    """Authenticate with Google OAuth 2.0 separately for Drive and YouTube
    to prevent scope incompatibility errors (Error 400).
    """
    creds_path = SCRIPT_DIR / "credentials.json"
    token_path = SCRIPT_DIR / "token.pickle"

    creds = None

    # Step 1: Check existing session token
    if token_path.exists():
        try:
            with open(token_path, "rb") as token:
                creds = pickle.load(token)
        except Exception:
            creds = None

    # Step 2: Refresh token in background if expired
    if creds and creds.expired and creds.refresh_token:
        print("Refreshing session in background...")
        try:
            creds.refresh(Request())
            with open(token_path, "wb") as token:
                pickle.dump(creds, token)
        except Exception as e:
            print(f"Failed to refresh token: {e}")
            creds = None

    # Step 3: Authenticate separately if credentials are missing/invalid
    if not creds or not creds.valid:
        if not creds_path.exists():
            print(f"\nERROR: credentials.json was not found at {creds_path}!")
            return None, None

        # 1. Drive Authentication
        print("\n[1/2] Authorizing Google Drive access...")
        flow_drive = InstalledAppFlow.from_client_secrets_file(
            str(creds_path), 
            scopes=["https://www.googleapis.com/auth/drive.file"]
        )
        creds_drive = flow_drive.run_local_server(port=8080, prompt="consent")

        # 2. YouTube Authentication
        print("\n[2/2] Authorizing YouTube access...")
        flow_yt = InstalledAppFlow.from_client_secrets_file(
            str(creds_path), 
            scopes=["https://www.googleapis.com/auth/youtube.readonly"]
        )
        creds_yt = flow_yt.run_local_server(port=8081, prompt="consent")

        # 3. Combine credentials for the session
        creds = creds_drive
        # Inject the secondary YouTube token scope into the session credentials
        drive_service = build("drive", "v3", credentials=creds_drive)
        youtube_service = build("youtube", "v3", credentials=creds_yt)

        # Save drive credentials as primary
        with open(token_path, "wb") as token:
            pickle.dump({"drive": creds_drive, "youtube": creds_yt}, token)
            print("\nSession saved successfully!")
            
        return drive_service, youtube_service

    # Handle loading combined token dict if saved previously
    if isinstance(creds, dict):
        drive_service = build("drive", "v3", credentials=creds["drive"])
        youtube_service = build("youtube", "v3", credentials=creds["youtube"])
    else:
        drive_service = build("drive", "v3", credentials=creds)
        youtube_service = build("youtube", "v3", credentials=creds)

    return drive_service, youtube_service


# ============================================================
# RCLONE AUTOMATED CONFIGURATION & MOUNT
# ============================================================

def setup_and_mount_rclone(drive_letter="G"):
    """Auto-configures Rclone using Google OAuth token and mounts Drive as a local Windows drive.
    Skips completely if drive is already mounted.
    """
    target_drive = f"{drive_letter}:"

    # Skip if drive is already mounted
    if os.path.exists(target_drive):
        print(f"✓ Drive {target_drive} is already mounted. Skipping mount step.")
        return

    rclone_bin = SCRIPT_DIR / "rclone.exe"
    if not rclone_bin.exists():
        rclone_bin = shutil.which("rclone")
        if not rclone_bin:
            print("Rclone executable not found. Skipping auto-mount.")
            return

    token_path = SCRIPT_DIR / "token.pickle"
    creds_path = SCRIPT_DIR / "credentials.json"

    if not (token_path.exists() and creds_path.exists()):
        print("Missing credentials/token for Rclone setup.")
        return

    # Extract credentials for Rclone configuration
    with open(creds_path, "r") as f:
        creds_data = json.load(f).get("installed", {})

    with open(token_path, "rb") as f:
        creds = pickle.load(f)

    client_id = creds_data.get("client_id", "")
    client_secret = creds_data.get("client_secret", "")
    
    token_json = json.dumps({
        "access_token": creds.token,
        "token_type": "Bearer",
        "refresh_token": creds.refresh_token,
        "expiry": creds.expiry.isoformat() + "Z" if creds.expiry else ""
    })

    remote_name = "gdrive"
    print("\nConfiguring Rclone remote...")

    subprocess.run([
        str(rclone_bin), "config", "create", remote_name, "drive",
        f"client_id={client_id}",
        f"client_secret={client_secret}",
        f"token={token_json}",
        "scope=drive.file"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print(f"Mounting Google Drive to {target_drive} in background...")

    CREATE_NO_WINDOW = 0x08000000
    subprocess.Popen([
        str(rclone_bin), "mount", f"{remote_name}:", f"{drive_letter}:",
        "--vfs-cache-mode", "full"
    ], creationflags=CREATE_NO_WINDOW)

    print(f"✓ Google Drive mounted successfully to local drive {target_drive}\\!")


def get_drive_music_folder(service):
    """Find the Music folder or create it."""
    query = (
        f"name = '{DRIVE_FOLDER_NAME}' "
        f"and mimeType = 'application/vnd.google-apps.folder' "
        f"and trashed = false"
    )

    results = service.files().list(q=query, spaces="drive", fields="files(id, name)").execute()
    folders = results.get("files", [])

    if folders:
        print("Found Google Drive Music folder.")
        return folders[0]["id"]

    folder_metadata = {
        "name": DRIVE_FOLDER_NAME,
        "mimeType": "application/vnd.google-apps.folder"
    }

    folder = service.files().create(body=folder_metadata, fields="id").execute()
    print("Created Google Drive Music folder.")
    return folder["id"]


# ============================================================
# YOUTUBE SEARCH & DOWNLOAD
# ============================================================

def search_youtube(youtube_service):
    """Search YouTube using authenticated OAuth client and let the user choose a video."""
    query = input("\nEnter the song/video name: ").strip()

    if not query:
        print("Search can't be empty!")
        return None

    try:
        request = youtube_service.search().list(
            q=query,
            part="snippet",
            type="video",
            maxResults=SEARCH_RESULTS
        )
        response = request.execute()
    except Exception as e:
        print(f"YouTube search error: {e}")
        return None

    items = response.get("items", [])

    if not items:
        print("No results found.")
        return None

    videos = {}
    print("\nResults:\n")

    for i, item in enumerate(items, start=1):
        video_id = item["id"]["videoId"]
        title = item["snippet"]["title"]
        url = f"https://www.youtube.com/watch?v={video_id}"

        videos[i] = {"title": title, "url": url}
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


def download_song(url):
    """Download a YouTube video as MP3 with metadata embedded."""
    music_dir = Path.home() / "Music"
    music_dir.mkdir(parents=True, exist_ok=True)

    output_template = str(music_dir / "%(title)s.%(ext)s")

    command = [
        sys.executable, "-m", "yt_dlp",
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "0",
        "--write-thumbnail",
        "--convert-thumbnails", "jpg",
        "--embed-thumbnail",
        "--add-metadata",
        "-o", output_template,
        url
    ]

    print("\nDownloading song, cover art, and embedding metadata...")
    print("Please wait...\n")

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError:
        print("\n[ERROR] Download or conversion failed! Make sure FFmpeg is installed.")
        return None
    except FileNotFoundError:
        print("\n[ERROR] Python interpreter or module path not found.")
        return None

    mp3_files = list(music_dir.glob("*.mp3"))
    if not mp3_files:
        print("Download finished, but MP3 wasn't found.")
        return None

    newest_file = max(mp3_files, key=lambda file: file.stat().st_mtime)
    print(f"Downloaded & Tagged: {newest_file.name}")
    return newest_file


def find_file_on_drive(service, folder_id, filename):
    """Check whether a file already exists in Drive."""
    safe_filename = filename.replace("'", "\\'")
    query = (
        f"name = '{safe_filename}' "
        f"and '{folder_id}' in parents "
        f"and trashed = false"
    )

    results = service.files().list(q=query, spaces="drive", fields="files(id, name)").execute()
    files = results.get("files", [])
    return files[0] if files else None


def upload_file(service, file_path, folder_id):
    """Upload a file to Google Drive."""
    file_metadata = {"name": file_path.name, "parents": [folder_id]}
    media = MediaFileUpload(str(file_path), mimetype="audio/mpeg", resumable=True)
    return service.files().create(body=file_metadata, media_body=media, fields="id, name").execute()


# ============================================================
# MAIN
# ============================================================

def main():
    print("================================")
    print("      YouTube → Drive Music     ")
    print("================================")

    # 1. System tool verification & installation
    check_tools()

    # 2. Authenticate Google APIs (Drive + YouTube) using token.pickle if available
    drive_service, youtube_service = authenticate_google()
    if drive_service is None or youtube_service is None:
        return

    # 3. Mount Google Drive locally using Rclone (Skips if G: drive already exists)
    setup_and_mount_rclone(drive_letter="G")

    # 4. Fetch/Create Drive destination folder
    drive_folder_id = get_drive_music_folder(drive_service)

    # 5. Search YouTube via OAuth client
    video = search_youtube(youtube_service)
    if video is None:
        return

    print(f"\nSelected: {video['title']}")

    # 6. Download track locally
    local_file = download_song(video["url"])
    if local_file is None:
        return

    # 7. Check duplicates on Google Drive
    print("\nChecking Google Drive...")
    existing_file = find_file_on_drive(drive_service, drive_folder_id, local_file.name)

    if existing_file:
        print(f"Already exists on Drive: {existing_file['name']}")
        print("Deleting local copy...")
        gc.collect()
        try:
            local_file.unlink()
        except OSError as e:
            print(f"Couldn't remove local file: {e}")
        print("Done! No duplicate uploaded.")
        return

    # 8. Upload file to Google Drive
    print("\nUploading to Google Drive...")
    try:
        uploaded = upload_file(drive_service, local_file, drive_folder_id)
        print(f"Uploaded successfully: {uploaded['name']}")
    except Exception as e:
        print("\nUpload failed!")
        print(e)
        print("\nThe local MP3 was kept so you don't lose it.")
        return

    # 9. Clean up local copy
    print("\nDeleting local MP3...")
    gc.collect()
    try:
        local_file.unlink()
        print("Local file deleted.")
    except Exception as e:
        print(f"Couldn't delete local file: {e}")

    print("\n================================")
    print("             DONE!              ")
    print("================================")


if __name__ == "__main__":
    main()