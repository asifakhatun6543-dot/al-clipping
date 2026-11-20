"""
AutoTube AI - AI Clipping Studio
Interactive interface to trigger clipping from Web URLs (like AutoClip.dev) or Local Videos
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path on Streamlit Cloud & local
_ROOT_DIR = Path(__file__).resolve().parents[2]
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))


from pathlib import Path
import streamlit as st
from core.config import config
from database.db import list_source_videos, get_setting
from services.url_downloader import VideoURLDownloader
from video.clip_generator import ClipGenerationPipeline
from app.ui_components import inject_custom_css, render_sidebar

inject_custom_css()
render_sidebar()

st.title("✂ AI Clipping Studio")
st.caption("Generate viral 9:16 vertical shorts from Web URLs (YouTube, Vimeo) or Local Source Videos.")

url_downloader = VideoURLDownloader()

input_mode = st.radio(
    "Choose Input Source:",
    ["🔗 Web Video URL (YouTube / Online Video)", "📁 Local Library Video"],
    horizontal=True
)

target_video_path = None
cached_meta = None

if input_mode == "🔗 Web Video URL (YouTube / Online Video)":
    st.markdown("#### 🌐 Paste Video Link")
    input_url = st.text_input(
        "YouTube / Web Video URL:",
        placeholder="e.g. https://youtu.be/4gWOqYhxiko?si=DCo2kTxgAsW5hlGM"
    ).strip()

    if input_url:
        # Check session cache to prevent repeated fetching on every UI rerun
        cache_key = f"meta_{input_url}"
        if cache_key not in st.session_state:
            with st.spinner("⚡ Fetching video details..."):
                try:
                    st.session_state[cache_key] = url_downloader.extract_info(input_url)
                except Exception as e:
                    st.error(f"Could not load video: {e}")
                    st.session_state[cache_key] = None

        cached_meta = st.session_state.get(cache_key)

        if cached_meta:
            c_img, c_info = st.columns([3, 7])
            with c_img:
                if cached_meta.get("thumbnail"):
                    st.image(cached_meta["thumbnail"], use_container_width=True)
            with c_info:
                st.markdown(f"### {cached_meta['title']}")
                st.caption(
                    f"👤 Channel: **{cached_meta['uploader']}** | "
                    f"⏱ Duration: **{cached_meta['duration']:.1f}s** ({int(cached_meta['duration']//60)}m {int(cached_meta['duration']%60)}s)"
                )
else:
    sources = list_source_videos()
    if sources:
        source_options = {f"{s['file_name']} (ID: {s['id']}, {s['duration_seconds']:.1f}s)": s for s in sources}
        selected_label = st.selectbox("Select Source Video from Library:", list(source_options.keys()))
        selected_video = source_options[selected_label]
        target_video_path = selected_video["file_path"]
    else:
        st.warning("No local source videos found. Please select 'Web Video URL' above or drop files in `/videos/input/`.")

st.markdown("---")
st.markdown("### ⚙️ Shorts Generation Parameters")

c1, c2, c3 = st.columns(3)
with c1:
    target_dur = st.slider("Target Short Duration (seconds):", 15, 60, 35)
with c2:
    max_clips = st.slider("Max Shorts to Generate:", 1, 10, 3)
with c3:
    crop_mode = st.selectbox(
        "Vertical Framing Mode:",
        ["split_gaming", "smart", "blur_fill", "crop"],
        index=0,
        help="'split_gaming': Streamer reaction on TOP + Gameplay on BOTTOM (Viral Gaming Shorts). 'smart': Face-tracking horizontal centering. 'blur_fill': Mirror background Shorts style. 'crop': Center crop."
    )

c4, c5 = st.columns(2)
with c4:
    karaoke_on = st.checkbox("Word-by-Word Karaoke Subtitles", value=True)
with c5:
    auto_sched = st.checkbox("Automatically Add to Publishing Schedule", value=True)

# Main Execution Button
if st.button("🚀 Generate Shorts from Video Now", type="primary", use_container_width=True):
    pipeline = ClipGenerationPipeline()
    results = []

    if input_mode == "🔗 Web Video URL (YouTube / Online Video)":
        if not input_url:
            st.warning("Please enter a valid video URL first.")
            st.stop()

        with st.status("🔄 Processing Video...", expanded=True) as status:
            st.write("1. ⬇️ Downloading video stream in high quality...")
            prog_bar = st.progress(0.0)
            prog_txt = st.empty()

            def on_progress(d):
                if d.get("status") == "downloading":
                    total = d.get("total_bytes") or d.get("total_bytes_estimate") or 1
                    downloaded = d.get("downloaded_bytes") or 0
                    p = min(1.0, max(0.0, downloaded / total))
                    prog_bar.progress(p)
                    speed = (d.get("speed") or 0) / (1024 * 1024)
                    prog_txt.caption(f"Downloaded: {int(p * 100)}% ({speed:.1f} MB/s)")

            try:
                dest_path, _ = url_downloader.download_video(
                    input_url,
                    meta_info=cached_meta,
                    progress_callback=on_progress
                )
                prog_bar.progress(1.0)
                prog_txt.caption("✓ Download Complete!")
                st.write(f"✓ Video ready on disk: **{dest_path.name}**")
                target_video_path = str(dest_path)
            except Exception as de:
                status.update(label="❌ Download Failed", state="error")
                if "403" in str(de) or "Forbidden" in str(de) or "bot" in str(de):
                    st.error("❌ YouTube blocked this cloud download (HTTP 403 Forbidden / Anti-Bot check). Please use the '📤 Local File Upload' tab in Source Videos to upload the video directly, or add cookies.txt!")
                else:
                    st.error(f"Download error: {de}")
                st.stop()

            st.write("2. 🎙️ Local Speech Recognition (detecting spoken language & word timestamps)...")
            st.write("3. 🧠 Multimodal AI moment detection (isolating viral 15–60s hooks)...")
            st.write("4. 🎬 Rendering vertical 1080x1920 MP4 clips with karaoke captions & thumbnails...")

            try:
                results = pipeline.process_source_video(target_video_path, auto_schedule=auto_sched)
                status.update(label="✅ Shorts Generation Complete!", state="complete")
            except Exception as pe:
                status.update(label="❌ Processing Failed", state="error")
                st.error(f"Processing error: {pe}")
                st.stop()

    else:
        if not target_video_path:
            st.warning("Please select a video.")
            st.stop()

        with st.spinner("AI analyzing video, transcribing audio, and rendering vertical 9:16 shorts..."):
            try:
                results = pipeline.process_source_video(target_video_path, auto_schedule=auto_sched)
            except Exception as e:
                st.error(f"Clipping execution error: {e}")
                st.stop()

    if results:
        st.success(f"🎉 Successfully created {len(results)} YouTube Shorts!")
        for r in results:
            with st.expander(f"🎬 {r['title']} ({r['duration']:.1f}s) — AI Score: {r['score']}/100", expanded=True):
                col_v, col_t = st.columns([6, 4])
                with col_v:
                    if Path(r["file_path"]).exists():
                        st.video(r["file_path"])
                with col_t:
                    if Path(r["thumbnail_path"]).exists():
                        st.image(r["thumbnail_path"], caption="9:16 Hook Thumbnail", width=220)
    else:
        st.warning("No clips were generated. Check the video length or audio content.")
