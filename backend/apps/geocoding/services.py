"""
Geocoding service using OpenStreetMap Nominatim with comprehensive in-memory caching
and freight hub fallbacks.
"""

import logging
import re
import requests
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Pre-populated freight hubs to provide instant response and network resilience
_GEOCODE_CACHE: Dict[str, Dict[str, Any]] = {
    "chicago, il": {"lat": 41.8781, "lon": -87.6298, "display_name": "Chicago, Illinois, USA", "city": "Chicago", "state": "IL"},
    "chicago": {"lat": 41.8781, "lon": -87.6298, "display_name": "Chicago, Illinois, USA", "city": "Chicago", "state": "IL"},
    "dallas, tx": {"lat": 32.7767, "lon": -96.7970, "display_name": "Dallas, Texas, USA", "city": "Dallas", "state": "TX"},
    "dallas": {"lat": 32.7767, "lon": -96.7970, "display_name": "Dallas, Texas, USA", "city": "Dallas", "state": "TX"},
    "atlanta, ga": {"lat": 33.7490, "lon": -84.3880, "display_name": "Atlanta, Georgia, USA", "city": "Atlanta", "state": "GA"},
    "atlanta": {"lat": 33.7490, "lon": -84.3880, "display_name": "Atlanta, Georgia, USA", "city": "Atlanta", "state": "GA"},
    "indianapolis, in": {"lat": 39.7684, "lon": -86.1581, "display_name": "Indianapolis, Indiana, USA", "city": "Indianapolis", "state": "IN"},
    "indianapolis": {"lat": 39.7684, "lon": -86.1581, "display_name": "Indianapolis, Indiana, USA", "city": "Indianapolis", "state": "IN"},
    "columbus, oh": {"lat": 39.9612, "lon": -82.9988, "display_name": "Columbus, Ohio, USA", "city": "Columbus", "state": "OH"},
    "columbus": {"lat": 39.9612, "lon": -82.9988, "display_name": "Columbus, Ohio, USA", "city": "Columbus", "state": "OH"},
    "los angeles, ca": {"lat": 34.0522, "lon": -118.2437, "display_name": "Los Angeles, California, USA", "city": "Los Angeles", "state": "CA"},
    "los angeles": {"lat": 34.0522, "lon": -118.2437, "display_name": "Los Angeles, California, USA", "city": "Los Angeles", "state": "CA"},
    "denver, co": {"lat": 39.7392, "lon": -104.9903, "display_name": "Denver, Colorado, USA", "city": "Denver", "state": "CO"},
    "denver": {"lat": 39.7392, "lon": -104.9903, "display_name": "Denver, Colorado, USA", "city": "Denver", "state": "CO"},
    "new york, ny": {"lat": 40.7128, "lon": -74.0060, "display_name": "New York, New York, USA", "city": "New York", "state": "NY"},
    "new york": {"lat": 40.7128, "lon": -74.0060, "display_name": "New York, New York, USA", "city": "New York", "state": "NY"},
    "houston, tx": {"lat": 29.7604, "lon": -95.3698, "display_name": "Houston, Texas, USA", "city": "Houston", "state": "TX"},
    "memphis, tn": {"lat": 35.1495, "lon": -90.0490, "display_name": "Memphis, Tennessee, USA", "city": "Memphis", "state": "TN"},
    "nashville, tn": {"lat": 36.1627, "lon": -86.7816, "display_name": "Nashville, Tennessee, USA", "city": "Nashville", "state": "TN"},
    "kansas city, mo": {"lat": 39.0997, "lon": -94.5786, "display_name": "Kansas City, Missouri, USA", "city": "Kansas City", "state": "MO"},
    "st. louis, mo": {"lat": 38.6270, "lon": -90.1994, "display_name": "St. Louis, Missouri, USA", "city": "St. Louis", "state": "MO"},
    "phoenix, az": {"lat": 33.4484, "lon": -112.0740, "display_name": "Phoenix, Arizona, USA", "city": "Phoenix", "state": "AZ"},
    "seattle, wa": {"lat": 47.6062, "lon": -122.3321, "display_name": "Seattle, Washington, USA", "city": "Seattle", "state": "WA"},
    "miami, fl": {"lat": 25.7617, "lon": -80.1918, "display_name": "Miami, Florida, USA", "city": "Miami", "state": "FL"},
}

