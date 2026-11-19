"""
AutoTube AI - Database Access Layer
SQLite implementation with WAL mode for safe multi-process concurrency
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from core.config import config
from database.models import CREATE_TABLES_SQL


def get_db_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Creates a connection with Row factory and WAL mode enabled for high concurrency."""
    path = db_path or config.db_path
    conn = sqlite3.connect(str(path), timeout=30.0)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode and foreign keys
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: Optional[Path] = None):
    """Initializes tables, indexes, and default settings."""
    conn = get_db_connection(db_path)
    with conn:
        conn.executescript(CREATE_TABLES_SQL)
        # Default settings if not already populated
        default_settings = {
            "automation_running": "true",
            "daily_schedule_slots": json.dumps(config.daily_schedule_slots),
            "timezone": config.timezone,
            "min_clip_duration": str(config.min_clip_duration),
            "max_clip_duration": str(config.max_clip_duration),
            "default_clip_duration": str(config.default_clip_duration),
            "max_clips_per_video": str(config.max_clips_per_video),
            "karaoke_enabled": "true",
            "crop_mode": config.crop_mode,
            "default_privacy": config.default_privacy,
            "default_category_id": config.default_category_id,
            "whisper_model_size": config.whisper_model_size,
            "auto_publish_enabled": "true",
            "bg_music_volume": str(config.bg_music_volume),
            "normalize_audio": "true",
        }
        for k, v in default_settings.items():
            conn.execute(
                "INSERT OR IGNORE INTO app_settings (key, value) VALUES (?, ?)",
                (k, v)
            )
    conn.close()


# ---------------------- SOURCE VIDEOS ----------------------

