"""
AutoTube AI - YouTube Upload History & Performance Audit
Complete log of all videos published through the YouTube Data API v3
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path on Streamlit Cloud & local
_ROOT_DIR = Path(__file__).resolve().parents[2]
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))


from pathlib import Path
import streamlit as st
from database.db import list_upload_history
from app.ui_components import inject_custom_css, render_sidebar

inject_custom_css()
render_sidebar()

st.title("📜 YouTube Upload History")
st.caption("Permanent record of all YouTube Shorts published by AutoTube AI.")

history = list_upload_history(limit=100)

if not history:
    st.info("No upload history recorded yet. Published clips will automatically appear here.")
    st.stop()

for item in history:
    with st.container():
        st.markdown(
            f"""
            <div class="glass-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-size: 13px; color: #3fb950; font-weight: 700;">
                            ✓ PUBLISHED: {item['uploaded_at']}
                        </div>
                        <h4 style="margin: 4px 0 0 0; color: #f0f6fc;">{item['title']}</h4>
                        <p style="margin: 2px 0 0 0; font-size: 13px; color: #8b949e;">
                            YouTube Video ID: <code>{item['youtube_video_id']}</code> | Privacy: <b>{item['privacy'].upper()}</b>
                        </p>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        col1, col2 = st.columns([8, 2])
        with col2:
            st.link_button("📺 Open Short on YouTube", item["youtube_url"], use_container_width=True)
