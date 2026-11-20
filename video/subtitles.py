"""
AutoTube AI - Word-by-Word Karaoke Subtitles Generator
Generates ASS (Advanced SubStation Alpha) subtitles with real-time word highlighting.
Designed for 1080x1920 vertical mobile YouTube Shorts.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
from core.config import config
from services.logger import log_info, log_error


def format_ass_time(seconds: float) -> str:
    """Formats seconds into ASS timestamp: H:MM:SS.cc"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds - int(seconds)) * 100))
    if centis >= 100:
        centis = 99
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"


class SubtitleGenerator:
    def __init__(
        self,
        font_name: str = "Impact",
        font_size: int = 58,
        primary_color: str = "&H00FFFFFF",    # Crisp White (AABBGGRR in ASS)
        highlight_color: str = "&H0000FFFF",  # Electric Neon Yellow (AABBGGRR)
        outline_color: str = "&H00000000",    # Solid Black
        outline_width: int = 6,
        shadow_depth: int = 3,
        alignment: int = 2,  # 2 = Bottom-Center in ASS
        margin_v: int = 880  # Positioned directly at center junction between reaction and gameplay
    ):
        self.font_name = font_name
        self.font_size = font_size
        self.primary_color = primary_color
        self.highlight_color = highlight_color
        self.outline_color = outline_color
        self.outline_width = outline_width
        self.shadow_depth = shadow_depth
        self.alignment = alignment
        self.margin_v = margin_v

    def generate_karaoke_ass(
        self,
        words: List[Dict[str, Any]],
        output_ass_path: str,
        clip_start_offset: float = 0.0,
        max_words_per_line: int = 2
    ) -> Path:
        """
        Creates an ASS subtitle file where each spoken word lights up dynamically
        in highlight color while the rest of the 3-4 word phrase remains white.
        """
        out_path = Path(output_ass_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Normalize word timestamps relative to clip start
        rel_words = []
        for w in words:
            rel_start = max(0.0, round(w["start"] - clip_start_offset, 2))
            rel_end = max(rel_start + 0.1, round(w["end"] - clip_start_offset, 2))
            clean_word = w["word"].strip().upper()  # Uppercase makes Shorts captions pop
            if clean_word:
                rel_words.append({
                    "word": clean_word,
                    "start": rel_start,
                    "end": rel_end
                })

        # ASS Script Header with vertical 1080x1920 PlayRes
        ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: KaraokeDefault,{self.font_name},{self.font_size},{self.primary_color},{self.highlight_color},{self.outline_color},&H80000000,-1,0,0,0,100,100,1,0,1,{self.outline_width},{self.shadow_depth},{self.alignment},60,60,{self.margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        dialogue_lines: List[str] = []

        # Group words into chunks of max_words_per_line
        chunks = [rel_words[i:i + max_words_per_line] for i in range(0, len(rel_words), max_words_per_line)]

        for chunk in chunks:
            if not chunk:
                continue
            chunk_start = chunk[0]["start"]
            chunk_end = chunk[-1]["end"]

            # For each word in the chunk, emit a dialogue event highlighting that specific word
            for active_idx, target_word in enumerate(chunk):
                w_start = target_word["start"]
                # Active until next word starts or chunk ends
                w_end = chunk[active_idx + 1]["start"] if active_idx + 1 < len(chunk) else target_word["end"]
                if w_end <= w_start:
                    w_end = w_start + 0.2

                # Assemble line text with active word highlighted
                styled_tokens = []
                for idx, w in enumerate(chunk):
                    if idx == active_idx:
                        # Highlighted word with vibrant color and slight scaling
                        styled_tokens.append(r"{\c" + self.highlight_color + r"\fscx108\fscy108}" + w["word"] + r"{\rKaraokeDefault}")
                    else:
                        styled_tokens.append(w["word"])

                text_line = " ".join(styled_tokens)
                line_str = f"Dialogue: 0,{format_ass_time(w_start)},{format_ass_time(w_end)},KaraokeDefault,,0,0,0,,{text_line}"
                dialogue_lines.append(line_str)

        # Write file
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(ass_header)
            f.write("\n".join(dialogue_lines))
            f.write("\n")

        log_info("Subtitles", f"Generated karaoke subtitles ASS: {out_path.name} ({len(dialogue_lines)} events)")
        return out_path
