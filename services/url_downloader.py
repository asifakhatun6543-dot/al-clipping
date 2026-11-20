"""
AutoTube AI - Video URL Downloader Service
Optimized high-speed video ingestion using yt-dlp with in-memory caching.
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

# Global in-memory cache to prevent redundant YouTube API hits
_URL_INFO_CACHE: Dict[str, Dict[str, Any]] = {}


def sanitize_filename(name: str) -> str:
    """Removes invalid filesystem characters from title."""
    clean = re.sub(r'[\\/*?:"<>|]', "", name)
    clean = re.sub(r'\s+', "_", clean).strip("_")
    return clean[:60] if clean else "downloaded_video"


class VideoURLDownloader:
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or config.input_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"

    def get_default_ydl_opts(self, progress_hook: Optional[Callable] = None) -> Dict[str, Any]:
        opts = {
            "quiet": True,
            "no_warnings": True,
            "ffmpeg_location": self.ffmpeg_bin,
            # Progressive direct stream to eliminate HTTP 403 Forbidden
            "format": "best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best",
            "merge_output_format": "mp4",
            "socket_timeout": 25,
            "retries": 5,
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            },
            "extractor_args": {
                "youtube": {
                    "player_client": ["android", "ios"]
                }
            }
        }
        cookie_file = config.base_dir / "cookies.txt"
        if cookie_file.exists() and cookie_file.stat().st_size > 10:
            opts["cookiefile"] = str(cookie_file.resolve())

        if progress_hook:
            opts["progress_hooks"] = [progress_hook]
        return opts

    def extract_info(self, url: str) -> Dict[str, Any]:
        """
        Fast cached metadata extraction (title, duration, thumbnail, author).
        """
        clean_url = url.strip()
        if clean_url in _URL_INFO_CACHE:
            return _URL_INFO_CACHE[clean_url]

        log_info("URLDownloader", f"Fetching metadata for: {clean_url}")
        opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "socket_timeout": 8,
            "no_playlist": True,
            "check_formats": False,
            "youtube_include_dash_manifest": False,
            "youtube_include_hls_manifest": False,
            "extractor_args": {
                "youtube": {
                    "player_client": ["android", "ios"]
                }
            }
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(clean_url, download=False)
                result = {
                    "title": info.get("title", "Online Video"),
                    "duration": float(info.get("duration", 0.0) or 0.0),
                    "thumbnail": info.get("thumbnail"),
                    "uploader": info.get("uploader") or info.get("channel", "Unknown Creator"),
                    "view_count": info.get("view_count", 0),
                    "description": info.get("description", ""),
                    "webpage_url": info.get("webpage_url", clean_url),
                    "id": info.get("id", "")
                }
                _URL_INFO_CACHE[clean_url] = result
                return result
        except Exception as e:
            log_warning("URLDownloader", f"Android client failed, retrying with fallback clients: {e}")
            # Fallback to general client if android fails
            fallback_opts = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "socket_timeout": 15,
                "extractor_args": {
                    "youtube": {
                        "player_client": ["ios", "mweb"]
                    }
                }
            }
            try:
                with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                    info = ydl.extract_info(clean_url, download=False)
                    result = {
                        "title": info.get("title", "Online Video"),
                        "duration": float(info.get("duration", 0.0) or 0.0),
                        "thumbnail": info.get("thumbnail"),
                        "uploader": info.get("uploader") or info.get("channel", "Unknown Creator"),
                        "view_count": info.get("view_count", 0),
                        "description": info.get("description", ""),
                        "webpage_url": info.get("webpage_url", clean_url),
                        "id": info.get("id", "")
                    }
                    _URL_INFO_CACHE[clean_url] = result
                    return result
            except Exception as e2:
                log_error("URLDownloader", f"Failed to extract info from {clean_url}: {e2}")
                raise RuntimeError(f"Could not load video: {e2}")

    def download_video(
        self,
        url: str,
        meta_info: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        max_duration_seconds: Optional[float] = None
    ) -> Tuple[Path, Dict[str, Any]]:
        """
        Downloads video stream directly to videos/input/ and registers it in SQLite.
        Uses cached metadata if provided to avoid duplicate network calls.
        """
        clean_url = url.strip()
        meta = meta_info or self.extract_info(clean_url)
        clean_title = sanitize_filename(meta["title"])
        dest_filename = f"{clean_title}.mp4"
        dest_path = self.output_dir / dest_filename

        # If file already downloaded, skip re-download
        if dest_path.exists() and dest_path.stat().st_size > 1024 * 1024:
            log_info("URLDownloader", f"Using existing downloaded video: {dest_filename}")
            register_source_video(
                file_path=str(dest_path.resolve()),
                file_name=dest_filename,
                file_size_bytes=dest_path.stat().st_size,
                duration_seconds=meta["duration"]
            )
            return dest_path, meta

        log_info("URLDownloader", f"Downloading stream for: '{meta['title']}'")

        def _hook(d):
            if progress_callback:
                progress_callback(d)

        opts = self.get_default_ydl_opts(progress_hook=_hook)
        opts["outtmpl"] = str(self.output_dir / f"{clean_title}.%(ext)s")

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([clean_url])
        except Exception as e:
            if "403" in str(e) or "Forbidden" in str(e):
                log_warning("URLDownloader", f"Got 403 on primary download, trying resilient android_vr fallback: {e}")
                opts["extractor_args"] = {"youtube": {"player_client": ["android_vr"]}}
                opts["format"] = "18/best[ext=mp4]/best"
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([clean_url])
            else:
                raise

            target_file = dest_path
            if not target_file.exists():
                candidates = list(self.output_dir.glob(f"{clean_title}.*"))
                if candidates:
                    target_file = candidates[0]

            if not target_file.exists() or target_file.stat().st_size == 0:
                raise RuntimeError(f"Downloaded file {target_file.name} is missing or 0 bytes.")

            log_info("URLDownloader", f"Downloaded {target_file.name} ({target_file.stat().st_size / (1024*1024):.1f} MB)")

            register_source_video(
                file_path=str(target_file.resolve()),
                file_name=target_file.name,
                file_size_bytes=target_file.stat().st_size,
                duration_seconds=meta["duration"]
            )

            return target_file, meta

        except Exception as e:
            log_error("URLDownloader", f"Download failed: {e}")
            raise
