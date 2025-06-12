from __future__ import annotations

"""Utility helpers."""
from zoneinfo import ZoneInfo


def get_timezone(settings: dict | None) -> ZoneInfo:
    """Return ZoneInfo from settings or UTC if unset/invalid."""
    tz_name = "UTC"
    if settings and settings.get("timezone"):
        tz_name = settings["timezone"] or "UTC"
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return ZoneInfo("UTC")
