"""
AutoTube AI - Overview Page
High-level studio diagnostics and real-time status
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path on Streamlit Cloud & local
_ROOT_DIR = Path(__file__).resolve().parents[2]
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))


import streamlit as st
from database.db import get_dashboard_stats, list_source_videos, list_clips, list_upload_history
from app.ui_components import inject_custom_css, render_sidebar

inject_custom_css()
render_sidebar()

st.title("📊 Studio Overview & System Health")
stats = get_dashboard_stats()

# Top KPI metrics
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Total Source Videos", stats["total_source_videos"])
with c2:
    st.metric("Total Clips Rendered", stats["total_clips_generated"])
with c3:
    st.metric("Live on YouTube", stats["total_uploaded_videos"])
with c4:
    st.metric("Queued for Upload", stats["pending_uploads"])

st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    st.subheader("📁 Input Directory Status")
    st.caption("Videos placed in `/videos/input/` are detected automatically.")
    sources = list_source_videos(limit=5)
    if sources:
        for s in sources:
            st.write(f"• **{s['file_name']}** ({s['duration_seconds']:.1f}s) — Status: `{s['status']}`")
    else:
        st.info("Input directory is currently empty.")

with col2:
    st.subheader("🚀 Latest Publishing History")
    history = list_upload_history(limit=5)
    if history:
        for h in history:
            st.write(f"• **{h['title']}** — [{h['youtube_url']}]({h['youtube_url']}) (`{h['uploaded_at']}`)")
    else:
        st.info("No uploads recorded yet.")
