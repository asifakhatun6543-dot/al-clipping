"""
AutoTube AI - Video & Audio Analyzer
Extracts technical metadata, audio loudness peaks, scene cuts, and visual focal centers
"""

import json
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import cv2
import numpy as np
from core.config import config
from services.logger import log_info, log_error, log_warning


class VideoAnalyzer:
    def __init__(self, video_path: str):
        self.video_path = Path(video_path)
        if not self.video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        self.ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"
        self.ffprobe_bin = shutil.which("ffprobe") or "ffprobe"
        
        # Load OpenCV Haar face detector if available
        self.face_cascade = None
        if hasattr(cv2, "CascadeClassifier") and hasattr(cv2, "data") and hasattr(cv2.data, "haarcascades"):
            try:
                haar_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
                self.face_cascade = cv2.CascadeClassifier(haar_path)
            except Exception:
                self.face_cascade = None

    def get_metadata(self) -> Dict[str, Any]:
        """Extracts container, video, and audio stream metadata using ffprobe."""
        cmd = [
            self.ffprobe_bin,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(self.video_path)
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            probe_data = json.loads(result.stdout)
            
            format_info = probe_data.get("format", {})
            duration = float(format_info.get("duration", 0.0))
            file_size = int(format_info.get("size", 0))
            
            video_stream = None
            audio_stream = None
            for stream in probe_data.get("streams", []):
                if stream.get("codec_type") == "video" and not video_stream:
                    video_stream = stream
                elif stream.get("codec_type") == "audio" and not audio_stream:
                    audio_stream = stream

            width = int(video_stream.get("width", 0)) if video_stream else 0
            height = int(video_stream.get("height", 0)) if video_stream else 0
            
            # FPS calculation
            fps = 30.0
            if video_stream and "r_frame_rate" in video_stream:
                num, den = video_stream["r_frame_rate"].split("/")
                if float(den) > 0:
                    fps = round(float(num) / float(den), 2)
            
            has_audio = audio_stream is not None

            return {
                "file_path": str(self.video_path),
                "file_name": self.video_path.name,
                "duration": duration,
                "file_size": file_size,
                "width": width,
                "height": height,
                "fps": fps,
                "has_audio": has_audio,
                "video_codec": video_stream.get("codec_name") if video_stream else None,
                "audio_codec": audio_stream.get("codec_name") if audio_stream else None
            }
        except Exception as e:
            log_error("VideoAnalyzer", f"Failed to probe metadata for {self.video_path.name}: {e}")
            raise

    def detect_scene_changes(self, threshold: float = 0.35, max_scenes: int = 50) -> List[float]:
        """
        Detects timestamps (seconds) where visual scene cuts happen using OpenCV histogram differences.
        """
        scene_cuts: List[float] = [0.0]
        cap = cv2.VideoCapture(str(self.video_path))
        if not cap.isOpened():
            log_warning("VideoAnalyzer", f"Cannot open video for scene detection: {self.video_path.name}")
            return scene_cuts

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        
        # Sample every 15 frames (~0.5s) to stay fast
        step = max(1, int(fps * 0.5))
        prev_hist = None
        frame_idx = 0

        while frame_idx < total_frames:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret or frame is None:
                break
            
            # Convert to HSV and calculate Hue histogram
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            hist = cv2.calcHist([hsv], [0, 1], None, [30, 32], [0, 180, 0, 256])
            cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)

            if prev_hist is not None:
                # Correlation distance (1 = identical, 0 = completely different)
                correlation = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL)
                if (1.0 - correlation) > threshold:
                    timestamp = round(frame_idx / fps, 2)
                    if not scene_cuts or (timestamp - scene_cuts[-1]) >= 2.0:
                        scene_cuts.append(timestamp)
                        if len(scene_cuts) >= max_scenes:
                            break

            prev_hist = hist
            frame_idx += step

        cap.release()
        return scene_cuts

    def analyze_audio_energy(self, sample_rate: int = 16000) -> List[Tuple[float, float]]:
        """
        Extracts audio RMS energy curve over time in 0.5s windows.
        Returns a list of (timestamp_seconds, normalized_energy).
        """
        temp_wav = config.base_dir / f"temp_energy_{self.video_path.stem}.wav"
        # Extract 16kHz mono audio
        cmd = [
            self.ffmpeg_bin,
            "-y",
            "-i", str(self.video_path),
            "-vn",
            "-ac", "1",
            "-ar", str(sample_rate),
            "-f", "wav",
            str(temp_wav)
        ]
        energy_curve: List[Tuple[float, float]] = []
        try:
            res = subprocess.run(cmd, capture_output=True, text=True)
            if not temp_wav.exists() or temp_wav.stat().st_size == 0:
                log_warning("VideoAnalyzer", f"No audio stream found or extraction failed for {self.video_path.name}")
                return energy_curve

            import wave
            with wave.open(str(temp_wav), "rb") as wf:
                n_frames = wf.getnframes()
                audio_bytes = wf.readframes(n_frames)
                samples = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)

            window_size = int(sample_rate * 0.5)  # 500ms
            if len(samples) == 0:
                return energy_curve

            # Compute RMS per window
            num_windows = len(samples) // window_size
            rms_values = []
            for w in range(num_windows):
                segment = samples[w * window_size : (w + 1) * window_size]
                rms = np.sqrt(np.mean(segment ** 2))
                rms_values.append(rms)

            if rms_values:
                max_rms = max(rms_values) or 1.0
                for w, rms in enumerate(rms_values):
                    t = round(w * 0.5, 2)
                    norm_energy = round(float(rms / max_rms), 3)
                    energy_curve.append((t, norm_energy))

        except Exception as e:
            log_warning("VideoAnalyzer", f"Audio energy analysis skipped: {e}")
        finally:
            if temp_wav.exists():
                try:
                    temp_wav.unlink()
                except Exception:
                    pass

        return energy_curve

    def detect_subject_focal_center(self, start_sec: float, duration_sec: float, sample_count: int = 10) -> float:
        """
        Samples frames within [start_sec, start_sec + duration_sec] and finds the average
        horizontal center of faces detected.
        Returns normalized center X in range [0.0, 1.0]. Defaults to 0.5 (center) if no face detected.
        """
        if not self.face_cascade:
            return 0.5

        cap = cv2.VideoCapture(str(self.video_path))
        if not cap.isOpened():
            return 0.5

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frame_width = cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1920.0
        step_sec = duration_sec / max(1, sample_count)
        
        centers: List[float] = []

        for i in range(sample_count):
            t = start_sec + (i * step_sec)
            target_frame = int(t * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            ret, frame = cap.read()
            if not ret or frame is None:
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(60, 60))
            if len(faces) > 0:
                # Take largest face
                largest_face = max(faces, key=lambda f: f[2] * f[3])
                x, y, w, h = largest_face
                face_center_x = (x + w / 2.0) / frame_width
                centers.append(face_center_x)

        cap.release()
        if centers:
            # Return median for stability against outliers
            return float(np.median(centers))
        return 0.5
