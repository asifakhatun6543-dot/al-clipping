"""
Integration Tests for Video Analysis, Rendering, and Thumbnail Generation
"""

import subprocess
import shutil
from pathlib import Path
import pytest
from core.config import config
from video.analyzer import VideoAnalyzer
from video.editor import VideoEditor
from video.thumbnail import ThumbnailGenerator
from video.subtitles import SubtitleGenerator


@pytest.fixture(scope="module")
def sample_video(tmp_path_factory):
    """Generates a synthetic 20-second test video with audio using FFmpeg."""
    tmp_dir = tmp_path_factory.mktemp("video_test")
    test_video_path = tmp_dir / "sample_source.mp4"
    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"

    # Create 20-second 1280x720 video with moving color and 440Hz beep audio
    cmd = [
        ffmpeg_bin,
        "-y",
        "-f", "lavfi",
        "-i", "testsrc=duration=20:size=1280x720:rate=30",
        "-f", "lavfi",
        "-i", "sine=frequency=440:duration=20",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-c:a", "aac",
        "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        str(test_video_path)
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    assert test_video_path.exists()
    return test_video_path


def test_video_analyzer_metadata(sample_video):
    analyzer = VideoAnalyzer(str(sample_video))
    meta = analyzer.get_metadata()
    assert meta["duration"] >= 19.5
    assert meta["width"] == 1280
    assert meta["height"] == 720
    assert meta["fps"] == 30.0
    assert meta["has_audio"] is True


def test_video_analyzer_audio_and_scenes(sample_video):
    analyzer = VideoAnalyzer(str(sample_video))
    energy = analyzer.analyze_audio_energy()
    assert len(energy) > 0
    cuts = analyzer.detect_scene_changes()
    assert len(cuts) >= 1


def test_thumbnail_generator(sample_video, tmp_path):
    thumb_gen = ThumbnailGenerator(output_width=1080, output_height=1920)
    out_thumb = tmp_path / "test_thumb.jpg"
    thumb_gen.generate_thumbnail(
        video_path=str(sample_video),
        title_text="INCREDIBLE SECRET REVEALED",
        output_image_path=str(out_thumb),
        start_time=2.0,
        duration=10.0
    )
    assert out_thumb.exists()
    assert out_thumb.stat().st_size > 5000  # valid image file

    from PIL import Image
    with Image.open(out_thumb) as img:
        assert img.size == (1080, 1920)


def test_video_editor_render_vertical_short(sample_video, tmp_path):
    # 1. Create a quick ASS karaoke subtitle
    sub_gen = SubtitleGenerator(font_name="Arial", font_size=40)
    words = [
        {"word": "TESTING", "start": 0.5, "end": 1.0},
        {"word": "AUTOTUBE", "start": 1.1, "end": 1.8},
        {"word": "SHORTS", "start": 1.9, "end": 2.5}
    ]
    sub_path = tmp_path / "clip.ass"
    sub_gen.generate_karaoke_ass(words, str(sub_path), clip_start_offset=0.0)

    # 2. Render vertical clip
    editor = VideoEditor()
    out_mp4 = tmp_path / "rendered_short.mp4"
    editor.render_short_clip(
        source_video_path=str(sample_video),
        start_time=0.0,
        duration=5.0,
        output_clip_path=str(out_mp4),
        subtitle_ass_path=str(sub_path),
        crop_mode="smart",
        focal_center_x=0.5,
        source_width=1280,
        source_height=720,
        normalize_audio=False
    )

    assert out_mp4.exists()
    assert out_mp4.stat().st_size > 10000

    # Probe rendered clip to verify vertical 1080x1920 dimensions
    probe_analyzer = VideoAnalyzer(str(out_mp4))
    rendered_meta = probe_analyzer.get_metadata()
    assert rendered_meta["width"] == 1080
    assert rendered_meta["height"] == 1920
    assert rendered_meta["duration"] >= 4.5
