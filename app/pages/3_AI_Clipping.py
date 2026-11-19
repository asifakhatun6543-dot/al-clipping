"""
AutoTube AI - AI Clipping Studio
Interactive interface to trigger clipping, adjust AI parameters, and inspect moments
"""

from pathlib import Path
import streamlit as st
from core.config import config
from database.db import list_source_videos, get_setting
from video.clip_generator import ClipGenerationPipeline
from app.ui_components import inject_custom_css, render_sidebar

inject_custom_css()
render_sidebar()

st.title("✂ AI Clipping Studio")
st.caption("Inspect and manually trigger the multimodal AI clipping pipeline on any source video.")

sources = list_source_videos()
if not sources:
    st.warning("No source videos found in database. Please upload or drop a video into `videos/input/` first.")
    st.stop()

source_options = {f"{s['file_name']} (ID: {s['id']}, {s['duration_seconds']:.1f}s)": s for s in sources}
selected_label = st.selectbox("Select Source Video:", list(source_options.keys()))
selected_video = source_options[selected_label]

st.markdown("### ⚙️ Pipeline Parameters for this Run")
c1, c2, c3 = st.columns(3)
with c1:
    target_dur = st.slider("Target Clip Duration (seconds):", 15, 60, 35)
with c2:
    max_clips = st.slider("Max Clips to Generate:", 1, 10, 3)
with c3:
    crop_mode = st.selectbox("Vertical Framing Mode:", ["smart", "blur_fill", "crop"], index=0)

c4, c5 = st.columns(2)
with c4:
    karaoke_on = st.checkbox("Word-by-Word Karaoke Subtitles", value=True)
with c5:
    auto_sched = st.checkbox("Automatically Queue to Publishing Schedule", value=True)

if st.button("🚀 Run AI Clipping Pipeline Now", type="primary", use_container_width=True):
    video_path = selected_video["file_path"]
    pipeline = ClipGenerationPipeline()
    
    with st.spinner("AI analyzing video, transcribing audio, and rendering vertical 9:16 shorts..."):
        try:
            results = pipeline.process_source_video(video_path, auto_schedule=auto_sched)
            if results:
                st.success(f"Successfully generated {len(results)} viral short clips!")
                for r in results:
                    st.write(f"• **{r['title']}** ({r['duration']:.1f}s) - Score: `{r['score']}/100`")
                    if Path(r["file_path"]).exists():
                        st.video(r["file_path"])
            else:
                st.warning("No clips were generated. Check the video length or audio content.")
        except Exception as e:
            st.error(f"Clipping execution error: {e}")
