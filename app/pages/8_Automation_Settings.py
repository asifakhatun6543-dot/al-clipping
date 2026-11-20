"""
AutoTube AI - Automation & AI Processing Settings
Configure clipping algorithms, Whisper model, audio levels, and folder locations
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path on Streamlit Cloud & local
_ROOT_DIR = Path(__file__).resolve().parents[2]
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))


import streamlit as st
from database.db import get_all_settings, set_setting
from core.config import config
from app.ui_components import inject_custom_css, render_sidebar

inject_custom_css()
render_sidebar()

st.title("⚙️ Automation & AI Settings")
st.caption("Fine-tune clipping durations, framing modes, Whisper models, and audio normalization.")

current_settings = get_all_settings()

with st.form("settings_form"):
    st.subheader("⏱️ Clip Duration Parameters")
    c1, c2, c3 = st.columns(3)
    with c1:
        min_dur = st.number_input("Minimum Clip Duration (s):", min_value=10.0, max_value=30.0, value=float(current_settings.get("min_clip_duration", config.min_clip_duration)))
    with c2:
        max_dur = st.number_input("Maximum Clip Duration (s):", min_value=30.0, max_value=60.0, value=float(current_settings.get("max_clip_duration", config.max_clip_duration)))
    with c3:
        target_dur = st.number_input("Target Clip Duration (s):", min_value=15.0, max_value=55.0, value=float(current_settings.get("default_clip_duration", config.default_clip_duration)))

    max_clips = st.slider("Max Clips to Extract per Source Video:", 1, 10, int(current_settings.get("max_clips_per_video", config.max_clips_per_video)))

    st.markdown("---")
    st.subheader("📐 9:16 Vertical Framing & Subtitles")
    c4, c5 = st.columns(2)
    with c4:
        valid_modes = ["split_gaming", "smart", "blur_fill", "crop"]
        cur_mode = current_settings.get("crop_mode", config.crop_mode)
        mode_idx = valid_modes.index(cur_mode) if cur_mode in valid_modes else 0
        crop_mode = st.selectbox(
            "Intelligent Cropping & Layout Mode:",
            valid_modes,
            index=mode_idx,
            help="'split_gaming': Streamer reaction on TOP + Gameplay on BOTTOM (Viral Gaming Shorts). 'smart': auto-detects and centers on speaker/face. 'blur_fill': blurred mirror background Shorts style. 'crop': center crop."
        )
    with c5:
        whisper_size = st.selectbox(
            "Local Whisper Model Size (CPU Friendly):",
            ["tiny", "base", "small", "medium"],
            index=["tiny", "base", "small", "medium"].index(current_settings.get("whisper_model_size", config.whisper_model_size)),
            help="'base' is recommended: fast on CPU with high accuracy across languages."
        )

    karaoke_on = st.checkbox("Word-by-Word Karaoke Subtitles", value=(current_settings.get("karaoke_enabled", "true") == "true"))

    st.markdown("---")
    st.subheader("🔊 Audio & Background Music")
    c6, c7 = st.columns(2)
    with c6:
        norm_audio = st.checkbox("Normalize Speech Audio (-14 LUFS standard)", value=(current_settings.get("normalize_audio", "true") == "true"))
    with c7:
        bg_vol = st.slider("Background Music Ducking Volume (0.0 to 0.4):", 0.0, 0.4, float(current_settings.get("bg_music_volume", str(config.bg_music_volume))), step=0.02)

    st.markdown("---")
    st.subheader("🌐 Timezone")
    tz_input = st.text_input("Publishing Timezone (IANA string):", value=current_settings.get("timezone", config.timezone))

    submitted = st.form_submit_button("💾 Save All Settings", type="primary", use_container_width=True)
    if submitted:
        set_setting("min_clip_duration", str(min_dur))
        set_setting("max_clip_duration", str(max_dur))
        set_setting("default_clip_duration", str(target_dur))
        set_setting("max_clips_per_video", str(max_clips))
        set_setting("crop_mode", crop_mode)
        set_setting("whisper_model_size", whisper_size)
        set_setting("karaoke_enabled", "true" if karaoke_on else "false")
        set_setting("normalize_audio", "true" if norm_audio else "false")
        set_setting("bg_music_volume", str(bg_vol))
        set_setting("timezone", tz_input.strip())
        st.success("Configuration successfully updated and persisted to SQLite database!")
        st.rerun()
