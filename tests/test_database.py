"""
Unit Tests for AutoTube AI Database Layer
"""

import os
import pytest
from pathlib import Path
from database.db import (
    init_db,
    register_source_video,
    get_source_video,
    update_source_video_status,
    create_clip,
    get_clip,
    list_clips,
    add_to_schedule,
    get_due_schedule_items,
    record_upload,
    list_upload_history,
    get_setting,
    set_setting,
    get_dashboard_stats
)


@pytest.fixture(scope="module")
def test_db(tmp_path_factory):
    db_file = tmp_path_factory.mktemp("data") / "test_autotube.db"
    init_db(db_file)
    from core.config import config
    orig_path = config.db_path
    config.db_path = db_file
    yield db_file
    config.db_path = orig_path


def test_source_video_registration(test_db):
    vid_id = register_source_video(
        file_path="C:/videos/test1.mp4",
        file_name="test1.mp4",
        duration_seconds=120.5,
        width=1920,
        height=1080,
        fps=30.0
    )
    assert vid_id is not None
    vid = get_source_video(vid_id)
    assert vid["file_name"] == "test1.mp4"
    assert vid["status"] == "pending"

    # Duplicate check: should return existing id
    dup_id = register_source_video(file_path="C:/videos/test1.mp4", file_name="test1.mp4")
    assert dup_id == vid_id


def test_clip_creation_and_listing(test_db):
    vid_id = register_source_video(file_path="C:/videos/test2.mp4", file_name="test2.mp4")
    clip_id = create_clip(
        source_video_id=vid_id,
        clip_number=1,
        start_time=10.0,
        end_time=45.0,
        duration_seconds=35.0,
        title="Why AI Is Insane ⚡ #Shorts",
        description="Check this out!",
        keywords="ai, tech",
        hashtags="#Shorts #AI",
        score=88.5
    )
    assert clip_id is not None
    clip = get_clip(clip_id)
    assert clip["title"] == "Why AI Is Insane ⚡ #Shorts"
    assert clip["score"] == 88.5

    clips = list_clips()
    assert len(clips) >= 1


def test_scheduling_and_due_items(test_db):
    vid_id = register_source_video(file_path="C:/videos/test3.mp4", file_name="test3.mp4")
    clip_id = create_clip(
        source_video_id=vid_id,
        clip_number=1,
        start_time=0.0,
        end_time=30.0,
        duration_seconds=30.0,
        title="Scheduled Short #Shorts",
        description="Testing schedule queue",
        keywords="test",
        hashtags="#Shorts",
        file_path="C:/videos/clip.mp4"
    )
    
    # Schedule for past time to test due items
    sched_id = add_to_schedule(clip_id, "2020-01-01T09:00:00+05:30")
    assert sched_id is not None

    due = get_due_schedule_items("2025-01-01T00:00:00")
    assert len(due) >= 1
    assert any(d["clip_id"] == clip_id for d in due)


def test_upload_recording_and_dashboard_stats(test_db):
    vid_id = register_source_video(file_path="C:/videos/test4.mp4", file_name="test4.mp4")
    clip_id = create_clip(
        source_video_id=vid_id,
        clip_number=1,
        start_time=0.0,
        end_time=30.0,
        duration_seconds=30.0,
        title="Uploaded Short #Shorts",
        description="",
        keywords="",
        hashtags=""
    )
    add_to_schedule(clip_id, "2020-01-01T12:00:00")

    rec_id = record_upload(
        clip_id=clip_id,
        youtube_video_id="abc123xyz",
        title="Uploaded Short #Shorts",
        youtube_url="https://youtube.com/shorts/abc123xyz"
    )
    assert rec_id is not None
    history = list_upload_history()
    assert any(h["youtube_video_id"] == "abc123xyz" for h in history)

    stats = get_dashboard_stats()
    assert stats["total_uploaded_videos"] >= 1
