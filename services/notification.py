"""
AutoTube AI - Notification & Status Service
Tracks real-time events and failure notifications for the dashboard
"""

from typing import List, Dict, Any
from datetime import datetime
from services.logger import log_info, log_error, log_warning


class NotificationManager:
    """In-memory recent alerts buffer with fallback to database logs."""
    _alerts: List[Dict[str, Any]] = []
    _max_alerts: int = 50

    @classmethod
    def notify(cls, title: str, message: str, level: str = "info"):
        alert = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "title": title,
            "message": message,
            "level": level.lower()
        }
        cls._alerts.insert(0, alert)
        if len(cls._alerts) > cls._max_alerts:
            cls._alerts.pop()
        
        if level.lower() == "error":
            log_error("Notification", f"{title}: {message}")
        elif level.lower() == "warning":
            log_warning("Notification", f"{title}: {message}")
        else:
            log_info("Notification", f"{title}: {message}")

    @classmethod
    def get_recent_alerts(cls, limit: int = 10) -> List[Dict[str, Any]]:
        return cls._alerts[:limit]

    @classmethod
    def clear_alerts(cls):
        cls._alerts.clear()
