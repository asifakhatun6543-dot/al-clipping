"""
AutoTube AI - Central Configuration
Zero recurring investment YouTube Shorts automation system
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

VIDEOS_DIR = BASE_DIR / "videos"
INPUT_DIR = VIDEOS_DIR / "input"
PROCESSED_DIR = VIDEOS_DIR / "processed"
THUMBNAILS_DIR = VIDEOS_DIR / "thumbnails"
MUSIC_DIR = VIDEOS_DIR / "background_music"
LOGS_DIR = BASE_DIR / "logs"
DATABASE_DIR = BASE_DIR / "database"
DB_PATH = DATABASE_DIR / "autotube.db"
YOUTUBE_SECRETS_PATH = BASE_DIR / "client_secret.json"
YOUTUBE_TOKEN_PATH = BASE_DIR / "token.json"

# Ensure all critical directories exist
for path in [INPUT_DIR, PROCESSED_DIR, THUMBNAILS_DIR, MUSIC_DIR, LOGS_DIR, DATABASE_DIR]:
    path.mkdir(parents=True, exist_ok=True)


@dataclass
class AppConfig:
    # Storage & directories
    base_dir: Path = BASE_DIR
    input_dir: Path = INPUT_DIR
    processed_dir: Path = PROCESSED_DIR
    thumbnails_dir: Path = THUMBNAILS_DIR
    music_dir: Path = MUSIC_DIR
    logs_dir: Path = LOGS_DIR
    db_path: Path = DB_PATH
    client_secret_path: Path = YOUTUBE_SECRETS_PATH
    token_path: Path = YOUTUBE_TOKEN_PATH

    # Video specification (YouTube Shorts 9:16)
    target_width: int = 1080
    target_height: int = 1920
    fps: int = 60
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    audio_bitrate: str = "192k"
    video_bitrate: str = "8500k"
    quality_preset: str = "1080p_60fps"  # '1080p_60fps', '4k_60fps'

    # AI Clipping Durations (seconds)
    min_clip_duration: float = 15.0
    max_clip_duration: float = 60.0
    default_clip_duration: float = 35.0
    max_clips_per_video: int = 5

    # Intelligent Cropping & Layout:
    # 'split_gaming' (Streamer on Top, Gameplay on Bottom - Viral Shorts layout)
    # 'smart' (face/motion centered), 'crop' (center 9:16), 'blur_fill' (letterbox with blurred mirror bg)
    crop_mode: str = "split_gaming"
    facecam_position: str = "auto"  # 'auto', 'top_right', 'top_left', 'bottom_right', 'bottom_left'
    hook_banner_text: str = "WAIT TILL THE END 💀"

    # Subtitles (Word-by-word High-Retention Gaming Karaoke)
    karaoke_enabled: bool = True
    subtitle_font: str = "Impact"
    font_size: int = 56
    highlight_color: str = "&H0000FFFF"  # ASS Hex for Electric Neon Yellow (&HAABBGGRR)
    text_color: str = "&H00FFFFFF"       # ASS Hex for Crisp White
    outline_color: str = "&H00000000"    # Solid Black
    outline_width: int = 5
    shadow_depth: int = 3
    max_words_per_subtitle_line: int = 2  # Punchy 1-2 words at a time
    subtitle_margin_v: int = 880          # Positioned directly at center junction between reaction and game

    # Audio normalization & Background Music
    normalize_audio: bool = True
    target_lufs: float = -14.0
    bg_music_volume: float = 0.12  # Ducked volume so speech is crystal clear

    # Speech Recognition (Whisper)
    whisper_model_size: str = "base"  # 'tiny', 'base', 'small', 'medium' (local CPU friendly)
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"  # Lightweight for ordinary CPUs

    # Scheduling Defaults
    timezone: str = "Asia/Kolkata"
    daily_schedule_slots: List[str] = field(
        default_factory=lambda: ["09:00", "12:00", "15:00", "18:00", "21:00"]
    )

    # YouTube Upload Settings
    default_privacy: str = "private"  # 'private', 'unlisted', 'public'
    default_category_id: str = "24"    # 24 = Entertainment, 22 = People & Blogs, 28 = Sci & Tech
    channel_name: str = "AutoTube Channel"
    auto_publish_enabled: bool = False  # Upload automatically when ready

    # File watcher & automation
    watch_interval_seconds: int = 10
    max_concurrent_jobs: int = 1
    supported_extensions: List[str] = field(
        default_factory=lambda: [".mp4", ".mov", ".mkv", ".webm"]
    )


# Global default configuration instance
config = AppConfig()