def register_source_video(
    file_path: str,
    file_name: str,
    file_size_bytes: int = 0,
    duration_seconds: float = 0.0,
    width: int = 0,
    height: int = 0,
    fps: float = 0.0
) -> Optional[int]:
    """Registers a new input video. Returns its ID, or None if already registered."""
    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO source_videos 
                (file_path, file_name, file_size_bytes, duration_seconds, width, height, fps, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
                """,
                (file_path, file_name, file_size_bytes, duration_seconds, width, height, fps)
            )
            if cursor.lastrowid and cursor.lastrowid > 0:
                return cursor.lastrowid
            # If already exists, return existing id
            cur = conn.execute("SELECT id FROM source_videos WHERE file_path = ?", (file_path,))
            row = cur.fetchone()
            return row["id"] if row else None
    finally:
        conn.close()


def get_source_video(video_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    try:
        cur = conn.execute("SELECT * FROM source_videos WHERE id = ?", (video_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_source_video_by_path(file_path: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    try:
        cur = conn.execute("SELECT * FROM source_videos WHERE file_path = ?", (file_path,))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_source_videos(status: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    try:
        if status:
            cur = conn.execute(
                "SELECT * FROM source_videos WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit)
            )
        else:
            cur = conn.execute(
                "SELECT * FROM source_videos ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def update_source_video_status(video_id: int, status: str, error_message: Optional[str] = None):
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                """
                UPDATE source_videos 
                SET status = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
                """,
                (status, error_message, video_id)
            )
    finally:
        conn.close()


def update_source_video_meta(video_id: int, duration: float, width: int, height: int, fps: float):
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                """
                UPDATE source_videos 
                SET duration_seconds = ?, width = ?, height = ?, fps = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
                """,
                (duration, width, height, fps, video_id)
            )
    finally:
        conn.close()


# ---------------------- GENERATED CLIPS ----------------------

def create_clip(
    source_video_id: int,
    clip_number: int,
    start_time: float,
    end_time: float,
    duration_seconds: float,
    title: str,
    description: str,
    keywords: str,
    hashtags: str,
    category_id: str = "24",
    privacy: str = "private",
    score: float = 0.0,
    file_path: Optional[str] = None,
    thumbnail_path: Optional[str] = None,
    status: str = "ready"
) -> int:
    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO generated_clips 
                (source_video_id, clip_number, start_time, end_time, duration_seconds, 
                 title, description, keywords, hashtags, category_id, privacy, score, 
                 file_path, thumbnail_path, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (source_video_id, clip_number, start_time, end_time, duration_seconds,
                 title, description, keywords, hashtags, category_id, privacy, score,
                 file_path, thumbnail_path, status)
            )
            return cursor.lastrowid
    finally:
        conn.close()


def get_clip(clip_id: int) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    try:
        cur = conn.execute("SELECT * FROM generated_clips WHERE id = ?", (clip_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_clips(status: Optional[str] = None, source_video_id: Optional[int] = None, limit: int = 100) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    try:
        query = "SELECT * FROM generated_clips WHERE 1=1"
        params = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if source_video_id:
            query += " AND source_video_id = ?"
            params.append(source_video_id)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        cur = conn.execute(query, tuple(params))
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def update_clip_status(
    clip_id: int, 
    status: str, 
    file_path: Optional[str] = None, 
    thumbnail_path: Optional[str] = None,
    youtube_video_id: Optional[str] = None, 
    youtube_url: Optional[str] = None,
    error_message: Optional[str] = None
):
    conn = get_db_connection()
    try:
        with conn:
            updates = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
            params = [status]
            if file_path:
                updates.append("file_path = ?")
                params.append(file_path)
            if thumbnail_path:
                updates.append("thumbnail_path = ?")
                params.append(thumbnail_path)
            if youtube_video_id:
                updates.append("youtube_video_id = ?")
                params.append(youtube_video_id)
            if youtube_url:
                updates.append("youtube_url = ?")
                params.append(youtube_url)
            if error_message is not None:
                updates.append("error_message = ?")
                params.append(error_message)
            params.append(clip_id)
            conn.execute(f"UPDATE generated_clips SET {', '.join(updates)} WHERE id = ?", tuple(params))
    finally:
        conn.close()


# ---------------------- PUBLISHING SCHEDULE ----------------------

def add_to_schedule(clip_id: int, scheduled_time: str, tz: str = "Asia/Kolkata") -> int:
    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.execute(
                """
                INSERT OR REPLACE INTO publishing_schedule 
                (clip_id, scheduled_time, timezone, status)
                VALUES (?, ?, ?, 'pending')
                """,
                (clip_id, scheduled_time, tz)
            )
            # Also update clip status to 'scheduled'
            conn.execute(
                "UPDATE generated_clips SET status = 'scheduled', scheduled_time = ? WHERE id = ?",
                (scheduled_time, clip_id)
            )
            return cursor.lastrowid
    finally:
        conn.close()


def get_due_schedule_items(now_iso: str) -> List[Dict[str, Any]]:
    """Returns items that are pending and due at or before now_iso."""
    conn = get_db_connection()
    try:
        cur = conn.execute(
            """
            SELECT ps.*, gc.title, gc.description, gc.file_path, gc.thumbnail_path,
                   gc.keywords, gc.hashtags, gc.category_id, gc.privacy
            FROM publishing_schedule ps
            JOIN generated_clips gc ON ps.clip_id = gc.id
            WHERE ps.status = 'pending' AND ps.scheduled_time <= ?
            ORDER BY ps.scheduled_time ASC
            """,
            (now_iso,)
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def get_next_scheduled_item() -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    try:
        cur = conn.execute(
            """
            SELECT ps.*, gc.title, gc.file_path, gc.thumbnail_path
            FROM publishing_schedule ps
            JOIN generated_clips gc ON ps.clip_id = gc.id
            WHERE ps.status = 'pending'
            ORDER BY ps.scheduled_time ASC
            LIMIT 1
            """
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_latest_scheduled_time() -> Optional[str]:
    conn = get_db_connection()
    try:
        cur = conn.execute(
            """
            SELECT scheduled_time FROM publishing_schedule 
            WHERE status IN ('pending', 'processing')
            ORDER BY scheduled_time DESC LIMIT 1
            """
        )
        row = cur.fetchone()
        return row["scheduled_time"] if row else None
    finally:
        conn.close()


def list_schedule(status: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    try:
        query = """
            SELECT ps.*, gc.title, gc.file_path, gc.thumbnail_path, gc.privacy, gc.duration_seconds
            FROM publishing_schedule ps
            JOIN generated_clips gc ON ps.clip_id = gc.id
        """
        params = []
        if status:
            query += " WHERE ps.status = ?"
            params.append(status)
        query += " ORDER BY ps.scheduled_time ASC LIMIT ?"
        params.append(limit)
        cur = conn.execute(query, tuple(params))
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def update_schedule_status(schedule_id: int, status: str, error_message: Optional[str] = None):
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                """
                UPDATE publishing_schedule
                SET status = ?, last_attempt_at = CURRENT_TIMESTAMP, error_message = ?
                WHERE id = ?
                """,
                (status, error_message, schedule_id)
            )
    finally:
        conn.close()


# ---------------------- UPLOAD HISTORY ----------------------

def record_upload(
    clip_id: int,
    youtube_video_id: str,
    title: str,
    youtube_url: str,
    privacy: str = "private",
    status: str = "success",
    raw_response: Optional[str] = None
) -> int:
    conn = get_db_connection()
    try:
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO upload_history 
                (clip_id, youtube_video_id, title, youtube_url, privacy, status, raw_response)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (clip_id, youtube_video_id, title, youtube_url, privacy, status, raw_response)
            )
            # Update clip record as uploaded
            conn.execute(
                """
                UPDATE generated_clips 
                SET status = 'uploaded', youtube_video_id = ?, youtube_url = ? 
                WHERE id = ?
                """,
                (youtube_video_id, youtube_url, clip_id)
            )
            # Update publishing schedule as published
            conn.execute(
                "UPDATE publishing_schedule SET status = 'published' WHERE clip_id = ?",
                (clip_id,)
            )
            return cursor.lastrowid
    finally:
        conn.close()


def list_upload_history(limit: int = 100) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    try:
        cur = conn.execute(
            """
            SELECT uh.*, gc.duration_seconds, gc.thumbnail_path, gc.file_path
            FROM upload_history uh
            JOIN generated_clips gc ON uh.clip_id = gc.id
            ORDER BY uh.uploaded_at DESC LIMIT ?
            """,
            (limit,)
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


# ---------------------- LOGGING & AUDIT ----------------------

def log_event(level: str, module: str, message: str, details: Optional[str] = None):
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                "INSERT INTO processing_logs (level, module, message, details) VALUES (?, ?, ?, ?)",
                (level.upper(), module, message, details)
            )
    except Exception:
        pass
    finally:
        conn.close()


def get_recent_logs(level: Optional[str] = None, limit: int = 200) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    try:
        if level and level != "ALL":
            cur = conn.execute(
                "SELECT * FROM processing_logs WHERE level = ? ORDER BY id DESC LIMIT ?",
                (level.upper(), limit)
            )
        else:
            cur = conn.execute(
                "SELECT * FROM processing_logs ORDER BY id DESC LIMIT ?",
                (limit,)
            )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def clear_logs():
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("DELETE FROM processing_logs")
    finally:
        conn.close()


# ---------------------- APP SETTINGS ----------------------

def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    conn = get_db_connection()
    try:
        cur = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
        row = cur.fetchone()
        return row["value"] if row else default
    finally:
        conn.close()


def set_setting(key: str, value: str):
    conn = get_db_connection()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO app_settings (key, value, updated_at) 
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP
                """,
                (key, value)
            )
    finally:
        conn.close()


