import gc
import importlib.util
import json
import os
import pickle
import platform
import queue
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import webbrowser
import zipfile
from pathlib import Path

import requests
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Force UTF-8 terminal output for Windows compatibility
if sys.platform == "win32":
    # Allow running with pythonw.exe (no console): sys.stdout/stderr are None
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).parent.resolve()

# Scopes covering Google Drive upload + mount
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

SEARCH_RESULTS = 5
DRIVE_FOLDER_NAME = "Music"

CREDENTIALS_PATH = SCRIPT_DIR / "credentials.json"
TOKEN_PATH = SCRIPT_DIR / "token.pickle"


# ============================================================
# TOOLS CHECK & AUTOMATED SETUP
# ============================================================

def check_tools(log):
    """Check and auto-install yt-dlp, FFmpeg, WinFsp, and Rclone."""
    log("Checking required tools...")

    yt_dlp_ok = importlib.util.find_spec("yt_dlp") is not None
    if not yt_dlp_ok:
        log("- yt-dlp missing")

    ffmpeg_ok = shutil.which("ffmpeg") is not None
    if not ffmpeg_ok:
        log("- ffmpeg missing")

    rclone_exe = SCRIPT_DIR / "rclone.exe"
    rclone_ok = rclone_exe.exists() or (shutil.which("rclone") is not None)
    if not rclone_ok:
        log("- rclone missing")

    if yt_dlp_ok and ffmpeg_ok and rclone_ok:
        log("OK: yt-dlp, ffmpeg, rclone all present.")
        return True

    log("Installing/setting up missing tools...")

    if platform.system() == "Windows":
        if not yt_dlp_ok:
            log("Installing yt-dlp via pip...")
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", "yt-dlp"], check=True)
                log("OK: yt-dlp installed.")
            except subprocess.CalledProcessError:
                log("FAILED to install yt-dlp via pip.")

        if not ffmpeg_ok and shutil.which("winget"):
            log("Installing FFmpeg via winget...")
            try:
                subprocess.run(
                    ["winget", "install", "Gyan.FFmpeg", "--accept-source-agreements", "--accept-package-agreements"],
                    check=True
                )
                log("OK: FFmpeg installed.")
            except subprocess.CalledProcessError:
                log("FAILED to auto-install FFmpeg via winget.")

        if shutil.which("winget"):
            log("Ensuring WinFsp is installed for drive mounting...")
            try:
                subprocess.run(
                    ["winget", "install", "WinFsp.WinFsp", "--accept-source-agreements", "--accept-package-agreements"],
                    check=False
                )
            except Exception:
                pass

        if not rclone_ok:
            log("Downloading portable Rclone for Windows...")
            rclone_url = "https://downloads.rclone.org/rclone-current-windows-amd64.zip"
            zip_path = SCRIPT_DIR / "rclone.zip"
            try:
                res = requests.get(rclone_url, stream=True, timeout=120)
                with open(zip_path, "wb") as f:
                    f.write(res.content)
                with zipfile.ZipFile(zip_path, "r") as zip_ref:
                    for file_info in zip_ref.infolist():
                        if file_info.filename.endswith("rclone.exe"):
                            file_info.filename = "rclone.exe"
                            zip_ref.extract(file_info, SCRIPT_DIR)
                            break
                zip_path.unlink(missing_ok=True)
                log("OK: Portable Rclone configured.")
            except Exception as e:
                log(f"FAILED to download rclone: {e}")
    return True


# ============================================================
# GOOGLE DRIVE AUTHENTICATION
# ============================================================

def open_browser(url):
    """Try to open a URL in the default browser."""
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"Could not open browser automatically: {e}\nOpen manually: {url}")


