"""
AutoTube AI - Publishing Upload Queue
Inspect and manage scheduled YouTube Shorts waiting in line to be published
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path on Streamlit Cloud & local
_ROOT_DIR = Path(__file__).resolve().parents[2]
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))


from datetime import datetime
from zoneinfo import ZoneInfo
import streamlit as st
from database.db import list_schedule, update_schedule_status, get_setting
from youtube.uploader import YouTubeUploader
from app.ui_components import inject_custom_css, render_sidebar

inject_custom_css()
render_sidebar()

st.title("⏳ Publishing Upload Queue")
st.caption("Videos lined up for automated background publishing at designated time slots.")

uploader = YouTubeUploader()
queue = list_schedule(status="pending", limit=50)

if not queue:
    st.info("The publishing queue is currently empty. Ready clips will automatically enter the queue when generated.")
    st.stop()

tz_name = get_setting("timezone", "Asia/Kolkata")
try:
    tz = ZoneInfo(tz_name)
except Exception:
    tz = ZoneInfo("UTC")

now = datetime.now(tz)

for item in queue:
    sched_dt_str = item["scheduled_time"]
    try:
        dt = datetime.fromisoformat(sched_dt_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz)
        time_diff = dt - now
        diff_str = f"In {time_diff.days}d {time_diff.seconds//3600}h {(time_diff.seconds%3600)//60}m" if time_diff.total_seconds() > 0 else "Due Now!"
    except Exception:
        diff_str = sched_dt_str

    with st.container():
        st.markdown(
            f"""
            <div class="glass-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-size: 13px; color: #58a6ff; font-weight: 700; text-transform: uppercase;">
                            ⏰ Scheduled For: {sched_dt_str} ({diff_str})
                        </div>
                        <h4 style="margin: 4px 0 0 0; color: #f0f6fc;">{item['title']}</h4>
                        <p style="margin: 2px 0 0 0; font-size: 13px; color: #8b949e;">
                            Duration: <b>{item['duration_seconds']:.1f}s</b> | Privacy: <b>{item['privacy'].upper()}</b>
                        </p>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        col1, col2 = st.columns([8, 2])
        with col2:
            if st.button("🚀 Publish Now", key=f"force_pub_{item['id']}", use_container_width=True):
                with st.spinner("Publishing queued short..."):
                    success, vid_id, err = uploader.upload_clip(
                        clip_id=item["clip_id"],
                        video_path=item["file_path"],
                        title=item["title"],
                        description="",
                        privacy_status=item["privacy"]
                    )
                    if success:
                        update_schedule_status(item["id"], "published")
                        st.success(f"Published successfully! Video ID: {vid_id}")
                        st.rerun()
                    else:
                        st.error(f"Upload failed: {err}")
