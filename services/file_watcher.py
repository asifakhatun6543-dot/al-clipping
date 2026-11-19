"""
AutoTube AI - File Watcher Service
Monitors /videos/input/ for newly dropped videos, checks file stability,
and triggers automatic processing.
"""

import time
from pathlib import Path
from typing import Callable, Optional, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileMovedEvent
from core.config import config
from database.db import get_source_video_by_path
from services.logger import log_info, log_error, log_warning


def is_file_fully_written(file_path: Path, wait_interval: float = 2.0, max_attempts: int = 15) -> bool:
    """Verifies that a video copy or download has completed by checking file size stability."""
    if not file_path.exists():
        return False

    prev_size = -1
    for _ in range(max_attempts):
        try:
            curr_size = file_path.stat().st_size
            if curr_size > 0 and curr_size == prev_size:
                return True
            prev_size = curr_size
            time.sleep(wait_interval)
        except Exception:
            time.sleep(wait_interval)
    return False


class VideoDropHandler(FileSystemEventHandler):
    def __init__(self, on_new_video_callback: Callable[[str], None]):
        super().__init__()
        self.callback = on_new_video_callback
        self.processed_paths: Set[str] = set()

    def process_candidate(self, file_path_str: str):
        path = Path(file_path_str)
        if not path.is_file():
            return

        if path.suffix.lower() not in config.supported_extensions:
            return

        resolved_str = str(path.resolve())
        if resolved_str in self.processed_paths:
            return

        # Check database if already processed
        existing = get_source_video_by_path(resolved_str)
        if existing and existing["status"] in ["analyzed", "completed", "processing"]:
            log_info("FileWatcher", f"Skipping already tracked video: {path.name}")
            self.processed_paths.add(resolved_str)
            return

        log_info("FileWatcher", f"New video detected in input folder: {path.name}. Awaiting write completion...")
        if is_file_fully_written(path):
            self.processed_paths.add(resolved_str)
            log_info("FileWatcher", f"File ready: {path.name}. Dispatching to pipeline.")
            try:
                self.callback(resolved_str)
            except Exception as e:
                log_error("FileWatcher", f"Error dispatching video {path.name}: {e}")
        else:
            log_warning("FileWatcher", f"File {path.name} was not fully written within timeout.")

    def on_created(self, event: FileCreatedEvent):
        if not event.is_directory:
            self.process_candidate(event.src_path)

    def on_moved(self, event: FileMovedEvent):
        if not event.is_directory:
            self.process_candidate(event.dest_path)


class InputFolderWatcher:
    def __init__(self, on_new_video: Callable[[str], None], watch_dir: Optional[Path] = None):
        self.watch_dir = watch_dir or config.input_dir
        self.on_new_video = on_new_video
        self.observer: Optional[Observer] = None
        self.handler = VideoDropHandler(self.on_new_video)

    def scan_existing_files(self):
        """Scans folder for existing files that haven't been processed yet."""
        log_info("FileWatcher", f"Scanning input directory for pending videos: {self.watch_dir}")
        for ext in config.supported_extensions:
            for video_file in self.watch_dir.glob(f"*{ext}"):
                self.handler.process_candidate(str(video_file))

    def start(self):
        self.watch_dir.mkdir(parents=True, exist_ok=True)
        # First process any existing files
        self.scan_existing_files()
        
        self.observer = Observer()
        self.observer.schedule(self.handler, path=str(self.watch_dir), recursive=False)
        self.observer.start()
        log_info("FileWatcher", f"Active watcher started on: {self.watch_dir}")

    def stop(self):
        if self.observer and self.observer.is_alive():
            self.observer.stop()
            self.observer.join()
            log_info("FileWatcher", "Watcher stopped.")