def guide_credentials_setup(root=None):
    """Show interactive guide for creating credentials.json.

    Uses a Tk dialog if a root is available (GUI mode), else console prompts.
    """
    steps = [
        "1. Open the Google Cloud Console link (below).",
        "2. Sign in with your Google account.",
        "3. If it asks you to create a project, click ACCEPT / CREATE.",
        "4. Go to 'APIs & Services' -> 'Enabled APIs & services'.",
        "5. Click '+ ENABLE APIS AND SERVICES'.",
        "6. Search for 'Google Drive API' and click it.",
        "7. Click 'ENABLE'.",
        "8. Go back to 'APIs & Services' -> 'Credentials'.",
        "9. Click '+ CREATE CREDENTIALS', then 'OAuth client ID'.",
        "10. For 'Application type' choose 'Desktop app'.",
        "11. Click 'CREATE'.",
        "12. Click 'DOWNLOAD JSON'.",
        "13. Save the downloaded file as  credentials.json",
        "     in the app folder, then click OK here.",
    ]

    if root is not None:
        # GUI mode
        messagebox.showinfo(
            "Google Drive Setup Needed",
            "This app needs credentials.json to upload to YOUR Drive.\n\n"
            "It is a small file that identifies the app to Google.\n"
            "You only do this ONCE.\n\n"
            "Click OK and follow the steps in the next window."
        )
        open_browser("https://console.cloud.google.com/welcome")
        text = "\n".join(steps)
        messagebox.showinfo("Steps - create credentials.json", text)
        return os.path.exists(CREDENTIALS_PATH)

    # Console mode (fallback)
    print("\n" + "=" * 60)
    print("  GOOGLE DRIVE SETUP NEEDED (one time)")
    print("=" * 60)
    for s in steps:
        print(s)
    print("\nOpening Google Cloud Console in your browser...")
    open_browser("https://console.cloud.google.com/welcome")
    try:
        input("\n[Press Enter once you've saved the file] ")
    except (EOFError, OSError):
        pass
    return os.path.exists(CREDENTIALS_PATH)


def authenticate_drive():
    """Authenticate with Google Drive, with guided setup if needed."""
    creds = None

    if os.path.exists(TOKEN_PATH):
        try:
            with open(TOKEN_PATH, "rb") as token:
                creds = pickle.load(token)
        except Exception:
            creds = None

    if creds and creds.expired and creds.refresh_token:
        print("Refreshing session...")
        try:
            creds.refresh(Request())
            with open(TOKEN_PATH, "wb") as token:
                pickle.dump(creds, token)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        while not os.path.exists(CREDENTIALS_PATH):
            print("\nERROR: credentials.json was not found!")
            print(f"Expected at: {CREDENTIALS_PATH}\n")
            if not guide_credentials_setup():
                print("credentials.json still not found. Please re-run and try again.")
                return None

        print("\nOpening browser to authorize Google Drive access...")
        flow = InstalledAppFlow.from_client_secrets_file(
            str(CREDENTIALS_PATH),
            SCOPES
        )
        creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, "wb") as token:
            pickle.dump(creds, token)

    print("Google Drive authentication successful!")
    service = build("drive", "v3", credentials=creds)
    return service


# ============================================================
# RCLONE MOUNT
# ============================================================

def setup_and_mount_rclone(drive_letter="G"):
    """Auto-configures Rclone using Google OAuth token and mounts Drive locally."""
    target_drive = f"{drive_letter}:"

    if os.path.exists(target_drive):
        print(f"OK: Drive {target_drive} is already mounted. Skipping mount step.")
        return

    rclone_bin = SCRIPT_DIR / "rclone.exe"
    if not rclone_bin.exists():
        rclone_bin = shutil.which("rclone")
        if not rclone_bin:
            print("Rclone executable not found. Skipping auto-mount.")
            return

    if not (TOKEN_PATH.exists() and CREDENTIALS_PATH.exists()):
        print("Missing credentials/token for Rclone setup.")
        return

    with open(CREDENTIALS_PATH, "r") as f:
        creds_data = json.load(f).get("installed", {})

    with open(TOKEN_PATH, "rb") as f:
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
    print("Configuring Rclone remote...")

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

    print(f"OK: Google Drive mounted to local drive {target_drive}\\!")


