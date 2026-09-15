"""
Routing service using Open Source Routing Machine (OSRM) driving profile
with polyline distance calculation and mile-marker interpolation.
"""

import math
import logging
import requests
from typing import Dict, Any, List, Tuple

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

    @classmethod
    def get_route(cls, waypoints: List[Tuple[float, float]]) -> Dict[str, Any]:
        """
        waypoints: list of (lat, lon) tuples.
        Returns:
            {
                "status": "success",
                "distance_miles": float,
                "duration_hours": float,
                "geometry": {"type": "LineString", "coordinates": [[lon, lat], ...]},
                "cumulative_miles": List[float], # Cumulative distance at each coordinate index
                "steps": List[Dict]
            }
        """
        if len(waypoints) < 2:
            raise ValueError("At least two waypoints (origin and destination) are required.")

        # OSRM format: {lon},{lat};{lon},{lat}
        coord_str = ";".join(f"{lon:.6f},{lat:.6f}" for lat, lon in waypoints)
        url = f"{cls.OSRM_URL}/{coord_str}?overview=full&geometries=geojson&steps=true"

        try:
            resp = requests.get(url, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == "Ok" and data.get("routes"):
                    route = data["routes"][0]
                    distance_meters = route.get("distance", 0)
                    duration_seconds = route.get("duration", 0)
                    geometry = route.get("geometry", {})
                    coordinates = geometry.get("coordinates", [])

                    distance_miles = round(distance_meters * METERS_TO_MILES, 1)

                    # Commercial trucks are governed at ~60-65 mph on highways, accounting for traffic
                    # If OSRM car profile gives unrealistically fast duration, ensure realistic truck speed (~55-60 mph)
                    raw_duration_hours = duration_seconds / 3600.0
                    truck_duration_hours = max(raw_duration_hours, distance_miles / 60.0) if distance_miles > 0 else 0.0

                    # Compute cumulative distances along geometry points
                    cum_miles = cls._compute_cumulative_distances(coordinates)

                    return {
                        "status": "success",
                        "distance_miles": distance_miles,
                        "duration_hours": round(truck_duration_hours, 2),
                        "geometry": geometry,
                        "coordinates": coordinates, # [[lon, lat], ...]
                        "cumulative_miles": cum_miles,
                        "legs": route.get("legs", []),
                    }
                else:
                    logger.warning("OSRM returned code %s, falling back to Haversine", data.get("code"))
        except Exception as exc:
            logger.warning("OSRM request failed (%s), using Haversine route fallback", exc)

        return cls._haversine_fallback(waypoints)

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

        # Binary search or scan for segment
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
        """Fallback when external routing service is unreachable."""
        total_dist_miles = 0.0
        coords = []
        for i in range(len(waypoints) - 1):
            lat1, lon1 = waypoints[i]
            lat2, lon2 = waypoints[i + 1]
            d = haversine_distance((lat1, lon1), (lat2, lon2)) * 1.22 # Highway route multiplier
            total_dist_miles += d

            # Generate intermediate interpolated coordinates for realistic polyline
            steps = max(5, int(d / 40.0))
            for s in range(steps):
                f = s / steps
                coords.append([lon1 + f * (lon2 - lon1), lat1 + f * (lat2 - lat1)])

        coords.append([waypoints[-1][1], waypoints[-1][0]])
        cum_miles = cls._compute_cumulative_distances(coords)

        duration_hours = total_dist_miles / 55.0 # ~55 mph commercial average
        return {
            "status": "fallback",
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
