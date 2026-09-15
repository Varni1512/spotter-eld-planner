"""
DRF Views for Spotter ELD Route Planner API.
Provides endpoints for health check, geocoding, and complete FMCSA trip planning with daily ELD logs.
"""

from datetime import datetime, timezone
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.geocoding.services import GeocodingService
from apps.routing.services import RoutingService
from apps.hos.engine import HOSSimulationEngine
from apps.logs.generator import DailyLogSheetGenerator
from .serializers import GeocodeRequestSerializer, PlanTripRequestSerializer

logger = logging.getLogger(__name__)

class HealthCheckView(APIView):
    """
    Health check endpoint returning backend status and FMCSA ruleset metadata.
    """
    def get(self, request):
        return Response({
            "status": "ok",
            "service": "Spotter ELD Route Planner Backend API",
            "version": "1.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "fmcsa_ruleset": {
                "regulation": "49 CFR Part 395",
                "carrier_type": "Property-carrying driver",
                "cycle": "70 hours / 8 days",
                "driving_limit": "11 hours",
                "duty_window": "14 consecutive hours",
                "rest_break": "30 minutes after 8 hours cumulative driving",
                "qualifying_rest": "10 consecutive hours off duty/sleeper",
                "restart": "34 consecutive hours off duty",
                "fueling_frequency": "At least once every 1,000 miles",
                "pickup_time": "1 hour on-duty not driving",
                "dropoff_time": "1 hour on-duty not driving",
            }
        }, status=status.HTTP_200_OK)

class GeocodeView(APIView):
    """
    Geocode an address or city/state query to coordinates.
    """
    def get(self, request):
        q = request.query_params.get("q", "").strip()
        if not q:
            return Response({"error": "Query parameter 'q' is required."}, status=status.HTTP_400_BAD_REQUEST)

        result = GeocodingService.geocode(q)
        if not result:
            return Response({"error": f"Could not geocode location: '{q}'"}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "query": q,
            "latitude": result["lat"],
            "longitude": result["lon"],
            "display_name": result["display_name"],
            "city": result.get("city", ""),
            "state": result.get("state", ""),
        }, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = GeocodeRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        q = serializer.validated_data["query"]
        result = GeocodingService.geocode(q)
        if not result:
            return Response({"error": f"Could not geocode location: '{q}'"}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "query": q,
            "latitude": result["lat"],
            "longitude": result["lon"],
            "display_name": result["display_name"],
            "city": result.get("city", ""),
            "state": result.get("state", ""),
        }, status=status.HTTP_200_OK)

