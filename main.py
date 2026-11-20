"""
AutoTube AI - Main Application Entrypoint
Autonomous YouTube Shorts Clipping, Karaoke Subtitles & Publishing System
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import config
from database.db import init_db, get_dashboard_stats
from services.logger import log_info, log_error
from core.automation import engine


def run_dashboard():
    """Launches the Streamlit web dashboard."""
    dashboard_script = PROJECT_ROOT / "app" / "dashboard.py"
    cmd = [
        sys.executable,
        "-m", "streamlit", "run",
        str(dashboard_script),
        "--server.port=8501",
        "--server.headless=true",
        "--browser.gatherUsageStats=false"
    ]
    log_info("Main", f"Launching Streamlit dashboard on port 8501...")
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        log_info("Main", "Dashboard stopped by user.")


def run_worker():
    """Runs headless background automation worker indefinitely."""
    log_info("Main", "Starting AutoTube AI headless background automation worker...")
    engine.start()
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log_info("Main", "Stopping background worker...")
        engine.stop()


def run_process_video(video_path: str):
    """Processes a single video directly from command line."""
    from video.clip_generator import ClipGenerationPipeline
    path = Path(video_path).resolve()
    if not path.exists():
        print(f"Error: Video file not found: {video_path}")
        sys.exit(1)

    print(f"Processing source video: {path.name}")
    pipeline = ClipGenerationPipeline()
    clips = pipeline.process_source_video(str(path), auto_schedule=True)
    print(f"\nCompleted! Generated {len(clips)} short clips:")
    for c in clips:
        print(f" - [{c['duration']:.1f}s] {c['title']} -> {c['file_path']}")


def run_process_url(video_url: str):
    """Downloads a video from a URL and automatically processes it into Shorts."""
    from services.url_downloader import VideoURLDownloader
    from video.clip_generator import ClipGenerationPipeline

    print(f"Fetching and downloading video from URL: {video_url}")
    downloader = VideoURLDownloader()
    dest_path, meta = downloader.download_video(video_url)
    print(f"Downloaded: {dest_path.name} ({dest_path.stat().st_size / (1024*1024):.1f} MB)")

    print("Running AI clipping pipeline...")
    pipeline = ClipGenerationPipeline()
    clips = pipeline.process_source_video(str(dest_path), auto_schedule=True)
    print(f"\nCompleted! Generated {len(clips)} short clips from URL:")
    for c in clips:
        print(f" - [{c['duration']:.1f}s] {c['title']} -> {c['file_path']}")


def main():
    parser = argparse.ArgumentParser(
        description="AutoTube AI: Autonomous YouTube Shorts Clipping & Publishing System"
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Launch the Streamlit web dashboard"
    )
    parser.add_argument(
        "--worker",
        action="store_true",
        help="Run only the headless background automation worker"
    )
    parser.add_argument(
        "--process",
        type=str,
        help="Process a single video file directly via CLI"
    )
    parser.add_argument(
        "--url",
        type=str,
        help="Download and clip video directly from YouTube or Web URL"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Print database metrics and system status"
    )
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Initialize or reset SQLite database tables"
    )

    args = parser.parse_args()

    # Always ensure DB is initialized
    init_db()

    if args.init_db:
        print("Database initialized successfully.")
        return

    if args.status:
        stats = get_dashboard_stats()
        print("\n=== AutoTube AI Status ===")
        for k, v in stats.items():
            print(f" {k.replace('_', ' ').capitalize()}: {v}")
        print("==========================\n")
        return

    if args.process:
        run_process_video(args.process)
        return

    if args.url:
        run_process_url(args.url)
        return

    if args.worker:
        run_worker()
        return

    # Default action: launch dashboard (which starts background engine automatically)
    run_dashboard()


if __name__ == "__main__":
    main()
