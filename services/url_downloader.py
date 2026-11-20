"""
AutoTube AI - Video URL Downloader Service
Downloads videos directly from YouTube, Vimeo, Twitch, and direct URLs using yt-dlp.
Zero paid APIs - 100% free and open-source.
"""

import re
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Callable
import yt_dlp
from core.config import config
from database.db import register_source_video
from services.logger import log_info, log_error, log_warning


def sanitize_filename(name: str) -> str:
    """Removes invalid filesystem characters from title."""
    clean = re.sub(r'[\\/*?:"<>|]', "", name)
    clean = re.sub(r'\s+', "_", clean).strip("_")
    return clean[:80] if clean else "downloaded_video"


class VideoURLDownloader:
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or config.input_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"

    def get_default_ydl_opts(self, progress_hook: Optional[Callable] = None) -> Dict[str, Any]:
        opts = {
            "quiet": True,
            "no_warnings": False,
            "ffmpeg_location": self.ffmpeg_bin,
            "format": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "merge_output_format": "mp4",
            "extractor_args": {
                "youtube": {
                    "player_client": ["ios", "android", "mweb"]
                }
            }
        }
        if progress_hook:
            opts["progress_hooks"] = [progress_hook]
        return opts

    def extract_info(self, url: str) -> Dict[str, Any]:
        """
        Extracts metadata (title, duration, thumbnail, author) from video URL
        without downloading the video.
        """
        log_info("URLDownloader", f"Extracting video metadata from URL: {url}")
        opts = {
            "quiet": True,
            "skip_download": True,
            "extractor_args": {
                "youtube": {
                    "player_client": ["ios", "android", "mweb"]
                }
            }
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    "title": info.get("title", "Online Video"),
                    "duration": float(info.get("duration", 0.0) or 0.0),
                    "thumbnail": info.get("thumbnail"),
                    "uploader": info.get("uploader") or info.get("channel", "Unknown Creator"),
                    "view_count": info.get("view_count", 0),
                    "description": info.get("description", ""),
                    "webpage_url": info.get("webpage_url", url),
                    "id": info.get("id", "")
                }
        except Exception as e:
            log_error("URLDownloader", f"Failed to extract info from {url}: {e}")
            raise RuntimeError(f"Could not fetch video info from URL: {e}")

    def download_video(
        self,
        url: str,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        max_duration_seconds: Optional[float] = None
    ) -> Tuple[Path, Dict[str, Any]]:
        """
        Downloads the video from the URL, saves it as an MP4 in videos/input/,
        and registers it in the SQLite database.
        """
        log_info("URLDownloader", f"Starting video download from: {url}")
        
        # 1. Fetch info first
        meta = self.extract_info(url)
        clean_title = sanitize_filename(meta["title"])
        dest_filename = f"{clean_title}.mp4"
        dest_path = self.output_dir / dest_filename

        # If file already exists, avoid re-downloading
        if dest_path.exists() and dest_path.stat().st_size > 1024 * 1024:
            log_info("URLDownloader", f"Video already downloaded: {dest_filename}")
            vid_id = register_source_video(
                file_path=str(dest_path.resolve()),
                file_name=dest_filename,
                file_size_bytes=dest_path.stat().st_size,
                duration_seconds=meta["duration"]
            )
            return dest_path, meta

        # 2. Configure yt-dlp download options
        def _hook(d):
            if progress_callback:
                progress_callback(d)

        opts = self.get_default_ydl_opts(progress_hook=_hook)
        opts["outtmpl"] = str(self.output_dir / f"{clean_title}.%(ext)s")

        # Optional download range limit if video is very long
        if max_duration_seconds and meta["duration"] > max_duration_seconds:
            opts["download_ranges"] = yt_dlp.utils.download_range_func(None, [(0, max_duration_seconds)])
            opts["force_keyframes_at_cuts"] = True

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])

            # Find the downloaded file
            target_file = dest_path
            if not target_file.exists():
                # Check if downloaded with another extension and remux
                candidates = list(self.output_dir.glob(f"{clean_title}.*"))
                if candidates:
                    target_file = candidates[0]

            if not target_file.exists() or target_file.stat().st_size == 0:
                raise RuntimeError(f"Download failed: {target_file.name} was not created.")

            log_info("URLDownloader", f"Successfully downloaded: {target_file.name} ({target_file.stat().st_size / (1024*1024):.1f} MB)")

            # 3. Register in SQLite database
            vid_id = register_source_video(
                file_path=str(target_file.resolve()),
                file_name=target_file.name,
                file_size_bytes=target_file.stat().st_size,
                duration_seconds=meta["duration"]
            )

            return target_file, meta

        except Exception as e:
            log_error("URLDownloader", f"Download error for {url}: {e}")
            raise
