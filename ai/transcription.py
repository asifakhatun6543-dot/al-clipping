"""
AutoTube AI - AI Transcription Engine
Extracts word-by-word timestamps, auto-detects spoken language, and identifies speech boundaries.
Powered by faster-whisper (local, 100% free, runs on CPU).
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from core.config import config
from services.logger import log_info, log_error, log_warning

# Global singleton to keep Whisper model loaded in memory for fast clipping
_whisper_model = None


def get_whisper_model(model_size: Optional[str] = None):
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model

    size = model_size or config.whisper_model_size
    log_info("Transcription", f"Loading local faster-whisper model '{size}' on {config.whisper_device} ({config.whisper_compute_type})...")
    
    try:
        from faster_whisper import WhisperModel
        # Download directory inside project cache or standard cache
        _whisper_model = WhisperModel(
            size,
            device=config.whisper_device,
            compute_type=config.whisper_compute_type,
            download_root=str(config.base_dir / ".cache" / "whisper")
        )
        log_info("Transcription", "Whisper model loaded successfully.")
        return _whisper_model
    except Exception as e:
        log_error("Transcription", f"Failed to load faster-whisper: {e}")
        return None


class SpeechTranscriber:
    def __init__(self, model_size: Optional[str] = None):
        self.model_size = model_size or config.whisper_model_size

    def transcribe(self, video_path: str) -> Dict[str, Any]:
        """
        Transcribes audio from video and returns full transcript, spoken language,
        sentence segments, and word-level karaoke timestamps.
        """
        model = get_whisper_model(self.model_size)
        if not model:
            log_warning("Transcription", "Model not available, returning empty transcript.")
            return {
                "language": "en",
                "language_probability": 0.0,
                "text": "",
                "segments": [],
                "words": []
            }

        log_info("Transcription", f"Starting speech transcription for: {Path(video_path).name}")
        try:
            segments_gen, info = model.transcribe(
                video_path,
                beam_size=5,
                word_timestamps=True,
                vad_filter=True, # Voice Activity Detection filters out silence
                vad_parameters=dict(min_silence_duration_ms=500)
            )

            detected_lang = info.language
            lang_prob = round(info.language_probability, 3)
            log_info("Transcription", f"Detected spoken language: '{detected_lang}' (confidence: {lang_prob*100:.1f}%)")

            all_segments: List[Dict[str, Any]] = []
            all_words: List[Dict[str, Any]] = []
            full_text_parts: List[str] = []

            for seg in segments_gen:
                seg_dict = {
                    "id": seg.id,
                    "start": round(seg.start, 2),
                    "end": round(seg.end, 2),
                    "text": seg.text.strip(),
                    "words": []
                }
                full_text_parts.append(seg.text.strip())

                if seg.words:
                    for w in seg.words:
                        w_dict = {
                            "word": w.word.strip(),
                            "start": round(w.start, 2),
                            "end": round(w.end, 2),
                            "probability": round(w.probability, 2)
                        }
                        seg_dict["words"].append(w_dict)
                        all_words.append(w_dict)

                all_segments.append(seg_dict)

            full_transcript = " ".join(full_text_parts)
            log_info("Transcription", f"Transcription completed. {len(all_segments)} segments, {len(all_words)} words.")

            return {
                "language": detected_lang,
                "language_probability": lang_prob,
                "text": full_transcript,
                "segments": all_segments,
                "words": all_words
            }
        except Exception as e:
            log_error("Transcription", f"Transcription error for {video_path}: {e}")
            return {
                "language": "en",
                "language_probability": 0.0,
                "text": "",
                "segments": [],
                "words": []
            }
