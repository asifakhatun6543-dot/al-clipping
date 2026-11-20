"""
AutoTube AI - Source Videos Management
View, ingest, and inspect video sources from Local Files or Web URLs (YouTube, Vimeo, etc.)
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path on Streamlit Cloud & local
_ROOT_DIR = Path(__file__).resolve().parents[2]
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))


import shutil
from pathlib import Path
import streamlit as st
from core.config import config
from database.db import list_source_videos, register_source_video
from services.url_downloader import VideoURLDownloader
from video.clip_generator import ClipGenerationPipeline
from app.ui_components import inject_custom_css, render_sidebar
from core.automation import engine

inject_custom_css()
render_sidebar()

st.title("📁 Source Videos Repository")
st.caption("Manage source videos. Ingest raw files or import directly from YouTube & Web URLs.")

url_downloader = VideoURLDownloader()

# Ingest Options: URL vs File Upload
st.markdown("### 📥 Ingest New Video")
tab_url, tab_upload = st.tabs(["🔗 Import from Video URL (YouTube, Vimeo, etc.)", "📤 Local File Upload"])

with tab_url:
    st.write("Paste any public YouTube, Vimeo, or web video link (like autoclip.dev):")
    col_input, col_action = st.columns([8, 2])
    with col_input:
        video_url = st.text_input(
            "Video URL:",
            placeholder="e.g. https://youtu.be/4gWOqYhxiko or https://www.youtube.com/watch?v=...",
            label_visibility="collapsed"
        )
    with col_action:
        fetch_preview = st.button("🔍 Fetch Preview", use_container_width=True)

    if video_url.strip():
        cache_key = f"meta_{video_url.strip()}"
        if cache_key not in st.session_state:
            try:
                with st.spinner("⚡ Fetching video details..."):
                    st.session_state[cache_key] = url_downloader.extract_info(video_url.strip())
            except Exception as e:
                st.error(f"Could not load video: {e}")
                st.session_state[cache_key] = None

        info = st.session_state.get(cache_key)
        if info:
            # Display preview card
            col_thumb, col_details = st.columns([3, 7])
            with col_thumb:
                if info.get("thumbnail"):
                    st.image(info["thumbnail"], use_container_width=True)
            with col_details:
                st.markdown(f"#### {info['title']}")
                st.caption(f"👤 Channel: **{info['uploader']}** | ⏱ Duration: **{int(info['duration']//60)}m {int(info['duration']%60)}s** ({info['duration']:.1f}s)")
                
                btn_c1, btn_c2 = st.columns(2)
                with btn_c1:
                    if st.button("⬇️ Download to Input Folder", type="secondary", use_container_width=True):
                        try:
                            with st.spinner("Downloading video in high quality..."):
                                dest_path, _ = url_downloader.download_video(video_url.strip(), meta_info=info)
                                st.success(f"Downloaded: {dest_path.name}! It has been added to the clipping queue.")
                                st.rerun()
                        except Exception as err:
                            if "403" in str(err) or "Forbidden" in str(err) or "bot" in str(err):
                                st.error("❌ YouTube blocked this cloud download (HTTP 403 Forbidden / Bot Check). Please upload the video directly via the '📤 Local File Upload' tab above, or add cookies.txt below!")
                            else:
                                st.error(f"Download error: {err}")

                with btn_c2:
                    if st.button("✂️ Download & Clip into Shorts Instantly", type="primary", use_container_width=True):
                        try:
                            with st.spinner("Downloading video..."):
                                dest_path, _ = url_downloader.download_video(video_url.strip(), meta_info=info)
                            with st.spinner("AI transcribing, clipping, adding karaoke subtitles & rendering vertical 9:16 shorts..."):
                                pipeline = ClipGenerationPipeline()
                                results = pipeline.process_source_video(str(dest_path), auto_schedule=True)
                                st.success(f"🎉 Generated {len(results)} viral short clips from URL!")
                                st.rerun()
                        except Exception as err:
                            if "403" in str(err) or "Forbidden" in str(err) or "bot" in str(err):
                                st.error("❌ YouTube blocked this cloud download (HTTP 403 Forbidden / Bot Check). Please upload the video directly via the '📤 Local File Upload' tab above, or add cookies.txt below!")
                            else:
                                st.error(f"Download error: {err}")

    with st.expander("🛡️ YouTube 403 Forbidden / Anti-Bot Fix (Click Here)"):
        st.markdown("""
        **Why does HTTP Error 403 Forbidden happen?**  
        YouTube blocks cloud servers (Streamlit Cloud / AWS) from scraping video streams directly without user session verification.
        
        **How to bypass it easily:**
        1. **Recommended (Instant & 100% Reliable):** Download the video file and upload it in the **'📤 Local File Upload'** tab above. AutoTube will clip it instantly in full 60fps Split Gaming layout!
        2. **Automatic Link Download (with cookies):** Export your YouTube cookies using the free Chrome/Edge extension *"Get cookies.txt LOCALLY"* and upload the `cookies.txt` file below:
        """)
        cookie_file_up = st.file_uploader("Upload cookies.txt:", type=["txt"], key="cookie_uploader")
        if cookie_file_up is not None:
            if st.button("💾 Save cookies.txt", key="btn_save_cookie"):
                with open(config.base_dir / "cookies.txt", "wb") as f:
                    f.write(cookie_file_up.getbuffer())
                st.success("✅ cookies.txt saved! YouTube downloads are now verified.")
                st.rerun()

with tab_upload:
    uploaded_file = st.file_uploader(
        "Upload a video file from your computer (MP4, MOV, MKV, WEBM):",
        type=["mp4", "mov", "mkv", "webm"]
    )
    if uploaded_file is not None:
        save_dest = config.input_dir / uploaded_file.name
        if st.button("Save & Queue for Clipping", key="btn_save_upload"):
            with open(save_dest, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success(f"Video saved to {save_dest.name}! It will be picked up by the automation engine.")
            st.rerun()

st.markdown("---")

# List existing source videos
c1, c2 = st.columns([8, 2])
with c1:
    st.markdown("### 📋 Source Video Catalog")
with c2:
    if st.button("🔄 Refresh List", use_container_width=True):
        st.rerun()

videos = list_source_videos(limit=100)

if videos:
    for vid in videos:
        with st.container():
            st.markdown(
                f"""
                <div class="glass-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h4 style="margin: 0; color: #f0f6fc;">{vid['file_name']}</h4>
                            <p style="margin: 4px 0 0 0; font-size: 13px; color: #8b949e;">
                                Resolution: <b>{vid['width']}x{vid['height']}</b> | Duration: <b>{vid['duration_seconds']:.1f}s</b> | FPS: <b>{vid['fps']}</b> | Size: <b>{vid['file_size_bytes'] / (1024*1024):.1f} MB</b>
                            </p>
                        </div>
                        <div>
                            <span class="status-pill {'status-active' if vid['status'] == 'completed' else ('status-failed' if vid['status'] == 'failed' else 'status-paused')}">
                                {vid['status'].upper()}
                            </span>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
else:
    st.info("No source videos found. Paste a video URL above or place files in `videos/input/`.")
