"""
AutoTube AI - System Audit & Error Logs
Real-time inspection of pipeline logs, warnings, and errors
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path on Streamlit Cloud & local
_ROOT_DIR = Path(__file__).resolve().parents[2]
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))


import streamlit as st
from database.db import get_recent_logs, clear_logs
from app.ui_components import inject_custom_css, render_sidebar

inject_custom_css()
render_sidebar()

st.title("🛡️ System Logs & Diagnostics")
st.caption("Inspect pipeline events, Whisper transcripts, FFmpeg renders, and YouTube API calls.")

c1, c2, c3 = st.columns([4, 4, 2])
with c1:
    level_filter = st.selectbox("Filter by Severity:", ["ALL", "ERROR", "WARNING", "INFO", "SUCCESS"])
with c3:
    if st.button("🗑️ Clear Log History", use_container_width=True):
        clear_logs()
        st.success("Logs cleared.")
        st.rerun()

logs = get_recent_logs(level=level_filter, limit=200)

if not logs:
    st.info("No matching log records found.")
    st.stop()

for l in logs:
    lvl = l["level"]
    color = "#3fb950" if lvl == "SUCCESS" else ("#f85149" if lvl == "ERROR" else ("#d29922" if lvl == "WARNING" else "#58a6ff"))
    with st.container():
        st.markdown(
            f"""
            <div style="padding: 10px 14px; border-radius: 8px; background: rgba(255,255,255,0.02); border-left: 4px solid {color}; margin-bottom: 8px; font-size: 13px;">
                <span style="color: {color}; font-weight: 700;">[{lvl}]</span> 
                <span style="color: #8b949e; margin-right: 8px;">{l['created_at']}</span>
                <span style="background: rgba(255,255,255,0.08); padding: 2px 6px; border-radius: 4px; font-size: 11px; margin-right: 8px;">{l['module']}</span>
                <span style="color: #f0f6fc;">{l['message']}</span>
            </div>
            """,
            unsafe_allow_html=True
        )
        if l.get("details"):
            with st.expander("View Stack Trace / Details"):
                st.code(l["details"])
