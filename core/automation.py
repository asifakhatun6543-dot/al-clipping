"""
AutoTube AI - Unified Automation Orchestrator
Coordinates folder monitoring, pipeline clipping, and YouTube scheduled uploads.
"""

import time
import threading
from pathlib import Path
from typing import Optional
from core.config import config
from database.db import init_db, set_setting, get_setting
from video.clip_generator import ClipGenerationPipeline
from services.file_watcher import InputFolderWatcher
from core.scheduler import BackgroundUploadScheduler
from services.logger import log_info, log_error, log_warning


class AutoTubeEngine:
    _instance: Optional['AutoTubeEngine'] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AutoTubeEngine, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        
        init_db()
        self.pipeline = ClipGenerationPipeline()
        self.scheduler = BackgroundUploadScheduler()
        self.watcher = InputFolderWatcher(on_new_video=self._on_new_video_detected)
        self._processing_lock = threading.Lock()
        self._is_running = False
        self._initialized = True

    def _on_new_video_detected(self, file_path_str: str):
        """Called when watcher detects a newly added video."""
        # Check if automation is active
        if get_setting("automation_running", "true") != "true":
            log_info("Engine", f"Automation is paused. Queuing video {Path(file_path_str).name} for later.")
            return

        # Run pipeline in a background thread to prevent blocking watcher
        def worker():
            with self._processing_lock:
                try:
                    log_info("Engine", f"Starting automated workflow for: {Path(file_path_str).name}")
                    self.pipeline.process_source_video(file_path_str, auto_schedule=True)
                except Exception as e:
                    log_error("Engine", f"Automated processing failed for {file_path_str}: {e}")

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def start(self):
        """Starts background automation service."""
        if not self._is_running:
            set_setting("automation_running", "true")
            self.scheduler.start()
            self.watcher.start()
            self._is_running = True
            log_info("Engine", "AutoTube AI automation engine started successfully.")

    def pause(self):
        """Pauses automation (no new clippings or uploads will trigger)."""
        set_setting("automation_running", "false")
        log_info("Engine", "AutoTube AI automation paused by user.")

    def resume(self):
        """Resumes automation."""
        set_setting("automation_running", "true")
        log_info("Engine", "AutoTube AI automation resumed.")

    def stop(self):
        """Stops all background monitors and schedulers."""
        set_setting("automation_running", "false")
        if self._is_running:
            self.watcher.stop()
            self.scheduler.stop()
            self._is_running = False
            log_info("Engine", "AutoTube AI automation stopped.")

    def is_running(self) -> bool:
        return self._is_running and (get_setting("automation_running", "true") == "true")


# Global engine instance
engine = AutoTubeEngine()
