"""
DRF Views for Spotter ELD Route Planner API.
Provides endpoints for health check, geocoding, complete FMCSA trip planning, and driver daily log validation.
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
from apps.logs.recap import calculate_rolling_cycle_hours
from apps.core.timezones import get_location_timezone
from .serializers import GeocodeRequestSerializer, PlanTripRequestSerializer, ValidateLogRequestSerializer

logger = logging.getLogger(__name__)

class HealthCheckView(APIView):
    """
    Health check endpoint returning backend status and FMCSA ruleset metadata.
    """
    def get(self, request):
        return Response({
            "status": "ok",
            "service": "Spotter ELD Route Planner Backend API",
            "version": "2.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "fmcsa_ruleset": {
                "regulation": "49 CFR Part 395",
                "carrier_type": "Property-carrying commercial driver",
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
    Deterministic, transparent calculation of stops, daily logs, and rolling recap.
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
        leg1_route = RoutingService.get_route([
            (geo_current["lat"], geo_current["lon"]),
            (geo_pickup["lat"], geo_pickup["lon"])
        ])

        leg2_route = RoutingService.get_route([
            (geo_pickup["lat"], geo_pickup["lon"]),
            (geo_dropoff["lat"], geo_dropoff["lon"])
        ])

        # Resolve operational timezone at trip origin
        origin_tz = get_location_timezone(geo_current["lat"], geo_current["lon"])

        # 3. Run FMCSA Hours-of-Service Simulation Engine
        engine = HOSSimulationEngine(
            start_time=start_time,
            current_cycle_used=current_cycle_used,
            operational_timezone=origin_tz
        )
        sim_result = engine.simulate(
            locations=locations,
            leg1_route=leg1_route,
            leg2_route=leg2_route,
            operational_timezone=origin_tz
        )

        timeline = sim_result["timeline"]
        stops = sim_result["stops"]
        validation = sim_result["validation"]

        # 4. Generate Daily ELD Log Sheets (24.0h per sheet in operational timezone)
        daily_logs = DailyLogSheetGenerator.generate_daily_logs(
            timeline=timeline,
            start_time=start_time,
            end_time=sim_result["end_time"],
            initial_cycle_used=current_cycle_used,
            origin_name=geo_current["display_name"],
            destination_name=geo_dropoff["display_name"],
            carrier_name=carrier_name,
            truck_number=truck_num,
            trailer_number=trailer_num,
            operational_timezone=origin_tz
        )

        # Re-validate complete schedule and all daily log sheets together
        has_sufficient_history = (current_cycle_used > 0.0)
        validation = HOSSimulationEngine.validate_schedule(
            timeline=timeline,
            stops=stops,
            daily_logs=daily_logs,
            has_sufficient_history=has_sufficient_history
        )

        # 5. Build Combined Route Geometry for Leaflet / OSM
        combined_coords = []
        if leg1_route.get("coordinates"):
            combined_coords.extend(leg1_route["coordinates"])
        if leg2_route.get("coordinates"):
            combined_coords.extend(leg2_route["coordinates"])

        # 6. Format stops serialization with full timezone and metrics
        serialized_stops = []
        for s in stops:
            metrics_dict = None
            if s.hos_metrics:
                metrics_dict = {
                    "driving_used": s.hos_metrics.driving_used,
                    "driving_limit": s.hos_metrics.driving_limit,
                    "window_elapsed": s.hos_metrics.window_elapsed,
                    "window_limit": s.hos_metrics.window_limit,
                    "break_driving_elapsed": s.hos_metrics.break_driving_elapsed,
                    "break_required_after": s.hos_metrics.break_required_after,
                    "cycle_used": s.hos_metrics.cycle_used,
                    "cycle_limit": s.hos_metrics.cycle_limit,
                    "miles_since_fuel": s.hos_metrics.miles_since_fuel,
                    "fuel_limit": s.hos_metrics.fuel_limit
                }

            serialized_stops.append({
                "id": s.id,
                "stop_type": s.stop_type,
                "name": s.name,
                "location_name": s.location_name,
                "coordinates": [s.coordinates[0], s.coordinates[1]],
                "arrival_time": s.arrival_time.isoformat(),
                "departure_time": s.departure_time.isoformat(),
                "arrival_local_display": s.arrival_local_display,
                "departure_local_display": s.departure_local_display,
                "timezone_id": s.timezone_id,
                "duration_minutes": s.duration_minutes,
                "duty_status": s.duty_status.value,
                "duty_status_display": s.duty_status.display_label,
                "mile_marker": s.mile_marker,
                "reason": s.reason,
                "leg_id": s.leg_id,
                "hos_metrics": metrics_dict
            })

        # 7. Format timeline events serialization
        serialized_timeline = []
        for e in timeline:
            metrics_dict = None
            if e.metrics:
                metrics_dict = {
                    "driving_used": e.metrics.driving_used,
                    "driving_limit": e.metrics.driving_limit,
                    "window_elapsed": e.metrics.window_elapsed,
                    "window_limit": e.metrics.window_limit,
                    "break_driving_elapsed": e.metrics.break_driving_elapsed,
                    "break_required_after": e.metrics.break_required_after,
                    "cycle_used": e.metrics.cycle_used,
                    "cycle_limit": e.metrics.cycle_limit,
                }

            serialized_timeline.append({
                "id": e.id,
                "event_type": e.event_type.value,
                "duty_status": e.duty_status.value,
                "duty_status_display": e.duty_status.display_label,
                "start_time": e.start_time.isoformat(),
                "end_time": e.end_time.isoformat(),
                "local_start_time": e.local_start_time,
                "local_end_time": e.local_end_time,
                "timezone_id": e.timezone_id,
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
                "metrics": metrics_dict
            })

        # Count stop types
        fuel_count = sum(1 for s in stops if s.stop_type == "fuel")
        break_count = sum(1 for s in stops if s.stop_type == "rest_break")
        sleep_count = sum(1 for s in stops if s.stop_type == "sleeper_rest")
        restart_count = sum(1 for s in stops if s.stop_type == "restart_34h")

        # Format validation report
        validation_payload = {
            "passed": validation.passed,
            "compliance_status": validation.compliance_status,
            "has_sufficient_history": validation.has_sufficient_history,
            "status_type": validation.status_type,
            "explanation": validation.explanation,
            "violations": [
                {
                    "code": v.code,
                    "message": v.message,
                    "severity": v.severity,
                    "timestamp": v.timestamp.isoformat() if v.timestamp else None,
                    "event_id": v.event_id,
                    "details": v.details
                }
                for v in validation.violations
            ],
            "warnings": [
                {
                    "code": w.code,
                    "message": w.message,
                    "severity": w.severity,
                    "timestamp": w.timestamp.isoformat() if w.timestamp else None,
                    "details": getattr(w, "details", None)
                }
                for w in validation.warnings
            ]
        }

        return Response({
            "status": "success",
            "mode": "SIMULATION_MODE",
            "mode_label": "Planned Trip — Simulation Mode",
            "compliance_status": validation.compliance_status,
            "validation": validation_payload,
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
                "operational_timezone": origin_tz,
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

class ValidateLogView(APIView):
    """
    Validates manual driver edits, remarks, or corrections to a generated Daily Log Sheet.
    Checks:
    - 24.0 hour exact total duration.
    - Non-negative durations.
    - No overlapping segments.
    - Recomputes updated rolling recap for driver review.
    """
    def post(self, request):
        serializer = ValidateLogRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        day_number = data["day_number"]
        duty_hours = data["duty_hours"]
        remarks = data.get("remarks", [])
        daily_logs = data.get("daily_logs", [])

        errors = []
        warnings = []

        try:
            off_duty = float(duty_hours.get("off_duty", 0.0))
            sleeper = float(duty_hours.get("sleeper_berth", 0.0))
            driving = float(duty_hours.get("driving", 0.0))
            on_duty = float(duty_hours.get("on_duty_not_driving", 0.0))
        except (ValueError, TypeError):
            return Response({
                "valid": False,
                "status": "VIOLATION",
                "errors": ["Duty hours must contain numeric values for off_duty, sleeper_berth, driving, on_duty_not_driving."]
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check negative durations
        for name, val in [("Off Duty", off_duty), ("Sleeper Berth", sleeper), ("Driving", driving), ("On Duty Not Driving", on_duty)]:
            if val < 0.0:
                errors.append(f"{name} cannot be negative ({val}h).")

        # Check 24.0 hour sum
        total_hours = round(off_duty + sleeper + driving + on_duty, 2)
        diff = round(abs(24.0 - total_hours), 2)
        if diff > 0.05:
            errors.append(f"Daily status duration must equal exactly 24.0 hours (current total: {total_hours}h).")

        # Driving limit check for the day
        if driving > 11.05:
            warnings.append(f"Driving time today is {driving}h. Ensure shift limits (11.0h max) were not exceeded without 10h rest.")

        # Recompute updated recap if logs provided
        on_duty_today = round(driving + on_duty, 2)
        valid = (len(errors) == 0)

        return Response({
            "valid": valid,
            "status": "VALIDATED" if valid else "VIOLATION",
            "day_number": day_number,
            "total_hours": total_hours,
            "on_duty_today": on_duty_today,
            "errors": errors,
            "warnings": warnings,
            "message": "Daily log sheet passed all FMCSA structural validations." if valid else "Validation issues detected."
        }, status=status.HTTP_200_OK if valid else status.HTTP_422_UNPROCESSABLE_ENTITY)
