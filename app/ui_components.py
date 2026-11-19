"""
AutoTube AI - Shared UI Components & Luxury Dark Theme CSS
"""

import streamlit as st
from database.db import get_dashboard_stats, set_setting, get_setting
from core.automation import engine


def inject_custom_css():
    st.markdown(
        """
        <style>
        /* Import clean modern font */
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Plus Jakarta Sans', sans-serif;
        }

        /* Glassmorphism Cards */
        .glass-card {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.04) 0%, rgba(255, 255, 255, 0.01) 100%);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 16px;
            backdrop-filter: blur(10px);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }

        .metric-card {
            background: linear-gradient(135deg, rgba(22, 27, 34, 0.8) 0%, rgba(13, 17, 23, 0.9) 100%);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 14px;
            padding: 16px 20px;
            text-align: left;
            box-shadow: 0 4px 20px rgba(0,0,0,0.25);
        }

        .metric-label {
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            color: #8b949e;
            margin-bottom: 6px;
            font-weight: 600;
        }

        .metric-value {
            font-size: 28px;
            font-weight: 800;
            color: #f0f6fc;
            line-height: 1.2;
        }

        .metric-sub {
            font-size: 12px;
            color: #58a6ff;
            margin-top: 4px;
        }

        /* Status Pills */
        .status-pill {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            letter-spacing: 0.5px;
        }
        .status-active {
            background: rgba(46, 160, 67, 0.15);
            color: #3fb950;
            border: 1px solid rgba(46, 160, 67, 0.4);
        }
        .status-paused {
            background: rgba(210, 153, 34, 0.15);
            color: #d29922;
            border: 1px solid rgba(210, 153, 34, 0.4);
        }
        .status-failed {
            background: rgba(248, 81, 73, 0.15);
            color: #f85149;
            border: 1px solid rgba(248, 81, 73, 0.4);
        }

        /* YouTube Red Highlight */
        .yt-red {
            color: #ff0033;
            font-weight: 700;
        }

        /* Button Enhancements */
        .stButton>button {
            border-radius: 10px;
            font-weight: 600;
            transition: all 0.2s ease;
        }
        </style>
        """,
        unsafe_allow_html=True
    )


def render_sidebar():
    """Renders the common sidebar with system control and live status."""
    st.sidebar.markdown(
        """
        <div style="text-align: center; padding: 10px 0 20px 0;">
            <h2 style="margin: 0; font-size: 26px; font-weight: 800; letter-spacing: -0.5px;">
                <span style="color:#ff0033;">AutoTube</span> AI
            </h2>
            <p style="margin: 4px 0 0 0; font-size: 12px; color: #8b949e;">Autonomous Shorts Studio</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    stats = get_dashboard_stats()
    is_active = stats["automation_running"]

    st.sidebar.markdown("### ⚡ Engine Control")
    col1, col2, col3 = st.sidebar.columns(3)
    
    with col1:
        if st.button("▶ Start", key="btn_start_auto", use_container_width=True, disabled=is_active):
            engine.start()
            st.rerun()

    with col2:
        if st.button("⏸ Pause", key="btn_pause_auto", use_container_width=True, disabled=not is_active):
            engine.pause()
            st.rerun()

    with col3:
        if st.button("⏹ Stop", key="btn_stop_auto", use_container_width=True):
            engine.stop()
            st.rerun()

    status_html = (
        f'<div style="margin: 12px 0 20px 0; text-align: center;">'
        f'<span class="status-pill {"status-active" if is_active else "status-paused"}">'
        f'● {"AUTOMATION RUNNING" if is_active else "AUTOMATION PAUSED"}'
        f'</span></div>'
    )
    st.sidebar.markdown(status_html, unsafe_allow_html=True)

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Studio Pulse")
    st.sidebar.caption(f"📁 Source Videos: **{stats['total_source_videos']}**")
    st.sidebar.caption(f"✂ Clips Generated: **{stats['total_clips_generated']}**")
    st.sidebar.caption(f"🚀 Uploaded Shorts: **{stats['total_uploaded_videos']}**")
    st.sidebar.caption(f"⏳ In Queue: **{stats['pending_uploads']}**")
    st.sidebar.caption(f"⏰ Next: **{stats['next_scheduled_upload'][:20]}**")
    st.sidebar.markdown("---")
    st.sidebar.caption("AutoTube AI • Zero Recurring Investment • v1.0.0")
