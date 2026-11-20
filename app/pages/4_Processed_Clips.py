"""
AutoTube AI - Processed Clips Library
Preview rendered 9:16 vertical Shorts, inspect metadata, and trigger manual publishing
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path on Streamlit Cloud & local
_ROOT_DIR = Path(__file__).resolve().parents[2]
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))


from pathlib import Path
import streamlit as st
from database.db import list_clips, get_clip
from youtube.uploader import YouTubeUploader
from youtube.scheduler import PublishingScheduler
from app.ui_components import inject_custom_css, render_sidebar

inject_custom_css()
render_sidebar()

st.title("🎬 Processed Clips Library")
st.caption("Review vertical 1080x1920 YouTube Shorts stored in `videos/processed/`.")

filter_status = st.selectbox("Filter by Status:", ["ALL", "ready", "scheduled", "uploading", "uploaded", "failed"])
status_arg = None if filter_status == "ALL" else filter_status
clips = list_clips(status=status_arg, limit=100)

if not clips:
    st.info("No processed clips found matching filter.")
    st.stop()

uploader = YouTubeUploader()
scheduler = PublishingScheduler()

for clip in clips:
    with st.container():
        st.markdown(
            f"""
            <div class="glass-card">
                <div style="display: flex; justify-content: space-between;">
                    <div>
                        <h3 style="margin: 0; color: #f0f6fc;">{clip['title']}</h3>
                        <p style="margin: 4px 0 12px 0; font-size: 13px; color: #8b949e;">
                            Clip #{clip['clip_number']} | Duration: <b>{clip['duration_seconds']:.1f}s</b> | Score: <b>{clip['score']}/100</b> | Privacy: <b>{clip['privacy'].upper()}</b>
                        </p>
                    </div>
                    <div>
                        <span class="status-pill {'status-active' if clip['status'] == 'uploaded' else ('status-paused' if clip['status'] == 'scheduled' else 'status-failed')}">
                            ● {clip['status'].upper()}
                        </span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        col_vid, col_meta = st.columns([4, 6])
        with col_vid:
            clip_file = Path(clip["file_path"]) if clip.get("file_path") else None
            if clip_file and clip_file.exists():
                st.video(str(clip_file))
            else:
                st.warning("Video file not found on disk.")

            thumb_file = Path(clip["thumbnail_path"]) if clip.get("thumbnail_path") else None
            if thumb_file and thumb_file.exists():
                st.image(str(thumb_file), caption="Generated 9:16 Thumbnail", width=220)

        with col_meta:
            st.markdown("**Description Preview:**")
            st.text_area("", value=clip.get("description", ""), height=130, key=f"desc_{clip['id']}", disabled=True)
            st.markdown(f"**Hashtags:** `{clip.get('hashtags', '')}`")
            st.markdown(f"**Tags:** `{clip.get('keywords', '')}`")
            st.markdown(f"**Category ID:** `{clip.get('category_id', '24')}`")

            # Quick Actions
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if clip["status"] in ["ready", "failed"]:
                    if st.button(f"📅 Schedule Next Slot", key=f"sched_{clip['id']}"):
                        slot_dt = scheduler.schedule_clip_for_publishing(clip["id"])
                        st.success(f"Scheduled for {slot_dt.strftime('%Y-%m-%d %H:%M:%S')}!")
                        st.rerun()

            with btn_col2:
                if clip["status"] != "uploaded":
                    if st.button(f"⚡ Upload Now to YouTube", key=f"up_{clip['id']}", type="primary"):
                        with st.spinner("Uploading to YouTube..."):
                            success, vid_id, err = uploader.upload_clip(
                                clip_id=clip["id"],
                                video_path=clip["file_path"],
                                title=clip["title"],
                                description=clip["description"],
                                keywords=clip["keywords"],
                                category_id=clip["category_id"],
                                privacy_status=clip["privacy"],
                                thumbnail_path=clip.get("thumbnail_path")
                            )
                            if success:
                                st.success(f"Uploaded! Video ID: {vid_id}")
                                st.rerun()
                            else:
                                st.error(f"Upload failed: {err}")
                else:
                    if clip.get("youtube_url"):
                        st.link_button("📺 View on YouTube", clip["youtube_url"])

        st.markdown("<hr style='border: 0.5px solid rgba(255,255,255,0.06);'>", unsafe_allow_html=True)
