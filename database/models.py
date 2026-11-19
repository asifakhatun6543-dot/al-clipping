"""
AutoTube AI - Database Models & Schema Definitions
Lightweight SQLite relational schemas for zero-cost operation
"""

CREATE_TABLES_SQL = """
-- Source Videos tracking
CREATE TABLE IF NOT EXISTS source_videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT UNIQUE NOT NULL,
    file_name TEXT NOT NULL,
    file_size_bytes INTEGER DEFAULT 0,
    duration_seconds REAL DEFAULT 0,
    width INTEGER DEFAULT 0,
    height INTEGER DEFAULT 0,
    fps REAL DEFAULT 0,
    status TEXT DEFAULT 'pending', -- pending, processing, analyzed, completed, failed
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Generated Short Clips
CREATE TABLE IF NOT EXISTS generated_clips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_video_id INTEGER NOT NULL,
    clip_number INTEGER DEFAULT 1,
    start_time REAL NOT NULL,
    end_time REAL NOT NULL,
    duration_seconds REAL NOT NULL,
    file_path TEXT,
    thumbnail_path TEXT,
    title TEXT NOT NULL,
    description TEXT,
    keywords TEXT, -- comma-separated or JSON
    hashtags TEXT, -- e.g. #Shorts #Viral
    category_id TEXT DEFAULT '24',
    privacy TEXT DEFAULT 'private',
    score REAL DEFAULT 0.0, -- AI engagement rating
    status TEXT DEFAULT 'ready', -- ready, scheduled, uploading, uploaded, failed
    scheduled_time TIMESTAMP,
    youtube_video_id TEXT,
    youtube_url TEXT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(source_video_id) REFERENCES source_videos(id) ON DELETE CASCADE
);

-- Publishing Schedule Queue
CREATE TABLE IF NOT EXISTS publishing_schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clip_id INTEGER NOT NULL UNIQUE,
    scheduled_time TIMESTAMP NOT NULL,
    timezone TEXT DEFAULT 'Asia/Kolkata',
    status TEXT DEFAULT 'pending', -- pending, processing, published, failed, cancelled
    retry_count INTEGER DEFAULT 0,
    last_attempt_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(clip_id) REFERENCES generated_clips(id) ON DELETE CASCADE
);

-- YouTube Upload History
CREATE TABLE IF NOT EXISTS upload_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    clip_id INTEGER NOT NULL,
    youtube_video_id TEXT NOT NULL,
    title TEXT NOT NULL,
    youtube_url TEXT NOT NULL,
    privacy TEXT DEFAULT 'private',
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'success',
    raw_response TEXT,
    FOREIGN KEY(clip_id) REFERENCES generated_clips(id)
);

-- Application Settings Key-Value Store
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Activity & Processing Logs
CREATE TABLE IF NOT EXISTS processing_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level TEXT NOT NULL, -- INFO, WARNING, ERROR, SUCCESS
    module TEXT NOT NULL,
    message TEXT NOT NULL,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_source_status ON source_videos(status);
CREATE INDEX IF NOT EXISTS idx_clip_status ON generated_clips(status);
CREATE INDEX IF NOT EXISTS idx_schedule_time ON publishing_schedule(scheduled_time, status);
CREATE INDEX IF NOT EXISTS idx_logs_created ON processing_logs(created_at DESC);
"""
