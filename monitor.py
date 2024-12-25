import os
import hashlib
import sqlite3
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import requests
import threading

class LLaMAFileHandler(FileSystemEventHandler):
    def __init__(self, db_path):
        self.db_path = db_path

    def on_modified(self, event):
        if not event.is_directory:
            self.log_file_change(event.src_path)

    def log_file_change(self, file_path):
        file_hash = self.get_file_hash(file_path)
        file_size = os.path.getsize(file_path)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO file_analysis (file_hash, binary_type, file_size, analysis_timestamp)
                VALUES (?, ?, ?, ?)
            """, (file_hash, "binary", file_size, time.ctime()))

    @staticmethod 
    def get_file_hash(file_path):
        try:
            with open(file_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception as e:
            print(f"Failed to hash file: {e}")
            return "Error"

class LLaMAFileMonitor:
    def __init__(self, db_path="llama_analysis.db"):
        self.db_path = db_path
        self.setup_database()

    def setup_database(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_analysis (
                    id INTEGER PRIMARY KEY,
                    file_hash TEXT,
                    binary_type TEXT,
                    file_size INTEGER,
                    analysis_timestamp TEXT
                )
            """)

    def start_monitoring(self, path="."):
        event_handler = LLaMAFileHandler(self.db_path)
        observer = Observer()
        observer.schedule(event_handler, path, recursive=False)
        observer.start()
        print(f"Monitoring started in {path}")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()

class GitHubMonitor:
    def __init__(self, repo, db_path, token=None):
        self.repo = repo
        self.db_path = db_path
        self.token = token
        self.headers = {"Authorization": f"token {self.token}"} if self.token else {}

    def fetch_releases(self):
        url = f"https://api.github.com/repos/{self.repo}/releases"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            releases = response.json()
            for release in releases:
                for asset in release.get("assets", []):
                    self.log_remote_file(asset["browser_download_url"], asset["name"])
        else:
            print(f"Failed to fetch releases: {response.status_code}")
            print(response.json())

    def log_remote_file(self, url, file_name):
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                file_hash = hashlib.sha256(response.content).hexdigest()
                file_size = len(response.content)
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT INTO file_analysis (file_hash, binary_type, file_size, analysis_timestamp)
                        VALUES (?, ?, ?, ?)
                    """, (file_hash, file_name, file_size, time.ctime()))
                print(f"Logged remote file: {file_name}")
            else:
                print(f"Failed to download {url}: {response.status_code}")
        except Exception as e:
            print(f"Error logging remote file {file_name}: {e}")

if __name__ == "__main__":
    # Initialize the local monitor
    monitor = LLaMAFileMonitor()

    # Initialize GitHub monitor
    github_monitor = GitHubMonitor(
        repo="your-repo-name",  # Replace with your actual GitHub repo name
        db_path="llama_analysis.db",
        token="your-github-token"  # Replace with your GitHub token
    )

    def start_github_monitoring():
        while True:
            github_monitor.fetch_releases()
            time.sleep(3600)  # Check for new releases every hour

    # Start local monitoring in one thread
    threading.Thread(target=monitor.start_monitoring, args=(".",), daemon=True).start()

    # Start GitHub monitoring in another thread
    threading.Thread(target=start_github_monitoring, daemon=True).start()

    print("Monitoring both local and GitHub releases.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping monitoring.")
