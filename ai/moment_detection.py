"""
AutoTube AI - AI Moment Detection Engine
Finds the most engaging, viral, and context-complete segments for YouTube Shorts.
Combines sentence boundary analysis, hook detection, audio energy peaks, and scene transitions.
"""

import re
from typing import List, Dict, Any, Tuple
from core.config import config
from services.logger import log_info, log_warning

# High-engagement hook triggers common in viral Shorts
HOOK_WORDS = {
    "why", "how", "what", "secret", "never", "always", "best", "worst", "insane",
    "crazy", "mistake", "stop", "remember", "truth", "money", "dollar", "trick",
    "hack", "proven", "simple", "easy", "watch", "look", "listen", "believe",
    "unbelievable", "huge", "biggest", "first", "million", "billion", "rule"
}

QUESTION_STARTERS = (
    "why", "how", "what", "where", "who", "when", "is it", "can you", "did you know",
    "have you ever", "do you know", "would you"
)


class MomentDetector:
    def __init__(
        self,
        min_duration: float = 15.0,
        max_duration: float = 60.0,
        target_duration: float = 35.0,
        max_clips: int = 5
    ):
        self.min_duration = min_duration
        self.max_duration = max_duration
        self.target_duration = target_duration
        self.max_clips = max_clips

    def detect_moments(
        self,
        transcript_data: Dict[str, Any],
        audio_energy: List[Tuple[float, float]],
        scene_cuts: List[float],
        video_duration: float
    ) -> List[Dict[str, Any]]:
        """
        Analyzes multimodal inputs and produces ranked, non-overlapping engaging clips.
        """
        segments = transcript_data.get("segments", [])
        words = transcript_data.get("words", [])

        if segments and len(words) > 10:
            candidates = self._find_candidates_from_transcript(segments, words, video_duration)
        else:
            log_warning("MomentDetection", "Insufficient transcript words. Falling back to audio/visual energy peak windows.")
            candidates = self._find_candidates_from_energy_and_scenes(audio_energy, scene_cuts, video_duration)

        if not candidates:
            # Fallback to evenly spaced default windows if all else fails
            candidates = self._generate_fallback_windows(video_duration)

        # Score and rank candidates
        scored_clips = []
        for cand in candidates:
            score = self._score_candidate(cand, audio_energy, scene_cuts)
            cand["score"] = round(score, 2)
            scored_clips.append(cand)

        # Sort descending by score
        scored_clips.sort(key=lambda x: x["score"], reverse=True)

        # Filter overlapping clips to ensure diversity
        selected_clips: List[Dict[str, Any]] = []
        for clip in scored_clips:
            if len(selected_clips) >= self.max_clips:
                break
            
            # Check overlap with already selected clips
            is_overlap = False
            for sel in selected_clips:
                # If overlap is more than 5 seconds
                start_max = max(clip["start_time"], sel["start_time"])
                end_min = min(clip["end_time"], sel["end_time"])
                if end_min - start_max > 5.0:
                    is_overlap = True
                    break

            if not is_overlap:
                clip["clip_number"] = len(selected_clips) + 1
                selected_clips.append(clip)

        # Sort chronologically for nice publishing order
        selected_clips.sort(key=lambda x: x["start_time"])
        for idx, c in enumerate(selected_clips, 1):
            c["clip_number"] = idx

        log_info("MomentDetection", f"Selected {len(selected_clips)} high-quality moments from {video_duration:.1f}s source.")
        return selected_clips

    def _find_candidates_from_transcript(
        self,
        segments: List[Dict[str, Any]],
        all_words: List[Dict[str, Any]],
        video_duration: float
    ) -> List[Dict[str, Any]]:
        """Groups transcript segments into complete conversational ideas of valid Shorts duration."""
        candidates = []
        n_segs = len(segments)

        for i in range(n_segs):
            seg_start = segments[i]["start"]
            accumulated_text = []
            clip_words = []

            for j in range(i, n_segs):
                current_seg = segments[j]
                seg_end = current_seg["end"]
                duration = seg_end - seg_start

                accumulated_text.append(current_seg["text"])
                if "words" in current_seg and current_seg["words"]:
                    clip_words.extend(current_seg["words"])

                # Check if duration is in target window
                if duration >= self.min_duration:
                    if duration <= self.max_duration:
                        # Prefer ending on a full sentence boundary
                        text_str = " ".join(accumulated_text).strip()
                        ends_with_punct = text_str.endswith((".", "!", "?"))
                        
                        # Perfect duration match or natural sentence finish
                        if ends_with_punct or duration >= self.target_duration:
                            candidates.append({
                                "start_time": seg_start,
                                "end_time": seg_end,
                                "duration_seconds": round(duration, 2),
                                "text": text_str,
                                "words": [w for w in all_words if seg_start <= w["start"] <= seg_end],
                                "has_transcript": True
                            })
                    else:
                        break

        return candidates

    def _find_candidates_from_energy_and_scenes(
        self,
        audio_energy: List[Tuple[float, float]],
        scene_cuts: List[float],
        video_duration: float
    ) -> List[Dict[str, Any]]:
        """Generates candidates around audio loudness peaks and scene cuts."""
        candidates = []
        if not audio_energy:
            return self._generate_fallback_windows(video_duration)

        # Find timestamps with top 20% energy
        sorted_energy = sorted(audio_energy, key=lambda x: x[1], reverse=True)
        top_peaks = sorted_energy[:max(5, len(sorted_energy) // 5)]

        for t_peak, energy in top_peaks:
            # Center target_duration window around peak
            start = max(0.0, t_peak - (self.target_duration * 0.35))
            end = min(video_duration, start + self.target_duration)
            
            # Snap start/end to nearest scene cuts if close (within 2 seconds)
            for cut in scene_cuts:
                if abs(cut - start) <= 2.0:
                    start = cut
                if abs(cut - end) <= 2.0 and cut > start + self.min_duration:
                    end = cut

            dur = end - start
            if self.min_duration <= dur <= self.max_duration:
                candidates.append({
                    "start_time": round(start, 2),
                    "end_time": round(end, 2),
                    "duration_seconds": round(dur, 2),
                    "text": "",
                    "words": [],
                    "has_transcript": False
                })

        return candidates

    def _generate_fallback_windows(self, video_duration: float) -> List[Dict[str, Any]]:
        candidates = []
        step = max(self.target_duration, video_duration / max(1, self.max_clips))
        current = 0.0
        while current + self.min_duration <= video_duration:
            end = min(video_duration, current + self.target_duration)
            dur = end - current
            if dur >= self.min_duration:
                candidates.append({
                    "start_time": round(current, 2),
                    "end_time": round(end, 2),
                    "duration_seconds": round(dur, 2),
                    "text": "",
                    "words": [],
                    "has_transcript": False
                })
            current += step
        return candidates

    def _score_candidate(
        self,
        candidate: Dict[str, Any],
        audio_energy: List[Tuple[float, float]],
        scene_cuts: List[float]
    ) -> float:
        """Calculates a composite engagement score between 0.0 and 100.0."""
        score = 50.0  # Base score
        text = candidate.get("text", "").lower().strip()
        start = candidate["start_time"]
        end = candidate["end_time"]
        duration = candidate["duration_seconds"]

        # 1. Target duration proximity (ideal ~30-40s)
        dur_diff = abs(duration - self.target_duration)
        score += max(0.0, 15.0 - (dur_diff * 0.75))

        if text:
            # 2. Hook trigger words at the beginning (first 6 words)
            first_words = re.findall(r"\b\w+\b", text)[:8]
            has_starter = any(text.startswith(q) for q in QUESTION_STARTERS)
            if has_starter:
                score += 18.0

            hook_count = sum(1 for w in first_words if w in HOOK_WORDS)
            score += min(20.0, hook_count * 7.0)

            # 3. Overall semantic enthusiasm
            all_tokens = set(re.findall(r"\b\w+\b", text))
            viral_matches = len(all_tokens.intersection(HOOK_WORDS))
            score += min(15.0, viral_matches * 2.5)

            # 4. Sentence completeness (ends with punctuation)
            if text.endswith((".", "!", "?")):
                score += 10.0

            # 5. Word density (penalty if too slow or dead silence)
            wps = len(candidate.get("words", [])) / max(1.0, duration)
            if 1.8 <= wps <= 3.8:  # Good speaking cadence
                score += 8.0
            elif wps < 0.8:
                score -= 10.0

        # 6. Audio energy within the clip
        clip_energies = [e for t, e in audio_energy if start <= t <= end]
        if clip_energies:
            avg_energy = float(sum(clip_energies) / len(clip_energies))
            max_energy = float(max(clip_energies))
            score += (avg_energy * 10.0) + (max_energy * 8.0)

        # 7. Scene dynamics: having 1 to 4 scene cuts is optimal for retention
        cuts_in_clip = sum(1 for c in scene_cuts if start < c < end)
        if 1 <= cuts_in_clip <= 4:
            score += 8.0

        return max(5.0, min(99.0, score))
