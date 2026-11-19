"""
AutoTube AI - Publishing Slot Scheduler
Computes next available publishing slots according to configured daily posting times.
Default slots: 09:00 AM, 12:00 PM, 03:00 PM, 06:00 PM, 09:00 PM (Asia/Kolkata).
"""

import json
from datetime import datetime, timedelta, time
from typing import List, Optional
from zoneinfo import ZoneInfo
from core.config import config
from database.db import get_latest_scheduled_time, add_to_schedule, get_setting
from services.logger import log_info


class PublishingScheduler:
    def __init__(self, tz_name: Optional[str] = None):
        self.tz_name = tz_name or get_setting("timezone", config.timezone)
        try:
            self.tz = ZoneInfo(self.tz_name)
        except Exception:
            self.tz = ZoneInfo("UTC")

    def get_configured_slots(self) -> List[str]:
        slots_json = get_setting("daily_schedule_slots")
        if slots_json:
            try:
                return json.loads(slots_json)
            except Exception:
                pass
        return config.daily_schedule_slots

    def calculate_next_available_slot(self) -> datetime:
        """
        Determines the next chronological publishing slot that has not yet been assigned.
        Never overlaps two videos into the same publishing slot.
        """
        now = datetime.now(self.tz)
        slots = sorted(self.get_configured_slots()) # e.g. ["09:00", "12:00", "15:00", "18:00", "21:00"]
        
        # Check what the highest scheduled time currently is in DB
        latest_str = get_latest_scheduled_time()
        base_time = now
        if latest_str:
            try:
                dt_latest = datetime.fromisoformat(latest_str)
                if dt_latest.tzinfo is None:
                    dt_latest = dt_latest.replace(tzinfo=self.tz)
                # If there are already upcoming scheduled items in the future, base next slot on the latest one
                if dt_latest > now:
                    base_time = dt_latest
            except Exception:
                pass

        # Search for next slot strictly after base_time
        # Check current day or subsequent days
        current_date = base_time.date()
        for day_offset in range(30): # Look up to 30 days ahead
            target_date = current_date + timedelta(days=day_offset)
            for slot_str in slots:
                hour, minute = map(int, slot_str.split(":"))
                slot_dt = datetime.combine(target_date, time(hour, minute), tzinfo=self.tz)
                
                # Must be at least 5 minutes in the future from now, and strictly after base_time
                if slot_dt > (now + timedelta(minutes=5)) and slot_dt > (base_time + timedelta(minutes=2)):
                    return slot_dt

        # Fallback 1 hour from now
        return now + timedelta(hours=1)

    def schedule_clip_for_publishing(self, clip_id: int) -> datetime:
        """Assigns clip to the next available slot and records it in SQLite."""
        slot_dt = self.calculate_next_available_slot()
        slot_iso = slot_dt.isoformat()
        add_to_schedule(clip_id, slot_iso, tz=self.tz_name)
        log_info("PublishingScheduler", f"Clip #{clip_id} scheduled for {slot_iso} ({self.tz_name})")
        return slot_dt
