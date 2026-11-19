"""
AutoTube AI - Publishing Calendar
Visual timetable and calendar view of scheduled YouTube Shorts
"""

import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import streamlit as st
from database.db import list_schedule, get_setting, set_setting
from core.config import config
from app.ui_components import inject_custom_css, render_sidebar

inject_custom_css()
render_sidebar()

st.title("📅 Publishing Calendar & Slots")
st.caption("Review your daily posting timetable and adjust release schedule slots.")

tz_name = get_setting("timezone", config.timezone)
slots_raw = get_setting("daily_schedule_slots", json.dumps(config.daily_schedule_slots))
try:
    slots = json.loads(slots_raw)
except Exception:
    slots = config.daily_schedule_slots

# Slot Configuration Card
with st.expander("⚙️ Configure Daily Upload Slots", expanded=False):
    st.markdown("Enter comma-separated publishing times in 24-hour HH:MM format:")
    slots_input = st.text_input("Daily Posting Slots:", value=", ".join(slots))
    if st.button("Save Daily Slots", key="btn_save_slots"):
        parsed = [s.strip() for s in slots_input.split(",") if s.strip()]
        set_setting("daily_schedule_slots", json.dumps(parsed))
        st.success("Updated schedule slots successfully!")
        st.rerun()

st.markdown("### 🕒 Active Daily Release Windows")
cols = st.columns(len(slots))
for idx, s in enumerate(slots):
    with cols[idx]:
        st.markdown(
            f"""
            <div class="metric-card" style="text-align: center;">
                <div class="metric-label">Slot #{idx+1}</div>
                <div class="metric-value" style="font-size: 22px; color: #ff0033;">{s}</div>
                <div class="metric-sub">{tz_name}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

st.markdown("---")
st.markdown("### 📋 Upcoming Scheduled Releases")

scheduled_items = list_schedule(status="pending", limit=30)
if scheduled_items:
    # Group by date
    days_map = {}
    for item in scheduled_items:
        date_str = item["scheduled_time"][:10]
        if date_str not in days_map:
            days_map[date_str] = []
        days_map[date_str].append(item)

    for day, items in sorted(days_map.items()):
        st.markdown(f"#### 📆 {day}")
        for it in items:
            t_str = it["scheduled_time"][11:16]
            st.markdown(
                f"""
                <div style="padding: 10px 16px; border-radius: 8px; background: rgba(255,255,255,0.03); border-left: 4px solid #58a6ff; margin-bottom: 8px;">
                    <span style="font-weight: 700; color: #58a6ff;">[{t_str}]</span>
                    <b>{it['title']}</b> ({it['duration_seconds']:.1f}s) — Privacy: <i>{it['privacy']}</i>
                </div>
                """,
                unsafe_allow_html=True
            )
else:
    st.info("No future releases scheduled. Add videos to `videos/input/` to populate the calendar automatically.")