class GeocodingService:
    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
    REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
    HEADERS = {
        "User-Agent": "SpotterELDRoutePlanner/1.0 (assessment@spotter.ai)"
    }

    @classmethod
    def geocode(cls, query: str) -> Optional[Dict[str, Any]]:
        """
        Geocode location string to {lat, lon, display_name, city, state}.
        Handles coordinate strings, cache, Nominatim search, and fallback dictionary.
        """
        clean_query = query.strip()
        if not clean_query:
            return None

        # Check if user entered direct lat/lon coordinates (e.g. "41.8781, -87.6298")
        coord_match = re.match(r"^[-+]?([1-8]?\d(\.\d+)?|90(\.0+)?),\s*[-+]?(180(\.0+)?|((1[0-7]\d)|([1-9]?\d))(\.\d+)?)$", clean_query)
        if coord_match:
            parts = clean_query.split(",")
            lat, lon = float(parts[0].strip()), float(parts[1].strip())
            return {
                "lat": lat,
                "lon": lon,
                "display_name": f"{lat:.4f}, {lon:.4f}",
                "city": f"Lat {lat:.2f}",
                "state": f"Lon {lon:.2f}"
            }

        cache_key = clean_query.lower()
        if cache_key in _GEOCODE_CACHE:
            return _GEOCODE_CACHE[cache_key]

        # Strip state punctuation variants e.g. "Chicago IL" -> "chicago, il"
        normalized = re.sub(r"\s+", " ", cache_key).replace(".", "")
        if normalized in _GEOCODE_CACHE:
            return _GEOCODE_CACHE[normalized]

        try:
            params = {
                "q": clean_query,
                "format": "json",
                "limit": 1,
                "addressdetails": 1,
            }
            resp = requests.get(cls.NOMINATIM_URL, params=params, headers=cls.HEADERS, timeout=6)
            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) > 0:
                    item = data[0]
                    addr = item.get("address", {})
                    city = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("county") or ""
                    state = addr.get("state") or ""

                    result = {
                        "lat": float(item["lat"]),
                        "lon": float(item["lon"]),
                        "display_name": item.get("display_name", clean_query),
                        "city": city,
                        "state": state
                    }
                    _GEOCODE_CACHE[cache_key] = result
                    return result
        except Exception as exc:
            logger.warning("Geocoding lookup failed for '%s': %s", query, exc)

        # Partial matching in local cache
        for hub_key, hub_data in _GEOCODE_CACHE.items():
            if hub_key in cache_key or cache_key in hub_key:
                return hub_data

        return None

    @classmethod
    def reverse_geocode(cls, lat: float, lon: float) -> str:
        """
        Resolve coordinate to friendly city, state location name for ELD log remarks.
        """
        cache_key = f"{round(lat, 2)},{round(lon, 2)}"
        if cache_key in _GEOCODE_CACHE:
            return _GEOCODE_CACHE[cache_key].get("display_name", f"{lat:.2f}, {lon:.2f}")

        try:
            params = {
                "lat": lat,
                "lon": lon,
                "format": "json",
                "zoom": 10,
            }
            resp = requests.get(cls.REVERSE_URL, params=params, headers=cls.HEADERS, timeout=1.5)
            if resp.status_code == 200:
                data = resp.json()
                addr = data.get("address", {})
                city = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("county") or ""
                state = addr.get("state", "")
                if city and state:
                    name = f"{city}, {state}"
                elif city:
                    name = city
                elif state:
                    name = state
                else:
                    name = data.get("display_name", f"{lat:.2f}, {lon:.2f}")[:40]

                _GEOCODE_CACHE[cache_key] = {"display_name": name}
                return name
        except Exception as exc:
            logger.debug("Reverse geocoding failed for (%s, %s): %s", lat, lon, exc)

        fallback = f"{lat:.2f}, {lon:.2f}"
        _GEOCODE_CACHE[cache_key] = {"display_name": fallback}
        return fallback
