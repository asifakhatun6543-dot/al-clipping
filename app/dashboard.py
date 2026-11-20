"""
AutoTube AI - Main Dashboard App
Production-ready Streamlit application for automated YouTube Shorts clipping & publishing
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path for Streamlit Cloud & local execution
_ROOT_DIR = Path(__file__).resolve().parents[1]
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))

import streamlit as st
from database.db import get_dashboard_stats, list_clips, list_source_videos, get_recent_logs
from app.ui_components import inject_custom_css, render_sidebar
from core.automation import engine

# Page configuration
st.set_page_config(
    page_title="AutoTube AI - YouTube Shorts Studio",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Start engine in background if not already started
try:
    if not engine.is_running():
        engine.start()
except Exception:
    pass

inject_custom_css()
render_sidebar()

# Main Header
st.markdown(
    """
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px;">
        <div>
            <h1 style="margin: 0; font-size: 32px; font-weight: 800;">
                <span style="color: #ff0033;">AutoTube</span> AI Studio
            </h1>
            <p style="margin: 4px 0 0 0; color: #8b949e; font-size: 15px;">
                Fully Autonomous AI Video Clipping, Karaoke Subtitles & YouTube Shorts Publishing
            </p>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

stats = get_dashboard_stats()

# Top 6 KPI Metric Cards
c1, c2, c3, c4, c5, c6 = st.columns(6)

with c1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Source Videos</div>
            <div class="metric-value">{stats['total_source_videos']}</div>
            <div class="metric-sub">Input folder</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with c2:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Clips Created</div>
            <div class="metric-value">{stats['total_clips_generated']}</div>
            <div class="metric-sub">9:16 vertical</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with c3:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Published Shorts</div>
            <div class="metric-value" style="color: #3fb950;">{stats['total_uploaded_videos']}</div>
            <div class="metric-sub">Live on YouTube</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with c4:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">In Queue</div>
            <div class="metric-value" style="color: #58a6ff;">{stats['pending_uploads']}</div>
            <div class="metric-sub">Scheduled</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with c5:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Failed Uploads</div>
            <div class="metric-value" style="color: #f85149;">{stats['failed_uploads']}</div>
            <div class="metric-sub">Auto-retry active</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with c6:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">Next Slot</div>
            <div class="metric-value" style="font-size: 16px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                {stats['next_scheduled_upload'][:16]}
            </div>
            <div class="metric-sub">Auto publishing</div>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

# Main Dashboard 2-column layout
col_left, col_right = st.columns([7, 5])

with col_left:
    st.markdown("### 🎬 Recent Generated Shorts")
    recent_clips = list_clips(limit=4)
    if recent_clips:
        for clip in recent_clips:
            with st.container():
                st.markdown(
                    f"""
                    <div class="glass-card" style="display: flex; gap: 16px; align-items: center;">
                        <div style="flex-grow: 1;">
                            <div style="font-size: 16px; font-weight: 700; color: #f0f6fc; margin-bottom: 4px;">
                                {clip['title']}
                            </div>
                            <div style="font-size: 13px; color: #8b949e; margin-bottom: 8px;">
                                Duration: <b>{clip['duration_seconds']:.1f}s</b> | AI Score: <b>{clip['score']}/100</b> | Privacy: <b>{clip['privacy'].upper()}</b>
                            </div>
                            <div>
                                <span class="status-pill {'status-active' if clip['status'] == 'uploaded' else 'status-paused'}">
                                    ● {clip['status'].upper()}
                                </span>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
    else:
        st.info("No clips generated yet. Drop source videos in `/videos/input/` or click 'Process New Video' in AI Clipping tab.")

with col_right:
    st.markdown("### 📡 Live Engine Activity")
    recent_logs = get_recent_logs(limit=6)
    if recent_logs:
        for l in recent_logs:
            lvl = l["level"]
            color = "#3fb950" if lvl == "SUCCESS" else ("#f85149" if lvl == "ERROR" else ("#d29922" if lvl == "WARNING" else "#58a6ff"))
            st.markdown(
                f"""
                <div style="padding: 10px 14px; border-radius: 8px; background: rgba(255,255,255,0.02); border-left: 3px solid {color}; margin-bottom: 8px; font-size: 13px;">
                    <span style="color: {color}; font-weight: 700;">[{lvl}]</span> 
                    <span style="color: #8b949e;">{l['created_at'][11:19]}</span>
                    <b>[{l['module']}]</b> {l['message']}
                </div>
                """,
                unsafe_allow_html=True
            )
    else:
        st.caption("No log events yet.")
