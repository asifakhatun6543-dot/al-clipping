"""
AutoTube AI - Source Videos Management
View, ingest, and inspect raw video sources
"""

import shutil
from pathlib import Path
import streamlit as st
from core.config import config
from database.db import list_source_videos, register_source_video
from app.ui_components import inject_custom_css, render_sidebar
from core.automation import engine

inject_custom_css()
render_sidebar()

st.title("📁 Source Videos Repository")
st.caption("Manage raw videos stored in `videos/input/`. Supports MP4, MOV, MKV, and WEBM.")

# Direct File Upload UI
with st.expander("📤 Add New Source Video", expanded=False):
    uploaded_file = st.file_uploader(
        "Upload a video file (properly licensed or user-owned):",
        type=["mp4", "mov", "mkv", "webm"]
    )
    if uploaded_file is not None:
        save_dest = config.input_dir / uploaded_file.name
        if st.button("Save & Queue for Clipping", key="btn_save_upload"):
            with open(save_dest, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success(f"Video saved to {save_dest.name}! It will be picked up by the automation engine.")
            st.rerun()

# Controls row
c1, c2 = st.columns([8, 2])
with c2:
    if st.button("🔄 Refresh List", use_container_width=True):
        st.rerun()

# List videos
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
    st.info("No source videos found. Place your video files in `videos/input/` or upload one above.")
