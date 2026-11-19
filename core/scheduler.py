"""
AutoTube AI - Background Scheduler Engine
Uses APScheduler to execute time-based YouTube video uploads.
Prevents concurrent uploads and automatically recovers pending jobs across restarts.
"""

import threading
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from core.config import config
from database.db import (
    get_due_schedule_items,
    update_schedule_status,
    get_setting,
    get_clip
)
from youtube.uploader import YouTubeUploader
from services.logger import log_info, log_error, log_warning, log_success
from services.notification import NotificationManager


class BackgroundUploadScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.uploader = YouTubeUploader()
        self._upload_lock = threading.Lock()
        self._running = False

    def check_and_publish_due_clips(self):
        """
        Job executed periodically to discover and publish any videos whose
        scheduled time has arrived.
        """
        if not self._upload_lock.acquire(blocking=False):
            log_info("Scheduler", "An upload is currently in progress. Skipping check this cycle.")
            return

        try:
            # Check if automation is paused in database settings
            is_active = get_setting("automation_running", "true") == "true"
            if not is_active:
                return

            tz_name = get_setting("timezone", config.timezone)
            try:
                tz = ZoneInfo(tz_name)
            except Exception:
                tz = ZoneInfo("UTC")

            now_iso = datetime.now(tz).isoformat()
            due_items = get_due_schedule_items(now_iso)

            if not due_items:
                return

            log_info("Scheduler", f"Found {len(due_items)} clip(s) due for publishing.")

            for item in due_items:
                schedule_id = item["id"]
                clip_id = item["clip_id"]
                title = item["title"]
                file_path = item["file_path"]
                thumb_path = item.get("thumbnail_path")
                desc = item.get("description", "")
                kws = item.get("keywords", "")
                cat_id = item.get("category_id", "24")
                privacy = item.get("privacy", "private")

                log_info("Scheduler", f"Processing scheduled publishing for Clip #{clip_id}: '{title}'")
                update_schedule_status(schedule_id, "processing")

                success, vid_id, err = self.uploader.upload_clip(
                    clip_id=clip_id,
                    video_path=file_path,
                    title=title,
                    description=desc,
                    keywords=kws,
                    category_id=cat_id,
                    privacy_status=privacy,
                    thumbnail_path=thumb_path
                )

                if success:
                    update_schedule_status(schedule_id, "published")
                    log_success("Scheduler", f"Successfully published Clip #{clip_id} to YouTube! Video ID: {vid_id}")
                else:
                    update_schedule_status(schedule_id, "failed", error_message=err)
                    log_error("Scheduler", f"Publishing failed for Clip #{clip_id}: {err}")

                # Process one clip at a time to respect YouTube rate limits
                break

        except Exception as e:
            log_error("Scheduler", f"Unexpected error in background schedule checker: {e}")
        finally:
            self._upload_lock.release()

    def start(self):
        if not self._running:
            self.scheduler.add_job(
                self.check_and_publish_due_clips,
                trigger=IntervalTrigger(seconds=30),
                id="due_clips_checker",
                name="Check Due YouTube Uploads",
                replace_existing=True
            )
            self.scheduler.start()
            self._running = True
            log_info("Scheduler", "APScheduler background upload monitor started (30s interval).")

    def stop(self):
        if self._running:
            self.scheduler.shutdown(wait=False)
            self._running = False
            log_info("Scheduler", "Scheduler stopped.")
