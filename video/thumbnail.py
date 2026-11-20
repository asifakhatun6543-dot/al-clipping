"""
AutoTube AI - Thumbnail Generator
Creates high-contrast, eye-catching 9:16 (1080x1920) YouTube Shorts thumbnails.
Combines smart frame selection, contrast enhancement, and readable hook text.
"""

from pathlib import Path
from typing import Optional, List
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
from core.config import config
from services.logger import log_info, log_error


class ThumbnailGenerator:
    def __init__(self, output_width: int = 1080, output_height: int = 1920):
        self.output_width = output_width
        self.output_height = output_height
        self.face_cascade = None
        if hasattr(cv2, "CascadeClassifier") and hasattr(cv2, "data") and hasattr(cv2.data, "haarcascades"):
            try:
                self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
            except Exception:
                self.face_cascade = None

    def generate_thumbnail(
        self,
        video_path: str,
        title_text: str,
        output_image_path: str,
        start_time: float = 0.0,
        duration: float = 30.0
    ) -> Path:
        """
        Extracts the most expressive, high-contrast frame from the clip and overlays
        bold, readable text and stylish badges.
        """
        out_path = Path(output_image_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        best_frame = self._select_best_frame(video_path, start_time, duration)
        if best_frame is None:
            # Fallback to generating a clean gradient background
            img = Image.new("RGB", (self.output_width, self.output_height), color=(20, 24, 33))
        else:
            img = self._prepare_background_image(best_frame)

        # Enhance color & sharpness slightly for mobile appeal
        img = ImageEnhance.Color(img).enhance(1.2)
        img = ImageEnhance.Contrast(img).enhance(1.15)

        # Add top and bottom subtle dark gradients for text contrast
        img = self._apply_dark_gradients(img)

        # Draw Title Hook and badge
        self._overlay_text_and_badge(img, title_text)

        # Save thumbnail
        img.save(str(out_path), "JPEG", quality=95)
        log_info("ThumbnailGenerator", f"Generated 9:16 thumbnail: {out_path.name}")
        return out_path

    def _select_best_frame(self, video_path: str, start_time: float, duration: float) -> Optional[np.ndarray]:
        """Samples frames across the clip and chooses the sharpest one with clear subject."""
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return None

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        sample_times = [
            start_time + (duration * 0.15),
            start_time + (duration * 0.35),
            start_time + (duration * 0.55),
            start_time + (duration * 0.75),
        ]

        best_score = -1.0
        best_frame = None

        for t in sample_times:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(t * fps))
            ret, frame = cap.read()
            if not ret or frame is None:
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # Sharpness metric: variance of Laplacian
            sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()

            # Face detection bonus
            face_bonus = 0.0
            if self.face_cascade:
                try:
                    faces = self.face_cascade.detectMultiScale(gray, 1.2, 5, minSize=(50, 50))
                    if len(faces) > 0:
                        face_bonus = 200.0
                except Exception:
                    pass

            total_score = sharpness + face_bonus
            if total_score > best_score:
                best_score = total_score
                best_frame = frame

        cap.release()
        return best_frame

    def _prepare_background_image(self, bgr_frame: np.ndarray) -> Image.Image:
        """Converts BGR OpenCV frame to 1080x1920 PIL Image with intelligent fit/crop."""
        rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        pil_frame = Image.fromarray(rgb_frame)

        fw, fh = pil_frame.size
        # Target 9:16 aspect ratio
        target_aspect = self.output_width / self.output_height
        frame_aspect = fw / fh

        if frame_aspect > target_aspect:
            # Horizontal video: Blur fill background with centered sharp crop
            bg = pil_frame.resize((self.output_width, self.output_height))
            bg = bg.filter(ImageFilter.GaussianBlur(radius=25))

            # Foreground scale to fit width
            fg_h = int(self.output_width / frame_aspect)
            fg = pil_frame.resize((self.output_width, fg_h), Image.Resampling.LANCZOS)
            y_offset = (self.output_height - fg_h) // 2
            bg.paste(fg, (0, y_offset))
            return bg
        else:
            # Vertical or tall: crop center to 1080x1920
            crop_h = int(fw / target_aspect)
            y_top = max(0, (fh - crop_h) // 2)
            cropped = pil_frame.crop((0, y_top, fw, y_top + crop_h))
            return cropped.resize((self.output_width, self.output_height), Image.Resampling.LANCZOS)

    def _apply_dark_gradients(self, img: Image.Image) -> Image.Image:
        """Applies smooth top and bottom vignettes to ensure text legibility."""
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        w, h = img.size

        # Top gradient (height ~ 400px)
        for y in range(450):
            alpha = int(180 * (1.0 - (y / 450)))
            draw.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))

        # Bottom gradient (height ~ 500px)
        for y in range(h - 500, h):
            alpha = int(210 * ((y - (h - 500)) / 500))
            draw.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))

        img = img.convert("RGBA")
        combined = Image.alpha_composite(img, overlay)
        return combined.convert("RGB")

    def _overlay_text_and_badge(self, img: Image.Image, text: str):
        """Draws a modern YouTube Shorts badge and high-contrast title banner."""
        draw = ImageDraw.Draw(img)
        w, h = img.size

        # Clean title text: first 5-8 words for thumbnail hook
        clean_text = text.replace("#Shorts", "").strip().upper()
        words = clean_text.split()
        if len(words) > 6:
            clean_text = " ".join(words[:6]) + "!"

        # Try loading system font, fallback to default
        font_size = 84
        font = None
        for font_candidate in ["impact.ttf", "arialbd.ttf", "arial.ttf", "segoeui.ttf"]:
            try:
                font = ImageFont.truetype(font_candidate, font_size)
                break
            except Exception:
                pass
        if font is None:
            font = ImageFont.load_default()

        # Word wrap text to 2 lines max
        lines = []
        words = clean_text.split()
        mid = len(words) // 2 if len(words) > 3 else len(words)
        if len(words) > 3:
            lines = [" ".join(words[:mid]), " ".join(words[mid:])]
        else:
            lines = [" ".join(words)]

        # Position text in upper-third (safe from YouTube Shorts bottom bar and right action buttons)
        y_cursor = 230

        # Draw red viral pill badge (e.g. GTA 6 EXCLUSIVE, MUST WATCH)
        badge_text = "🔴 GTA 6 EXCLUSIVE" if ("gta" in text.lower() or "speed" in text.lower()) else "🔴 MUST WATCH"
        badge_font = font
        try:
            badge_font = ImageFont.truetype("arialbd.ttf", 38)
        except Exception:
            pass

        bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
        bw = bbox[2] - bbox[0]
        bh = bbox[3] - bbox[1]
        badge_x = (w - bw) // 2
        badge_y = y_cursor - 75
        padding = 18
        draw.rounded_rectangle(
            [badge_x - padding, badge_y - padding // 2, badge_x + bw + padding, badge_y + bh + padding // 2],
            radius=12,
            fill=(255, 0, 50)  # Intense YouTube Red
        )
        draw.text((badge_x, badge_y), badge_text, font=badge_font, fill=(255, 255, 255))

        # Draw hook lines with bold dark stroke and vibrant yellow fill
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            lw = bbox[2] - bbox[0]
            lx = (w - lw) // 2
            
            # Thick black outline
            stroke_w = 8
            draw.text((lx, y_cursor), line, font=font, fill=(255, 222, 0), stroke_width=stroke_w, stroke_fill=(0, 0, 0))
            y_cursor += (bbox[3] - bbox[1]) + 28
