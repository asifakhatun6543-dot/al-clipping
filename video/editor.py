"""
AutoTube AI - Video Editing Engine
Converts clips into 1080x1920 vertical format with intelligent cropping,
audio normalization, background music mixing, and burnt karaoke subtitles.
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from core.config import config
from services.logger import log_info, log_error, log_warning


class VideoEditor:
    def __init__(self):
        self.ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
        self.target_width = config.target_width
        self.target_height = config.target_height

    def render_short_clip(
        self,
        source_video_path: str,
        start_time: float,
        duration: float,
        output_clip_path: str,
        subtitle_ass_path: Optional[str] = None,
        crop_mode: str = "smart",
        focal_center_x: float = 0.5,
        source_width: int = 1920,
        source_height: int = 1080,
        normalize_audio: bool = True,
        bg_music_path: Optional[str] = None,
        bg_music_volume: float = 0.12
    ) -> Path:
        """
        Renders a finished YouTube Short MP4 video.
        """
        out_path = Path(output_clip_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        src_path = Path(source_video_path)

        log_info("VideoEditor", f"Rendering clip ({duration:.1f}s) from {src_path.name} -> {out_path.name}")

        # Build video filter chain
        video_filters = []
        
        # Determine 9:16 framing
        is_horizontal = source_width >= source_height
        top_h = int(self.target_height * 0.45)
        bot_h = self.target_height - top_h

        if crop_mode == "split_gaming":
            # Viral Gaming Split-Screen: Streamer Reaction on Top, Gameplay on Bottom
            if is_horizontal:
                cam_w = int(source_width * 0.38)
                cam_h = int(source_height * 0.55)
                cam_x = int(source_width - cam_w) if focal_center_x > 0.45 else 0
                cam_y = 0
                vf_layout = (
                    "split=2[in_cam][in_game];"
                    f"[in_cam]crop={cam_w}:{cam_h}:{cam_x}:{cam_y},scale={self.target_width}:{top_h}:flags=lanczos,unsharp=3:3:0.6:3:3:0.0[cam];"
                    f"[in_game]crop={source_width}:{source_height}:0:0,scale={self.target_width}:{bot_h}:flags=lanczos,unsharp=3:3:0.6:3:3:0.0[game];"
                    f"[cam][game]vstack=inputs=2[stacked];"
                    f"[stacked]drawbox=y={top_h-2}:h=4:color=white@0.85:t=fill"
                )
            else:
                src_top_h = int(source_height * 0.45)
                src_bot_h = source_height - src_top_h
                vf_layout = (
                    "split=2[in_cam][in_game];"
                    f"[in_cam]crop={source_width}:{src_top_h}:0:0,scale={self.target_width}:{top_h}:flags=lanczos,unsharp=3:3:0.6:3:3:0.0[cam];"
                    f"[in_game]crop={source_width}:{src_bot_h}:0:{src_top_h},scale={self.target_width}:{bot_h}:flags=lanczos,unsharp=3:3:0.6:3:3:0.0[game];"
                    f"[cam][game]vstack=inputs=2[stacked];"
                    f"[stacked]drawbox=y={top_h-2}:h=4:color=white@0.85:t=fill"
                )
            video_filters.append(vf_layout)
        elif is_horizontal:
            if crop_mode == "blur_fill":
                # High-end Shorts blurred background layout
                vf_layout = (
                    "split=2[bg][fg];"
                    f"[bg]scale={self.target_width}:{self.target_height}:force_original_aspect_ratio=increase,"
                    f"crop={self.target_width}:{self.target_height},boxblur=25:5[blurred];"
                    f"[fg]scale={self.target_width}:-2[sharp];"
                    "[blurred][sharp]overlay=(W-w)/2:(H-h)/2"
                )
                video_filters.append(vf_layout)
            elif crop_mode == "smart":
                # Smart crop around subject focal center
                crop_w = int(source_height * (9.0 / 16.0))
                crop_w = crop_w - (crop_w % 2)
                x_center_px = int(focal_center_x * source_width)
                x_offset = max(0, min(source_width - crop_w, x_center_px - (crop_w // 2)))
                x_offset = x_offset - (x_offset % 2)
                vf_crop = f"crop={crop_w}:{source_height}:{x_offset}:0,scale={self.target_width}:{self.target_height}:flags=lanczos,unsharp=3:3:0.6:3:3:0.0"
                video_filters.append(vf_crop)
            else: # Center crop
                crop_w = int(source_height * (9.0 / 16.0))
                crop_w = crop_w - (crop_w % 2)
                vf_crop = f"crop={crop_w}:{source_height}:(in_w-{crop_w})/2:0,scale={self.target_width}:{self.target_height}:flags=lanczos,unsharp=3:3:0.6:3:3:0.0"
                video_filters.append(vf_crop)
        else:
            # Already vertical or square, scale and pad to 1080x1920
            vf_scale = f"scale={self.target_width}:{self.target_height}:force_original_aspect_ratio=decrease,pad={self.target_width}:{self.target_height}:(ow-iw)/2:(oh-ih)/2:black,unsharp=3:3:0.6:3:3:0.0"
            video_filters.append(vf_scale)

        # Append ASS subtitles if available
        working_dir = None
        if subtitle_ass_path and Path(subtitle_ass_path).exists():
            sub_file = Path(subtitle_ass_path).resolve()
            working_dir = str(sub_file.parent)
            # Use relative filename inside working_dir to eliminate Windows drive letter escaping bugs
            # e.g. subtitles='clip_1.ass'
            sub_name = sub_file.name
            video_filters.append(f"subtitles='{sub_name}'")

        vf_string = ",".join(video_filters)

        # Build FFmpeg command
        cmd = [
            self.ffmpeg_bin,
            "-y",
            "-ss", f"{start_time:.3f}",
            "-t", f"{duration:.3f}",
            "-i", str(src_path.resolve()),
        ]

        # Background music input
        has_bg_music = bg_music_path and Path(bg_music_path).exists()
        if has_bg_music:
            cmd.extend([
                "-stream_loop", "-1",  # loop background music seamlessly
                "-i", str(Path(bg_music_path).resolve())
            ])

        # Filter complex / Audio filtering
        if has_bg_music:
            # Normalize speech, mix with background music ducked at bg_music_volume
            af_filter = (
                f"[0:a]loudnorm=I={config.target_lufs}:LRA=7:tp=-1.5[a_speech];"
                f"[1:a]volume={bg_music_volume}[a_music];"
                f"[a_speech][a_music]amix=inputs=2:duration=first:dropout_transition=2[a_out]"
            )
            cmd.extend([
                "-filter_complex", f"[0:v]{vf_string}[v_out];{af_filter}",
                "-map", "[v_out]",
                "-map", "[a_out]"
            ])
        else:
            cmd.extend([
                "-vf", vf_string
            ])
            if normalize_audio:
                cmd.extend(["-af", f"loudnorm=I={config.target_lufs}:LRA=7:tp=-1.5"])

        # Output encoding settings - Crisp 60fps & visually lossless CRF 17
        cmd.extend([
            "-c:v", config.video_codec,
            "-preset", "medium",
            "-crf", "17",
            "-b:v", config.video_bitrate,
            "-maxrate", "12000k",
            "-bufsize", "24000k",
            "-r", str(config.fps),
            "-c:a", config.audio_codec,
            "-b:a", config.audio_bitrate,
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(out_path.resolve())
        ])

        try:
            res = subprocess.run(cmd, cwd=working_dir, capture_output=True, text=True)
            if res.returncode != 0:
                log_error("VideoEditor", f"FFmpeg render error: {res.stderr[-500:]}")
                raise RuntimeError(f"FFmpeg failed with exit code {res.returncode}")

            if not out_path.exists() or out_path.stat().st_size == 0:
                raise RuntimeError(f"Output file {out_path.name} was not created or is 0 bytes.")

            log_info("VideoEditor", f"Successfully rendered YouTube Short: {out_path.name} ({out_path.stat().st_size / (1024*1024):.2f} MB)")
            return out_path
        except Exception as e:
            log_error("VideoEditor", f"Failed to render clip: {e}")
            raise
