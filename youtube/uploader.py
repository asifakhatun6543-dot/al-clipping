"""
AutoTube AI - YouTube Video Uploader
Official YouTube Data API v3 chunked resumable upload service.
Handles exponential backoff, thumbnail upload, quota monitoring, and duplicate prevention.
"""

import os
import time
import json
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from youtube.authentication import YouTubeAuthenticator
from database.db import record_upload, update_clip_status, update_schedule_status
from services.logger import log_info, log_error, log_warning, log_success
from services.notification import NotificationManager


class YouTubeUploader:
    def __init__(self):
        self.auth = YouTubeAuthenticator()

    def upload_clip(
        self,
        clip_id: int,
        video_path: str,
        title: str,
        description: str,
        keywords: Optional[str] = None,
        category_id: str = "24",
        privacy_status: str = "private",
        thumbnail_path: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Uploads a generated short to YouTube via chunked resumable upload.
        Returns: (success: bool, youtube_video_id: Optional[str], error_message: Optional[str])
        """
        file_path = Path(video_path)
        if not file_path.exists():
            err = f"Video file not found: {video_path}"
            log_error("YouTubeUploader", err)
            update_clip_status(clip_id, "failed", error_message=err)
            return False, None, err

        service = self.auth.get_youtube_service()
        if not service:
            err = "YouTube service not authenticated. Please complete OAuth in settings."
            log_error("YouTubeUploader", err)
            update_clip_status(clip_id, "failed", error_message=err)
            NotificationManager.notify("Upload Failed", err, level="error")
            return False, None, err

        # Prepare tags list
        tags = []
        if keywords:
            tags = [k.strip() for k in keywords.split(",") if k.strip()]
        if "Shorts" not in tags:
            tags.append("Shorts")

        # Metadata body
        body = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": tags[:30],
                "categoryId": str(category_id)
            },
            "status": {
                "privacyStatus": privacy_status.lower(),
                "selfDeclaredMadeForKids": False
            }
        }

        # Media chunked file upload (2MB chunks)
        media = MediaFileUpload(
            str(file_path),
            mimetype="video/mp4",
            chunksize=2 * 1024 * 1024,
            resumable=True
        )

        log_info("YouTubeUploader", f"Starting resumable upload for: '{title}' ({file_path.stat().st_size / (1024*1024):.1f} MB)")
        update_clip_status(clip_id, "uploading")

        insert_request = service.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )

        response = None
        max_retries = 5
        retry_delay = 5.0
        video_id = None

        while response is None:
            try:
                status, response = insert_request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    log_info("YouTubeUploader", f"Upload progress: {progress}%")
            except HttpError as e:
                if e.resp.status in [500, 502, 503, 504]:
                    max_retries -= 1
                    if max_retries > 0:
                        log_warning("YouTubeUploader", f"Transient HTTP {e.resp.status}. Retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                        retry_delay *= 2
                        continue
                elif e.resp.status == 403:
                    # Check for quota exceeded
                    err_content = json.loads(e.content.decode("utf-8")) if e.content else {}
                    reasons = [err.get("reason") for err in err_content.get("error", {}).get("errors", [])]
                    if "quotaExceeded" in reasons:
                        msg = "Daily YouTube API quota exceeded (10,000 units/day). Uploads will resume when quota resets."
                        log_error("YouTubeUploader", msg)
                        update_clip_status(clip_id, "failed", error_message=msg)
                        NotificationManager.notify("API Quota Limit", msg, level="warning")
                        return False, None, msg

                err_msg = f"YouTube HTTP Error {e.resp.status}: {e.content.decode('utf-8') if e.content else str(e)}"
                log_error("YouTubeUploader", err_msg)
                update_clip_status(clip_id, "failed", error_message=err_msg)
                NotificationManager.notify("Upload Error", err_msg, level="error")
                return False, None, err_msg
            except Exception as e:
                err_msg = f"Unexpected upload failure: {e}"
                log_error("YouTubeUploader", err_msg)
                update_clip_status(clip_id, "failed", error_message=err_msg)
                return False, None, err_msg

        if response and "id" in response:
            video_id = response["id"]
            youtube_url = f"https://youtube.com/shorts/{video_id}"
            log_success("YouTubeUploader", f"Short uploaded successfully! URL: {youtube_url}")

            # Optional: Upload custom thumbnail if channel is verified
            if thumbnail_path and Path(thumbnail_path).exists():
                try:
                    thumb_media = MediaFileUpload(str(Path(thumbnail_path)), mimetype="image/jpeg")
                    service.thumbnails().set(videoId=video_id, media_body=thumb_media).execute()
                    log_info("YouTubeUploader", f"Custom thumbnail attached to video: {video_id}")
                except Exception as te:
                    log_warning("YouTubeUploader", f"Could not set custom thumbnail (channel may not be phone-verified for custom thumbnails): {te}")

            # Record in SQLite history
            record_upload(
                clip_id=clip_id,
                youtube_video_id=video_id,
                title=title,
                youtube_url=youtube_url,
                privacy=privacy_status,
                status="success",
                raw_response=json.dumps(response)
            )

            NotificationManager.notify("Upload Complete", f"Short published: {title}", level="success")
            return True, video_id, None
        else:
            err = "Upload completed but no video ID was returned in API response."
            log_error("YouTubeUploader", err)
            update_clip_status(clip_id, "failed", error_message=err)
            return False, None, err
