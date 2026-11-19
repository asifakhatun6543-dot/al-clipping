"""
Unit Tests for AutoTube AI Moment Detection, Subtitles, Metadata & Scheduler
"""

import json
from pathlib import Path
from ai.moment_detection import MomentDetector
from ai.metadata import MetadataGenerator
from video.subtitles import SubtitleGenerator, format_ass_time
from youtube.scheduler import PublishingScheduler


def test_format_ass_time():
    assert format_ass_time(0.0) == "0:00:00.00"
    assert format_ass_time(65.5) == "0:01:05.50"
    assert format_ass_time(3600.0) == "1:00:00.00"


def test_moment_detection_with_transcript():
    detector = MomentDetector(min_duration=15.0, max_duration=60.0, target_duration=30.0, max_clips=2)
    
    # Mock transcript with questions and emotional hooks
    segments = [
        {"id": 1, "start": 0.0, "end": 10.0, "text": "Did you know that building an automated YouTube system is insane?", "words": []},
        {"id": 2, "start": 10.0, "end": 22.0, "text": "The secret is using local AI models so you never pay any subscriptions.", "words": []},
        {"id": 3, "start": 22.0, "end": 32.0, "text": "This completely changes video automation forever.", "words": []},
        {"id": 4, "start": 32.0, "end": 45.0, "text": "Next up, let's talk about why standard APIs cost too much money.", "words": []},
        {"id": 5, "start": 45.0, "end": 65.0, "text": "By running everything locally on your own computer, you keep 100% control.", "words": []}
    ]
    words = []
    t = 0.0
    for s in segments:
        for w in s["text"].split():
            words.append({"word": w, "start": t, "end": t + 0.4})
            t += 0.5

    transcript_data = {
        "language": "en",
        "segments": segments,
        "words": words
    }
    audio_energy = [(t, 0.8) for t in range(0, 70)]
    scene_cuts = [0.0, 20.0, 45.0]

    clips = detector.detect_moments(transcript_data, audio_energy, scene_cuts, video_duration=70.0)
    assert len(clips) >= 1
    for c in clips:
        assert 15.0 <= c["duration_seconds"] <= 60.0
        assert c["score"] > 0.0


def test_metadata_generator():
    gen = MetadataGenerator(default_category_id="24")
    text = "Why is this AI video clipping engine so fast? Here is the secret truth about zero subscription software."
    meta = gen.generate_metadata(text, source_title="AI Secrets", clip_number=1)
    
    assert "#Shorts" in meta["title"]
    assert len(meta["title"]) <= 100
    assert "Subscribe" in meta["description"]
    assert "#Shorts" in meta["hashtags"]
    assert len(meta["keywords"]) > 0


def test_subtitle_karaoke_ass_generation(tmp_path):
    sub_gen = SubtitleGenerator(font_name="Arial", font_size=48)
    words = [
        {"word": "HELLO", "start": 1.0, "end": 1.4},
        {"word": "WORLD", "start": 1.5, "end": 1.9},
        {"word": "AUTOTUBE", "start": 2.0, "end": 2.6},
        {"word": "AI", "start": 2.7, "end": 3.0}
    ]
    out_ass = tmp_path / "test_karaoke.ass"
    res_path = sub_gen.generate_karaoke_ass(words, str(out_ass), clip_start_offset=1.0)
    
    assert res_path.exists()
    content = res_path.read_text(encoding="utf-8")
    assert "[Script Info]" in content
    assert "KaraokeDefault" in content
    assert "Dialogue:" in content
    assert r"{\c" in content  # contains highlight color code


def test_publishing_scheduler_slot_calculation():
    sched = PublishingScheduler(tz_name="Asia/Kolkata")
    slot = sched.calculate_next_available_slot()
    assert slot is not None
    # Slot hour should match one of the configured daily slots
    slot_time_str = slot.strftime("%H:%M")
    configured_slots = sched.get_configured_slots()
    assert slot_time_str in configured_slots