# ============================================================
# DRIVE FOLDER HELPERS
# ============================================================

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
# YOUTUBE SEARCH (yt-dlp, no API key)
# ============================================================

def search_youtube(query):
    """Search YouTube using yt-dlp (no API key / no OAuth)."""
    import json as _json
    search_url = f"ytsearch{SEARCH_RESULTS}:{query}"

    try:
        result = subprocess.run(
            [sys.executable, "-m", "yt_dlp",
             "--flat-playlist", "--dump-json", "--no-warnings",
             "--playlist-end", str(SEARCH_RESULTS), search_url],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
    except FileNotFoundError:
        print("yt-dlp was not found! Make sure it is installed.")
        return []

    if result.returncode != 0:
        print("Search failed (network issue or YouTube blocking).")
        if result.stderr:
            print(result.stderr[-300:])
        return []

    videos = []
    for line in result.stdout.strip().splitlines():
        if not line.strip():
            continue
        try:
            item = _json.loads(line)
        except Exception:
            continue
        video_id = item.get("id")
        if not video_id:
            continue
        videos.append({
            "title": item.get("title") or "Untitled",
            "url": f"https://www.youtube.com/watch?v={video_id}"
        })
    return videos


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


# ============================================================
# GUI APPLICATION
# ============================================================

class EchoYTApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube → Drive Music")
        self.root.geometry("720x600")
        self.root.minsize(620, 520)
        self.msg_queue = queue.Queue()
        self.results = []
        self.drive_service = None
        self.drive_folder_id = None

        self.build_ui()
        self.log_msg("Welcome! Preparing tools and connecting to Google Drive...")

        # Poll the message queue to keep the UI responsive
        self.root.after(100, self.process_queue)

    def build_ui(self):
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill="both", expand=True)

        # Title
        title = ttk.Label(main, text="YouTube → Drive Music",
                          font=("Segoe UI", 16, "bold"))
        title.pack(anchor="w", pady=(0, 10))

        # Search row
        row = ttk.Frame(main)
        row.pack(fill="x", pady=(0, 8))
        self.search_entry = ttk.Entry(row, font=("Segoe UI", 11))
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.search_entry.bind("<Return>", lambda e: self.do_search())
        self.search_btn = ttk.Button(row, text="Search", command=self.do_search)
        self.search_btn.pack(side="right")

        # Progress bar
        self.progress = ttk.Progressbar(main, mode="indeterminate")
        self.progress.pack(fill="x", pady=(0, 8))
        self.progress.pack_forget()

        # Results list
        self.results_list = tk.Listbox(main, height=10, font=("Segoe UI", 10))
        self.results_list.pack(fill="both", expand=True, pady=(0, 8))
        self.results_list.bind("<Double-Button-1>", lambda e: self.download_selected())

        # Download button
        self.dl_btn = ttk.Button(main, text="Download Selected", command=self.download_selected)
        self.dl_btn.pack(fill="x", pady=(0, 8))

        # Log area
        self.log = scrolledtext.ScrolledText(main, height=10, state="disabled",
                                             font=("Consolas", 9))
        self.log.pack(fill="both", expand=True)

        self.log_msg("Welcome! Preparing tools and connecting to Google Drive...")

    # ---------- logging ----------
    def log_msg(self, msg):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def set_busy(self, busy):
        if busy:
            self.search_btn.configure(state="disabled")
            self.dl_btn.configure(state="disabled")
            self.progress.pack(fill="x", pady=(0, 8))
            self.progress.start(10)
        else:
            self.search_btn.configure(state="normal")
            self.dl_btn.configure(state="normal")
            self.progress.stop()
            self.progress.pack_forget()

    # ---------- message queue ----------
    def worker(self, fn, *args):
        # fn returns a 3-tuple: (label, ok, payload)
        def run():
            try:
                label, ok, payload = fn(*args)
                self.msg_queue.put((label, ok, payload))
            except Exception as e:
                self.msg_queue.put(("generic", False, str(e)))
        threading.Thread(target=run, daemon=True).start()

    def process_queue(self):
        try:
            while True:
                label, ok, payload = self.msg_queue.get_nowait()
                if label == "log":
                    self.log_msg(payload)
                elif label == "done":
                    self.set_busy(False)
                    self.log_msg(payload if ok else f"ERROR: {payload}")
                else:
                    self.set_busy(False)
                    if label == "search":
                        self.populate_results(payload if ok else [])
                    elif not ok:
                        self.log_msg(f"ERROR: {payload}")
                        messagebox.showerror("Error", payload)
        except queue.Empty:
            pass
        self.root.after(100, self.process_queue)

    def populate_results(self, results):
        self.results = results
        self.results_list.delete(0, "end")
        if not results:
            self.log_msg("No results found.")
            return
        for r in results:
            self.results_list.insert("end", r["title"])
        self.log_msg(f"Found {len(results)} result(s).")

    # ---------- startup ----------
    def startup(self):
        self.set_busy(True)
        self.worker(self.startup_task)

    def startup_task(self):
        # 1. Tools
        self.msg_queue.put(("log", True, "Step 1/3: Checking tools..."))
        check_tools(lambda m: self.msg_queue.put(("log", True, "  " + m)))

        # 2. Authenticate Drive
        self.msg_queue.put(("log", True, "Step 2/3: Authenticating Google Drive..."))
        service = authenticate_drive()
        self.drive_service = service

        # 3. Mount rclone
        self.msg_queue.put(("log", True, "Step 3/3: Setting up Drive mount (G:)..."))
        setup_and_mount_rclone(drive_letter="G")

        if service:
            self.drive_folder_id = get_drive_music_folder(service)

        return "done", True, "Startup complete. Ready to search & download."

    # ---------- search ----------
    def do_search(self):
        query = self.search_entry.get().strip()
        if not query:
            messagebox.showwarning("Empty search", "Type a song name first.")
            return
        self.log_msg(f"\nSearching YouTube for: {query}")
        self.results_list.delete(0, "end")
        self.set_busy(True)
        self.worker(self.search_task, query)

    def search_task(self, query):
        results = search_youtube(query)
        return "search", True, results

    # ---------- download ----------
    def download_selected(self):
        sel = self.results_list.curselection()
        if not sel:
            messagebox.showwarning("No selection", "Select a result to download.")
            return
        idx = sel[0]
        video = self.results[idx]
        self.set_busy(True)
        self.worker(self.download_task, video)

    def download_task(self, video):
        self.msg_queue.put(("log", True, f"Selected: {video['title']}"))

        local_file = download_song(video["url"])
        if local_file is None:
            return "done", False, "Download failed, nothing uploaded."

        if not self.drive_service or not self.drive_folder_id:
            return "done", True, "Drive not ready; saved locally only."

        existing = find_file_on_drive(self.drive_service, self.drive_folder_id, local_file.name)
        if existing:
            gc.collect()
            try:
                local_file.unlink()
            except OSError:
                pass
            return "done", True, f"Already on Drive. Removed local copy. ({existing['name']})"

        uploaded = upload_file(self.drive_service, local_file, self.drive_folder_id)
        gc.collect()
        try:
            local_file.unlink()
        except OSError as e:
            self.msg_queue.put(("log", True, f"Note: couldn't delete local file: {e}"))

        return "done", True, f"Uploaded: {uploaded['name']}"


def run_gui():
    root = tk.Tk()
    app = EchoYTApp(root)

    # Block the worker until credentials exist, guiding the user on the main thread.
    def pre_check_credentials():
        while not os.path.exists(CREDENTIALS_PATH):
            app.set_busy(False)
            guide_credentials_setup(root=root)
        app.set_busy(True)
        app.startup()

    root.after(300, pre_check_credentials)
    root.mainloop()


if __name__ == "__main__":
    run_gui()
