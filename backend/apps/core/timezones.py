"""
Geographic timezone resolution and conversion utilities for Spotter ELD Route Planner.
Converts UTC timestamps to IANA location timezones for coherent, compliant time display
across route timelines, stops, and Driver's Daily Log remarks.
"""

from datetime import datetime, timezone
import zoneinfo
from typing import Optional, Tuple, Dict, Any

# Primary US Timezone regions by longitude and state approximations
# Used when exact polygon lookup is not available, adhering to standard US Timezone boundaries
STATE_TIMEZONES: Dict[str, str] = {
    # Pacific
    "CA": "America/Los_Angeles", "WA": "America/Los_Angeles", "OR": "America/Los_Angeles", "NV": "America/Los_Angeles",
    # Mountain
    "AZ": "America/Phoenix",     # Arizona does not observe DST
    "CO": "America/Denver", "UT": "America/Denver", "NM": "America/Denver", "WY": "America/Denver",
    "MT": "America/Denver", "ID": "America/Boise",
    # Central
    "TX": "America/Chicago", "IL": "America/Chicago", "WI": "America/Chicago", "MN": "America/Chicago",
    "IA": "America/Chicago", "MO": "America/Chicago", "AR": "America/Chicago", "LA": "America/Chicago",
    "MS": "America/Chicago", "AL": "America/Chicago", "OK": "America/Chicago", "KS": "America/Chicago",
    "NE": "America/Chicago", "SD": "America/Chicago", "ND": "America/Chicago", "TN": "America/Chicago",
    # Eastern
    "NY": "America/New_York", "VA": "America/New_York", "PA": "America/New_York", "OH": "America/New_York",
    "MI": "America/Detroit", "IN": "America/Indiana/Indianapolis", "KY": "America/New_York",
    "NC": "America/New_York", "SC": "America/New_York", "GA": "America/New_York", "FL": "America/New_York",
    "MD": "America/New_York", "DE": "America/New_York", "NJ": "America/New_York", "CT": "America/New_York",
    "RI": "America/New_York", "MA": "America/New_York", "VT": "America/New_York", "NH": "America/New_York",
    "ME": "America/New_York", "DC": "America/New_York",
}

def get_location_timezone(lat: float, lon: float, state_code: Optional[str] = None) -> str:
    """
    Resolves the IANA timezone identifier for a geographic coordinate in North America.
    Prioritizes explicit US state code when available, with coordinate boundary fallbacks.
    """
    if state_code and state_code.upper() in STATE_TIMEZONES:
        return STATE_TIMEZONES[state_code.upper()]

    # Longitude & latitude boundary heuristics for continental US:
    # 1. Arizona check (approx bounding box: lat 31.3 to 37.0, lon -114.8 to -109.0)
    if 31.3 <= lat <= 37.0 and -114.8 <= lon <= -109.0:
        return "America/Phoenix"

    # 2. Pacific Time (lon < -114.0)
    if lon < -114.0:
        return "America/Los_Angeles"

    # 3. Mountain Time (-114.0 <= lon < -102.0)
    if lon < -102.0:
        return "America/Denver"

    # 4. Central Time (-102.0 <= lon < -85.5)
    if lon < -85.5:
        # Special check for Indiana/Tennessee/Kentucky border areas
        return "America/Chicago"

    # 5. Eastern Time (lon >= -85.5)
    return "America/New_York"

def convert_utc_to_location_time(dt: datetime, iana_tz: str) -> datetime:
    """
    Converts a UTC datetime object to the target location's timezone-aware datetime.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    try:
        tz = zoneinfo.ZoneInfo(iana_tz)
    except Exception:
        tz = zoneinfo.ZoneInfo("America/Chicago")

    return dt.astimezone(tz)

def format_datetime_in_location(dt: datetime, iana_tz: str, fmt: str = "%b %d, %Y %H:%M %Z") -> str:
    """
    Formats a datetime in the given IANA location timezone with timezone abbreviation.
    """
    local_dt = convert_utc_to_location_time(dt, iana_tz)
    return local_dt.strftime(fmt)