class PlanTripView(APIView):
    """
    Primary route planning and FMCSA Hours-of-Service simulation endpoint.
    Accepts:
    - current_location
    - pickup_location
    - dropoff_location
    - current_cycle_used (hours)
    - start_time (optional, ISO 8601)

    Generates:
    1. Calculated route distance & estimated driving duration
    2. Route map geometry (GeoJSON LineString)
    3. Pickup and dropoff stops (1h on-duty each)
    4. Fueling stops (every ≤ 1,000 miles)
    5. Rest stops (30m break, 10h sleeper rests, 34h restarts)
    6. Complete chronological driving schedule
    7. Daily ELD log sheets for EVERY day of the trip (summing to exactly 24.0h)
    """
    def post(self, request):
        serializer = PlanTripRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        current_str = data["current_location"]
        pickup_str = data["pickup_location"]
        dropoff_str = data["dropoff_location"]
        current_cycle_used = data["current_cycle_used"]
        start_time = data.get("start_time") or datetime.now(timezone.utc)
        carrier_name = data.get("carrier_name", "Spotter Freight Logistics")
        truck_num = data.get("truck_number", "TRK-408")
        trailer_num = data.get("trailer_number", "TLR-9201")

        # 1. Geocode all locations
        geo_current = GeocodingService.geocode(current_str)
        if not geo_current:
            return Response({
                "error": f"Could not resolve current location: '{current_str}'. Please provide a valid US city, address, or coordinate."
            }, status=status.HTTP_400_BAD_REQUEST)

        geo_pickup = GeocodingService.geocode(pickup_str)
        if not geo_pickup:
            return Response({
                "error": f"Could not resolve pickup location: '{pickup_str}'. Please provide a valid US city, address, or coordinate."
            }, status=status.HTTP_400_BAD_REQUEST)

        geo_dropoff = GeocodingService.geocode(dropoff_str)
        if not geo_dropoff:
            return Response({
                "error": f"Could not resolve dropoff location: '{dropoff_str}'. Please provide a valid US city, address, or coordinate."
            }, status=status.HTTP_400_BAD_REQUEST)

        locations = {
            "current": {
                "query": current_str,
                "coordinates": [geo_current["lat"], geo_current["lon"]],
                "display_name": geo_current["display_name"],
            },
            "pickup": {
                "query": pickup_str,
                "coordinates": [geo_pickup["lat"], geo_pickup["lon"]],
                "display_name": geo_pickup["display_name"],
            },
            "dropoff": {
                "query": dropoff_str,
                "coordinates": [geo_dropoff["lat"], geo_dropoff["lon"]],
                "display_name": geo_dropoff["display_name"],
            }
        }

        # 2. Calculate Road Driving Routes for both legs
        # Leg 1: Current -> Pickup
        leg1_route = RoutingService.get_route([
            (geo_current["lat"], geo_current["lon"]),
            (geo_pickup["lat"], geo_pickup["lon"])
        ])

        # Leg 2: Pickup -> Dropoff
        leg2_route = RoutingService.get_route([
            (geo_pickup["lat"], geo_pickup["lon"]),
            (geo_dropoff["lat"], geo_dropoff["lon"])
        ])

        # 3. Run FMCSA Hours-of-Service Simulation Engine
        engine = HOSSimulationEngine(
            start_time=start_time,
            current_cycle_used=current_cycle_used
        )
        sim_result = engine.simulate(
            locations=locations,
            leg1_route=leg1_route,
            leg2_route=leg2_route
        )

        timeline = sim_result["timeline"]
        stops = sim_result["stops"]

        # 4. Generate Daily ELD Log Sheets (24.0h per sheet)
        daily_logs = DailyLogSheetGenerator.generate_daily_logs(
            timeline=timeline,
            start_time=start_time,
            end_time=sim_result["end_time"],
            initial_cycle_used=current_cycle_used,
            origin_name=geo_current["display_name"],
            destination_name=geo_dropoff["display_name"],
            carrier_name=carrier_name,
            truck_number=truck_num,
            trailer_number=trailer_num
        )

        # 5. Build Combined Route Geometry for Leaflet / OSM
        combined_coords = []
        if leg1_route.get("coordinates"):
            combined_coords.extend(leg1_route["coordinates"])
        if leg2_route.get("coordinates"):
            combined_coords.extend(leg2_route["coordinates"])

        # 6. Format stops serialization
        serialized_stops = []
        for s in stops:
            serialized_stops.append({
                "id": s.id,
                "stop_type": s.stop_type,
                "name": s.name,
                "location_name": s.location_name,
                "coordinates": [s.coordinates[0], s.coordinates[1]],
                "arrival_time": s.arrival_time.isoformat(),
                "departure_time": s.departure_time.isoformat(),
                "duration_minutes": s.duration_minutes,
                "duty_status": s.duty_status.value,
                "duty_status_display": s.duty_status.display_label,
                "mile_marker": s.mile_marker,
                "reason": s.reason,
                "leg_id": s.leg_id
            })

        # 7. Format timeline events serialization
        serialized_timeline = []
        for e in timeline:
            serialized_timeline.append({
                "id": e.id,
                "event_type": e.event_type.value,
                "duty_status": e.duty_status.value,
                "duty_status_display": e.duty_status.display_label,
                "start_time": e.start_time.isoformat(),
                "end_time": e.end_time.isoformat(),
                "duration_minutes": e.duration_minutes,
                "duration_hours": e.duration_hours,
                "start_mile": e.start_mile,
                "end_mile": e.end_mile,
                "distance_miles": e.distance_miles,
                "location_name": e.location_name,
                "coordinates": [e.coordinates[0], e.coordinates[1]],
                "remarks": e.remarks,
                "leg_id": e.leg_id,
                "shift_driving_at_end": e.shift_driving_at_end,
                "shift_elapsed_at_end": e.shift_elapsed_at_end,
                "cycle_used_at_end": e.cycle_used_at_end,
            })

        # Count stop types
        fuel_count = sum(1 for s in stops if s.stop_type == "fuel")
        break_count = sum(1 for s in stops if s.stop_type == "rest_break")
        sleep_count = sum(1 for s in stops if s.stop_type == "sleeper_rest")
        restart_count = sum(1 for s in stops if s.stop_type == "restart_34h")

        return Response({
            "status": "success",
            "summary": {
                "total_distance_miles": sim_result["total_distance_miles"],
                "total_driving_hours": sim_result["total_driving_hours"],
                "total_on_duty_hours": sim_result["total_on_duty_hours"],
                "total_trip_duration_hours": sim_result["total_trip_hours"],
                "total_calendar_days": len(daily_logs),
                "leg1_distance_miles": leg1_route["distance_miles"],
                "leg2_distance_miles": leg2_route["distance_miles"],
                "current_cycle_used_hours": current_cycle_used,
                "cycle_remaining_hours": round(max(0.0, 70.0 - current_cycle_used), 1),
                "final_cycle_used_hours": sim_result["final_cycle_used_hours"],
                "counts": {
                    "total_stops": len(stops),
                    "fuel_stops": fuel_count,
                    "rest_breaks": break_count,
                    "sleeper_rests": sleep_count,
                    "cycle_restarts": restart_count,
                },
                "start_time": start_time.isoformat(),
                "end_time": sim_result["end_time"].isoformat(),
            },
            "locations": locations,
            "route_geometry": {
                "type": "LineString",
                "coordinates": combined_coords
            },
            "legs": {
                "leg1": {
                    "from": geo_current["display_name"],
                    "to": geo_pickup["display_name"],
                    "distance_miles": leg1_route["distance_miles"],
                    "duration_hours": leg1_route["duration_hours"],
                    "geometry": leg1_route.get("geometry", {})
                },
                "leg2": {
                    "from": geo_pickup["display_name"],
                    "to": geo_dropoff["display_name"],
                    "distance_miles": leg2_route["distance_miles"],
                    "duration_hours": leg2_route["duration_hours"],
                    "geometry": leg2_route.get("geometry", {})
                }
            },
            "stops": serialized_stops,
            "timeline": serialized_timeline,
            "daily_logs": daily_logs,
        }, status=status.HTTP_200_OK)