def get_all_settings() -> Dict[str, str]:
    conn = get_db_connection()
    try:
        cur = conn.execute("SELECT key, value FROM app_settings")
        return {r["key"]: r["value"] for r in cur.fetchall()}
    finally:
        conn.close()


# ---------------------- DASHBOARD AGGREGATED METRICS ----------------------

def get_dashboard_stats() -> Dict[str, Any]:
    conn = get_db_connection()
    try:
        total_source = conn.execute("SELECT COUNT(*) as c FROM source_videos").fetchone()["c"]
        total_clips = conn.execute("SELECT COUNT(*) as c FROM generated_clips").fetchone()["c"]
        total_uploaded = conn.execute("SELECT COUNT(*) as c FROM upload_history WHERE status='success'").fetchone()["c"]
        pending_uploads = conn.execute("SELECT COUNT(*) as c FROM publishing_schedule WHERE status='pending'").fetchone()["c"]
        failed_uploads = conn.execute("SELECT COUNT(*) as c FROM publishing_schedule WHERE status='failed'").fetchone()["c"]
        
        # Next scheduled
        cur_next = conn.execute(
            """
            SELECT ps.scheduled_time, gc.title 
            FROM publishing_schedule ps 
            JOIN generated_clips gc ON ps.clip_id = gc.id 
            WHERE ps.status = 'pending' 
            ORDER BY ps.scheduled_time ASC LIMIT 1
            """
        )
        next_row = cur_next.fetchone()
        next_scheduled = f"{next_row['scheduled_time']} ({next_row['title'][:25]}...)" if next_row else "None"

        automation_status = get_setting("automation_running", "true")

        return {
            "total_source_videos": total_source,
            "total_clips_generated": total_clips,
            "total_uploaded_videos": total_uploaded,
            "pending_uploads": pending_uploads,
            "failed_uploads": failed_uploads,
            "next_scheduled_upload": next_scheduled,
            "automation_running": automation_status == "true",
        }
    finally:
        conn.close()
