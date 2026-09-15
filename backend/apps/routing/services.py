"""
Routing service using OpenRouteService (primary API) with automatic fallback
to Open Source Routing Machine (OSRM) and Haversine offline engine.
Supports commercial vehicle driving profiles, polyline distance calculation,
and mile-marker interpolation for FMCSA compliance.
"""

import math
import os
import logging
import requests
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger(__name__)

METERS_TO_MILES = 0.000621371
MILES_TO_METERS = 1609.344
EARTH_RADIUS_MILES = 3958.8

def haversine_distance(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
    """Calculate great-circle distance in miles between two (lat, lon) coordinates."""
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_MILES * c

class RoutingService:
    OSRM_URL = "https://router.project-osrm.org/route/v1/driving"
    ORS_URL = "https://api.openrouteservice.org/v2/directions/driving-car"

    @classmethod
    def get_route(cls, waypoints: List[Tuple[float, float]]) -> Dict[str, Any]:
        """
        Calculates driving route for waypoints: list of (lat, lon) tuples.
        Priority:
        1. OpenRouteService API (using OPENROUTESERVICE_KEY)
        2. OSRM Public Driving API
        3. Haversine Geometry Fallback
        """
        if len(waypoints) < 2:
            raise ValueError("At least two waypoints (origin and destination) are required.")

        ors_key = os.environ.get("OPENROUTESERVICE_KEY", "").strip()

        # 1. Try OpenRouteService if API key is configured
        if ors_key:
            ors_result = cls._call_openrouteservice(waypoints, ors_key)
            if ors_result:
                return ors_result

        # 2. Try OSRM Public Routing API
        osrm_result = cls._call_osrm(waypoints)
        if osrm_result:
            return osrm_result

        # 3. Fallback to Haversine
        logger.warning("External routing APIs unavailable, utilizing Haversine routing fallback")
        return cls._haversine_fallback(waypoints)

    @classmethod
    def _call_openrouteservice(cls, waypoints: List[Tuple[float, float]], api_key: str) -> Optional[Dict[str, Any]]:
        """Call OpenRouteService directions API."""
        try:
            # ORS expects coordinates as [[lon, lat], [lon, lat], ...]
            coords = [[lon, lat] for lat, lon in waypoints]
            headers = {
                "Authorization": api_key,
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8"
            }
            body = {
                "coordinates": coords,
                "elevation": False,
                "instructions": True,
            }

            resp = requests.post(f"{cls.ORS_URL}/geojson", json=body, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                features = data.get("features", [])
                if features:
                    feature = features[0]
                    geometry = feature.get("geometry", {})
                    coordinates = geometry.get("coordinates", [])
                    properties = feature.get("properties", {})
                    summary = properties.get("summary", {})

                    distance_meters = summary.get("distance", 0)
                    duration_seconds = summary.get("duration", 0)

                    distance_miles = round(distance_meters * METERS_TO_MILES, 1)

                    # Commercial truck speed adjustment (~55-60 mph average with traffic & grades)
                    raw_duration_hours = duration_seconds / 3600.0
                    truck_duration_hours = max(raw_duration_hours, distance_miles / 60.0) if distance_miles > 0 else 0.0

                    cum_miles = cls._compute_cumulative_distances(coordinates)

                    logger.info("Successfully fetched route via OpenRouteService API (%s mi)", distance_miles)
                    return {
                        "status": "success",
                        "provider": "OpenRouteService",
                        "distance_miles": distance_miles,
                        "duration_hours": round(truck_duration_hours, 2),
                        "geometry": geometry,
                        "coordinates": coordinates,
                        "cumulative_miles": cum_miles,
                        "legs": properties.get("segments", []),
                    }
                else:
                    logger.warning("OpenRouteService returned 200 but no features")
            else:
                logger.warning("OpenRouteService returned status %s: %s", resp.status_code, resp.text[:150])
        except Exception as exc:
            logger.warning("OpenRouteService request error: %s", exc)

        return None

    @classmethod
    def _call_osrm(cls, waypoints: List[Tuple[float, float]]) -> Optional[Dict[str, Any]]:
        """Call Open Source Routing Machine (OSRM) driving API."""
        try:
            coord_str = ";".join(f"{lon:.6f},{lat:.6f}" for lat, lon in waypoints)
            url = f"{cls.OSRM_URL}/{coord_str}?overview=full&geometries=geojson&steps=true"

            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == "Ok" and data.get("routes"):
                    route = data["routes"][0]
                    distance_meters = route.get("distance", 0)
                    duration_seconds = route.get("duration", 0)
                    geometry = route.get("geometry", {})
                    coordinates = geometry.get("coordinates", [])

                    distance_miles = round(distance_meters * METERS_TO_MILES, 1)
                    raw_duration_hours = duration_seconds / 3600.0
                    truck_duration_hours = max(raw_duration_hours, distance_miles / 60.0) if distance_miles > 0 else 0.0

                    cum_miles = cls._compute_cumulative_distances(coordinates)

                    return {
                        "status": "success",
                        "provider": "OSRM",
                        "distance_miles": distance_miles,
                        "duration_hours": round(truck_duration_hours, 2),
                        "geometry": geometry,
                        "coordinates": coordinates,
                        "cumulative_miles": cum_miles,
                        "legs": route.get("legs", []),
                    }
        except Exception as exc:
            logger.warning("OSRM request error: %s", exc)

        return None

    @classmethod
    def _compute_cumulative_distances(cls, coordinates: List[List[float]]) -> List[float]:
        """Compute cumulative miles at each coordinate vertex."""
        if not coordinates:
            return []
        cum = [0.0]
        total = 0.0
        for i in range(1, len(coordinates)):
            lon1, lat1 = coordinates[i - 1]
            lon2, lat2 = coordinates[i]
            d = haversine_distance((lat1, lon1), (lat2, lon2))
            total += d
            cum.append(round(total, 2))
        return cum

    @classmethod
    def interpolate_coordinate_at_mile(cls, coordinates: List[List[float]], cumulative_miles: List[float], target_mile: float) -> Tuple[float, float]:
        """
        Given route coordinates and cumulative distances, find the exact [lat, lon] at target_mile.
        """
        if not coordinates:
            return (0.0, 0.0)
        if target_mile <= 0 or len(coordinates) == 1:
            return (coordinates[0][1], coordinates[0][0])
        if target_mile >= cumulative_miles[-1]:
            return (coordinates[-1][1], coordinates[-1][0])

        for i in range(1, len(cumulative_miles)):
            if cumulative_miles[i] >= target_mile:
                m_prev = cumulative_miles[i - 1]
                m_next = cumulative_miles[i]
                ratio = (target_mile - m_prev) / (m_next - m_prev) if (m_next > m_prev) else 0.0

                lon_prev, lat_prev = coordinates[i - 1]
                lon_next, lat_next = coordinates[i]

                interp_lat = lat_prev + ratio * (lat_next - lat_prev)
                interp_lon = lon_prev + ratio * (lon_next - lon_prev)
                return (round(interp_lat, 5), round(interp_lon, 5))

        return (coordinates[-1][1], coordinates[-1][0])

    @classmethod
    def _haversine_fallback(cls, waypoints: List[Tuple[float, float]]) -> Dict[str, Any]:
        """Fallback when external routing services are unreachable."""
        total_dist_miles = 0.0
        coords = []
        for i in range(len(waypoints) - 1):
            lat1, lon1 = waypoints[i]
            lat2, lon2 = waypoints[i + 1]
            d = haversine_distance((lat1, lon1), (lat2, lon2)) * 1.22
            total_dist_miles += d

            steps = max(5, int(d / 40.0))
            for s in range(steps):
                f = s / steps
                coords.append([lon1 + f * (lon2 - lon1), lat1 + f * (lat2 - lat1)])

        coords.append([waypoints[-1][1], waypoints[-1][0]])
        cum_miles = cls._compute_cumulative_distances(coords)

        duration_hours = total_dist_miles / 55.0
        return {
            "status": "fallback",
            "provider": "Haversine",
            "distance_miles": round(total_dist_miles, 1),
            "duration_hours": round(duration_hours, 2),
            "geometry": {
                "type": "LineString",
                "coordinates": coords
            },
            "coordinates": coords,
            "cumulative_miles": cum_miles,
            "legs": []
        }
