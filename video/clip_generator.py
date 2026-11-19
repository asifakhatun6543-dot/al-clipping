"""
AutoTube AI - End-to-End Clip Generation Engine
Orchestrates analysis, transcription, moment detection, vertical editing,
karaoke burning, thumbnail rendering, and metadata synthesis.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
from core.config import config
from database.db import (
    register_source_video,
    update_source_video_meta,
    update_source_video_status,
    create_clip,
    get_setting
)
from video.analyzer import VideoAnalyzer
from ai.transcription import SpeechTranscriber
from ai.moment_detection import MomentDetector
from video.subtitles import SubtitleGenerator
from video.editor import VideoEditor
from video.thumbnail import ThumbnailGenerator
from ai.metadata import MetadataGenerator
from youtube.scheduler import PublishingScheduler
from services.logger import log_info, log_error, log_warning, log_success
from services.notification import NotificationManager


class ClipGenerationPipeline:
    def __init__(self):
        self.transcriber = SpeechTranscriber()
        self.editor = VideoEditor()
        self.sub_gen = SubtitleGenerator()
        self.thumb_gen = ThumbnailGenerator()
        self.meta_gen = MetadataGenerator()
        self.scheduler = PublishingScheduler()

    def process_source_video(
        self,
        video_path: str,
        auto_schedule: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Processes a single source video completely from raw input to ready/scheduled clips.
        """
        path = Path(video_path)
        if not path.exists():
            raise FileNotFoundError(f"Source video not found: {video_path}")

        log_info("Pipeline", f"=== Beginning AutoTube processing for: {path.name} ===")
        NotificationManager.notify("Processing Started", f"Analyzing {path.name}")

        # 1. Register or get DB record
        video_id = register_source_video(
            file_path=str(path.resolve()),
            file_name=path.name,
            file_size_bytes=path.stat().st_size
        )
        update_source_video_status(video_id, "processing")

        try:
            # 2. Extract technical metadata & analysis
            analyzer = VideoAnalyzer(str(path))
            meta = analyzer.get_metadata()
            update_source_video_meta(
                video_id=video_id,
                duration=meta["duration"],
                width=meta["width"],
                height=meta["height"],
                fps=meta["fps"]
            )

            if meta["duration"] < 15.0:
                msg = f"Source video too short ({meta['duration']:.1f}s). Minimum 15s required."
                log_warning("Pipeline", msg)
                update_source_video_status(video_id, "failed", error_message=msg)
                return []

            # 3. Multimodal Analysis: Audio Energy & Scene Cuts
            log_info("Pipeline", "Extracting audio energy curve and visual scene cuts...")
            audio_energy = analyzer.analyze_audio_energy()
            scene_cuts = analyzer.detect_scene_changes()

            # 4. Local AI Speech Transcription
            transcript_data = self.transcriber.transcribe(str(path))
            detected_lang = transcript_data.get("language", "en")

            # 5. Intelligent Moment Detection
            min_dur = float(get_setting("min_clip_duration", str(config.min_clip_duration)))
            max_dur = float(get_setting("max_clip_duration", str(config.max_clip_duration)))
            target_dur = float(get_setting("default_clip_duration", str(config.default_clip_duration)))
            max_clips = int(get_setting("max_clips_per_video", str(config.max_clips_per_video)))

            detector = MomentDetector(
                min_duration=min_dur,
                max_duration=max_dur,
                target_duration=target_dur,
                max_clips=max_clips
            )
            selected_moments = detector.detect_moments(
                transcript_data=transcript_data,
                audio_energy=audio_energy,
                scene_cuts=scene_cuts,
                video_duration=meta["duration"]
            )

            if not selected_moments:
                msg = "No suitable clips found meeting duration and quality criteria."
                log_warning("Pipeline", msg)
                update_source_video_status(video_id, "failed", error_message=msg)
                return []

            # 6. Render and generate assets for each moment
            generated_clips = []
            crop_mode = get_setting("crop_mode", config.crop_mode)
            karaoke_enabled = get_setting("karaoke_enabled", "true") == "true"
            normalize_audio = get_setting("normalize_audio", "true") == "true"

            # Check for background music in videos/background_music/
            bg_music_files = list(config.music_dir.glob("*.mp3")) + list(config.music_dir.glob("*.wav"))
            selected_music = str(bg_music_files[0]) if bg_music_files else None

            for moment in selected_moments:
                clip_num = moment["clip_number"]
                start_t = moment["start_time"]
                end_t = moment["end_time"]
                dur = moment["duration_seconds"]
                score = moment["score"]
                clip_text = moment.get("text", "")
                words = moment.get("words", [])

                log_info("Pipeline", f"Processing Clip #{clip_num} [{start_t:.1f}s - {end_t:.1f}s] (Score: {score})")

                # a. AI Metadata generation
                meta_info = self.meta_gen.generate_metadata(
                    clip_text=clip_text if clip_text else path.stem,
                    source_title=path.stem,
                    clip_number=clip_num
                )

                # Output paths
                base_stem = f"{path.stem}_short_{clip_num}"
                out_clip_path = config.processed_dir / f"{base_stem}.mp4"
                out_thumb_path = config.thumbnails_dir / f"{base_stem}.jpg"
                ass_sub_path = config.processed_dir / f"{base_stem}.ass"

                # b. Word-by-Word Karaoke Subtitles (if enabled and words exist)
                sub_file_to_burn = None
                if karaoke_enabled and words:
                    sub_file_to_burn = str(self.sub_gen.generate_karaoke_ass(
                        words=words,
                        output_ass_path=str(ass_sub_path),
                        clip_start_offset=start_t
                    ))

                # c. Detect visual focal center for smart crop
                focal_center_x = 0.5
                if crop_mode == "smart":
                    focal_center_x = analyzer.detect_subject_focal_center(start_t, dur)

                # d. Render 1080x1920 Short MP4
                self.editor.render_short_clip(
                    source_video_path=str(path),
                    start_time=start_t,
                    duration=dur,
                    output_clip_path=str(out_clip_path),
                    subtitle_ass_path=sub_file_to_burn,
                    crop_mode=crop_mode,
                    focal_center_x=focal_center_x,
                    source_width=meta["width"],
                    source_height=meta["height"],
                    normalize_audio=normalize_audio,
                    bg_music_path=selected_music,
                    bg_music_volume=float(get_setting("bg_music_volume", str(config.bg_music_volume)))
                )

                # e. Generate High-Converting 9:16 Thumbnail
                self.thumb_gen.generate_thumbnail(
                    video_path=str(out_clip_path),
                    title_text=meta_info["title"],
                    output_image_path=str(out_thumb_path),
                    start_time=0.0,
                    duration=dur
                )

                # f. Insert Clip Record into Database
                clip_id = create_clip(
                    source_video_id=video_id,
                    clip_number=clip_num,
                    start_time=start_t,
                    end_time=end_t,
                    duration_seconds=dur,
                    title=meta_info["title"],
                    description=meta_info["description"],
                    keywords=meta_info["keywords"],
                    hashtags=meta_info["hashtags"],
                    category_id=meta_info["category_id"],
                    privacy=get_setting("default_privacy", config.default_privacy),
                    score=score,
                    file_path=str(out_clip_path.resolve()),
                    thumbnail_path=str(out_thumb_path.resolve()),
                    status="ready"
                )

                # g. Schedule for automated publishing if requested
                if auto_schedule:
                    scheduled_dt = self.scheduler.schedule_clip_for_publishing(clip_id)
                    log_info("Pipeline", f"Clip #{clip_num} queued for YouTube upload at {scheduled_dt.isoformat()}")

                generated_clips.append({
                    "clip_id": clip_id,
                    "title": meta_info["title"],
                    "file_path": str(out_clip_path),
                    "thumbnail_path": str(out_thumb_path),
                    "duration": dur,
                    "score": score
                })

            update_source_video_status(video_id, "completed")
            log_success("Pipeline", f"Successfully generated {len(generated_clips)} clips for {path.name}")
            NotificationManager.notify("Clipping Complete", f"Created {len(generated_clips)} shorts from {path.name}", level="success")
            return generated_clips

        except Exception as e:
            err_msg = f"Pipeline failure for {path.name}: {e}"
            log_error("Pipeline", err_msg)
            update_source_video_status(video_id, "failed", error_message=err_msg)
            NotificationManager.notify("Processing Error", err_msg, level="error")
            raise
