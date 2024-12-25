import os
import hashlib
import sqlite3
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class LLaMAFileHandler(FileSystemEventHandler):
    def __init__(self, db_path):
        self.db_path = db_path

    def on_modified(self, event):
        if not event.is_directory:
            self.log_file_change(event.src_path)

    def log_file_change(self, file_path):
        try:
            file_hash = self.get_file_hash(file_path)
            file_size = os.path.getsize(file_path)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO file_analysis (file_hash, binary_type, file_size, analysis_timestamp)
                    VALUES (?, ?, ?, ?)
                """, (file_hash, "binary", file_size, time.ctime()))
                print(f"Logged change for file: {file_path}")
        except Exception as e:
            print(f"Error logging file change: {e}")

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

if __name__ == "__main__":
    monitor = LLaMAFileMonitor()
    monitor.start_monitoring()
