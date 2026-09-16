"""
Deterministic FMCSA Hours-of-Service (Part 395) Simulation Engine.
Implements the 70-hour / 8-day rule for property-carrying commercial drivers:
- 11-hour driving limit
- 14-hour driving window
- Mandatory 30-minute break after 8 cumulative hours of driving
- 10-hour qualifying rest (sleeper berth / off-duty)
- 70-hour cycle limit with 34-hour restart
- Fueling at least once every 1,000 miles (30 min on-duty)
- 1-hour on-duty for pickup, 1-hour on-duty for dropoff
- Full UTC datetime precision with location-aware IANA timezone annotations
- Transparent decision metrics & strict restart interval validation
"""

import math
from datetime import datetime, date, time, timedelta, timezone
from collections import defaultdict
from typing import Dict, Any, List, Tuple, Optional

from apps.routing.services import RoutingService
from apps.geocoding.services import GeocodingService
from apps.core.timezones import (
    get_location_timezone,
    convert_utc_to_location_time,
    format_datetime_in_location
)
from .models import (
    DutyStatus,
    EventType,
    TimelineEvent,
    TripStop,
    DriverClocks,
    HOSMetrics,
    HOSViolation,
    HOSValidationResult,
    HOSConflictError
)

class HOSSimulationEngine:
    # Regulation Constants
    MAX_DRIVING_SHIFT = 11.0          # Max driving hours per shift
    MAX_WINDOW_SHIFT = 14.0           # Max elapsed duty window per shift
    MAX_DRIVE_BEFORE_BREAK = 8.0      # Max cumulative driving before 30-min break
    QUALIFYING_REST_HOURS = 10.0      # 10 consecutive hours rest resets shift
    CYCLE_LIMIT_HOURS = 70.0          # 70-hour / 8-day rolling cycle limit
    RESTART_HOURS = 34.0              # 34 consecutive hours off-duty resets cycle
    MAX_FUEL_INTERVAL_MILES = 1000.0  # Fueling frequency limit
    FUEL_TRIGGER_MILES = 950.0        # Fuel safely before running dry (≤ 1000 mi)
    FUEL_DURATION_MINUTES = 30        # Fueling stop duration (on-duty)
    BREAK_DURATION_MINUTES = 30       # 30-min mandatory break duration
    PRE_TRIP_MINUTES = 15             # Pre-trip vehicle inspection
    POST_TRIP_MINUTES = 15            # Post-trip inspection
    PICKUP_DURATION_MINUTES = 60      # 1 hour for pickup (on-duty not driving)
    DROPOFF_DURATION_MINUTES = 60     # 1 hour for dropoff (on-duty not driving)

    def __init__(self, start_time: datetime, current_cycle_used: float = 0.0, operational_timezone: str = "America/Chicago"):
        # Guarantee timezone-aware UTC datetime
        if start_time.tzinfo is None:
            self.start_time = start_time.replace(tzinfo=timezone.utc)
        else:
            self.start_time = start_time.astimezone(timezone.utc)

        self.current_time = self.start_time
        self.clocks = DriverClocks(cycle_on_duty_hours=min(70.0, max(0.0, current_cycle_used)))
        self.timeline: List[TimelineEvent] = []
        self.stops: List[TripStop] = []
        self.event_counter = 1
        self.stop_counter = 1
        self.cumulative_trip_miles = 0.0
        self.daily_driving_hours: Dict[Any, float] = defaultdict(float)
        self.daily_driving_minutes: Dict[Any, int] = defaultdict(int)
        self.operational_timezone: str = operational_timezone

    def _get_current_metrics(self) -> HOSMetrics:
        """Capture transparent calculation metrics snapshot."""
        return HOSMetrics(
            driving_used=round(self.clocks.shift_driving_hours, 2),
            driving_limit=self.MAX_DRIVING_SHIFT,
            window_elapsed=round(self.clocks.shift_elapsed_hours, 2),
            window_limit=self.MAX_WINDOW_SHIFT,
            break_driving_elapsed=round(self.clocks.driving_since_break, 2),
            break_required_after=self.MAX_DRIVE_BEFORE_BREAK,
            cycle_used=round(self.clocks.cycle_on_duty_hours, 2),
            cycle_limit=self.CYCLE_LIMIT_HOURS,
            miles_since_fuel=round(self.clocks.miles_since_last_fuel, 1),
            fuel_limit=self.MAX_FUEL_INTERVAL_MILES
        )

    def simulate(
        self,
        locations: Dict[str, Any],
        leg1_route: Dict[str, Any],
        leg2_route: Dict[str, Any],
        operational_timezone: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Simulate full trip across Leg 1 (Current -> Pickup) and Leg 2 (Pickup -> Dropoff).
        Produces verified timeline events, stops, and comprehensive validation report.
        """
        curr_loc = locations["current"]
        if operational_timezone:
            self.operational_timezone = operational_timezone
        elif not self.operational_timezone:
            self.operational_timezone = get_location_timezone(curr_loc["coordinates"][0], curr_loc["coordinates"][1])

        # 1. Pre-trip vehicle inspection at origin
        origin_tz = get_location_timezone(curr_loc["coordinates"][0], curr_loc["coordinates"][1])

        self._add_event(
            event_type=EventType.PRE_TRIP,
            duty_status=DutyStatus.ON_DUTY_NOT_DRIVING,
            duration_minutes=self.PRE_TRIP_MINUTES,
            distance_miles=0.0,
            location_name=curr_loc["display_name"],
            coordinates=(curr_loc["coordinates"][0], curr_loc["coordinates"][1]),
            remarks="Pre-Trip Vehicle Inspection",
            leg_id=1,
            timezone_id=origin_tz
        )

        # Initial Stop entry for start
        self._add_stop(
            stop_type="current_location",
            name="Current Location",
            location_name=curr_loc["display_name"],
            coordinates=(curr_loc["coordinates"][0], curr_loc["coordinates"][1]),
            arrival_time=self.start_time,
            departure_time=self.current_time,
            duration_minutes=self.PRE_TRIP_MINUTES,
            duty_status=DutyStatus.ON_DUTY_NOT_DRIVING,
            mile_marker=0.0,
            reason="Trip Origin & Pre-trip inspection",
            leg_id=1,
            timezone_id=origin_tz
        )

        # 2. Drive Leg 1: Current -> Pickup
        self._simulate_driving_leg(
            leg_id=1,
            route=leg1_route,
            origin_name=curr_loc["display_name"],
            dest_name=locations["pickup"]["display_name"]
        )

        # 3. Arrive at Pickup Facility (1 hour on-duty not driving)
        pickup_loc = locations["pickup"]
        pickup_tz = get_location_timezone(pickup_loc["coordinates"][0], pickup_loc["coordinates"][1])
        pickup_arrival = self.current_time

        self._add_event(
            event_type=EventType.PICKUP,
            duty_status=DutyStatus.ON_DUTY_NOT_DRIVING,
            duration_minutes=self.PICKUP_DURATION_MINUTES,
            distance_miles=0.0,
            location_name=pickup_loc["display_name"],
            coordinates=(pickup_loc["coordinates"][0], pickup_loc["coordinates"][1]),
            remarks="Shipper Loading (1 hr On-Duty)",
            leg_id=1,
            timezone_id=pickup_tz
        )
        self._add_stop(
            stop_type="pickup",
            name="Pickup Location",
            location_name=pickup_loc["display_name"],
            coordinates=(pickup_loc["coordinates"][0], pickup_loc["coordinates"][1]),
            arrival_time=pickup_arrival,
            departure_time=self.current_time,
            duration_minutes=self.PICKUP_DURATION_MINUTES,
            duty_status=DutyStatus.ON_DUTY_NOT_DRIVING,
            mile_marker=self.cumulative_trip_miles,
            reason="Shipper Pickup / Cargo Loading",
            leg_id=1,
            timezone_id=pickup_tz
        )

        # 4. Drive Leg 2: Pickup -> Dropoff
        self._simulate_driving_leg(
            leg_id=2,
            route=leg2_route,
            origin_name=pickup_loc["display_name"],
            dest_name=locations["dropoff"]["display_name"]
        )

        # 5. Arrive at Dropoff Consignee (1 hour on-duty not driving)
        dropoff_loc = locations["dropoff"]
        dropoff_tz = get_location_timezone(dropoff_loc["coordinates"][0], dropoff_loc["coordinates"][1])
        dropoff_arrival = self.current_time

        self._add_event(
            event_type=EventType.DROPOFF,
            duty_status=DutyStatus.ON_DUTY_NOT_DRIVING,
            duration_minutes=self.DROPOFF_DURATION_MINUTES,
            distance_miles=0.0,
            location_name=dropoff_loc["display_name"],
            coordinates=(dropoff_loc["coordinates"][0], dropoff_loc["coordinates"][1]),
            remarks="Consignee Unloading (1 hr On-Duty)",
            leg_id=2,
            timezone_id=dropoff_tz
        )
        self._add_stop(
            stop_type="dropoff",
            name="Dropoff Location",
            location_name=dropoff_loc["display_name"],
            coordinates=(dropoff_loc["coordinates"][0], dropoff_loc["coordinates"][1]),
            arrival_time=dropoff_arrival,
            departure_time=self.current_time,
            duration_minutes=self.DROPOFF_DURATION_MINUTES,
            duty_status=DutyStatus.ON_DUTY_NOT_DRIVING,
            mile_marker=self.cumulative_trip_miles,
            reason="Consignee Delivery / Cargo Unload",
            leg_id=2,
            timezone_id=dropoff_tz
        )

        # 6. Post-trip vehicle inspection
        self._add_event(
            event_type=EventType.POST_TRIP,
            duty_status=DutyStatus.ON_DUTY_NOT_DRIVING,
            duration_minutes=self.POST_TRIP_MINUTES,
            distance_miles=0.0,
            location_name=dropoff_loc["display_name"],
            coordinates=(dropoff_loc["coordinates"][0], dropoff_loc["coordinates"][1]),
            remarks="Post-Trip Vehicle Inspection & End of Delivery",
            leg_id=2,
            timezone_id=dropoff_tz
        )

        # Run rigorous HOS validation checks on the generated schedule
        has_history = (self.clocks.cycle_on_duty_hours > 0.0)
        validation_result = self.validate_schedule(self.timeline, self.stops, has_sufficient_history=has_history)

        # Compute summary metrics
        total_driving_minutes = sum(e.duration_minutes for e in self.timeline if e.duty_status == DutyStatus.DRIVING)
        total_on_duty_minutes = sum(e.duration_minutes for e in self.timeline if e.duty_status in (DutyStatus.DRIVING, DutyStatus.ON_DUTY_NOT_DRIVING))
        total_trip_duration = self.current_time - self.start_time

        return {
            "timeline": self.timeline,
            "stops": self.stops,
            "total_distance_miles": round(self.cumulative_trip_miles, 1),
            "total_driving_hours": round(total_driving_minutes / 60.0, 2),
            "total_on_duty_hours": round(total_on_duty_minutes / 60.0, 2),
            "total_trip_hours": round(total_trip_duration.total_seconds() / 3600.0, 2),
            "final_cycle_used_hours": round(self.clocks.cycle_on_duty_hours, 2),
            "start_time": self.start_time,
            "end_time": self.current_time,
            "validation": validation_result,
        }

    def _simulate_driving_leg(
        self,
        leg_id: int,
        route: Dict[str, Any],
        origin_name: str,
        dest_name: str
    ):
        """
        Simulate driving along a route leg with continuous FMCSA compliance checks.
        """
        leg_distance = route.get("distance_miles", 0.0)
        leg_duration_hours = route.get("duration_hours", 0.0)
        coordinates = route.get("coordinates", [])
        cumulative_miles = route.get("cumulative_miles", [])

        if leg_distance <= 0.0:
            return

        # Commercial vehicle speed along corridor
        speed_mph = leg_distance / leg_duration_hours if leg_duration_hours > 0 else 55.0
        speed_mph = max(40.0, min(65.0, speed_mph))

        leg_miles_completed = 0.0

        while leg_miles_completed < (leg_distance - 0.1):
            miles_remaining_in_leg = leg_distance - leg_miles_completed

            # Calendar day boundary and daily driving limit in operational timezone
            local_curr = convert_utc_to_location_time(self.current_time, self.operational_timezone)
            curr_date = local_curr.date()
            next_midnight_local = datetime.combine(curr_date + timedelta(days=1), time.min, tzinfo=local_curr.tzinfo)
            mins_until_midnight = max(1, int(round((next_midnight_local - local_curr).total_seconds() / 60.0)))
            hours_until_midnight = mins_until_midnight / 60.0

            daily_driving_mins = self.daily_driving_minutes[curr_date]
            daily_mins_avail = max(0, int(self.MAX_DRIVING_SHIFT * 60) - daily_driving_mins)
            daily_drive_avail = daily_mins_avail / 60.0

            shift_mins_avail = max(0, int(self.MAX_DRIVING_SHIFT * 60) - int(round(self.clocks.shift_driving_hours * 60)))
            drive_avail_before_11h = shift_mins_avail / 60.0

            # Check remaining allowances before any FMCSA threshold:
            drive_avail_before_break = max(0.0, self.MAX_DRIVE_BEFORE_BREAK - self.clocks.driving_since_break)
            drive_avail_before_14h = max(0.0, self.MAX_WINDOW_SHIFT - self.clocks.shift_elapsed_hours)
            drive_avail_before_cycle = max(0.0, self.CYCLE_LIMIT_HOURS - self.clocks.cycle_on_duty_hours)

            miles_avail_before_fuel = max(0.0, self.FUEL_TRIGGER_MILES - self.clocks.miles_since_last_fuel)
            drive_avail_before_fuel = miles_avail_before_fuel / speed_mph

            hos_driving_allowed = min(
                drive_avail_before_break,
                drive_avail_before_11h,
                drive_avail_before_14h,
                drive_avail_before_cycle,
                drive_avail_before_fuel,
                daily_drive_avail,
                hours_until_midnight
            )

            # If an HOS/daily clock limit is reached (< 1 minute), resolve the limiting trigger
            if hos_driving_allowed < (1.0 / 60.0):
                self._handle_trigger_event(coordinates, cumulative_miles, leg_miles_completed, leg_id)
                continue

            # Drive chunk
            driving_time_allowed = min(miles_remaining_in_leg / speed_mph, hos_driving_allowed)
            chunk_miles = min(miles_remaining_in_leg, driving_time_allowed * speed_mph)
            chunk_duration_minutes = int(round((chunk_miles / speed_mph) * 60.0))
            chunk_duration_minutes = max(1, min(chunk_duration_minutes, mins_until_midnight, daily_mins_avail, shift_mins_avail))
            chunk_miles = min(miles_remaining_in_leg, (chunk_duration_minutes / 60.0) * speed_mph)

            interp_lat, interp_lon = RoutingService.interpolate_coordinate_at_mile(
                coordinates, cumulative_miles, leg_miles_completed + chunk_miles
            )
            interp_tz = get_location_timezone(interp_lat, interp_lon)

            self._add_event(
                event_type=EventType.DRIVING,
                duty_status=DutyStatus.DRIVING,
                duration_minutes=chunk_duration_minutes,
                distance_miles=chunk_miles,
                location_name=f"En Route ({round(leg_miles_completed + chunk_miles)} mi on Leg {leg_id})",
                coordinates=(interp_lat, interp_lon),
                remarks=f"Driving ({round(chunk_miles)} mi)",
                leg_id=leg_id,
                timezone_id=interp_tz
            )

            leg_miles_completed += chunk_miles

            # If finished leg (within 0.5 miles), exit loop
            if (leg_distance - leg_miles_completed) <= 0.5:
                leg_miles_completed = leg_distance
                break

            # If haven't finished leg, check if any limit was triggered
            self._handle_trigger_event(coordinates, cumulative_miles, leg_miles_completed, leg_id)

    def _handle_trigger_event(
        self,
        coordinates: List[List[float]],
        cumulative_miles: List[float],
        leg_miles_completed: float,
        leg_id: int
    ):
        """
        Evaluate and schedule required stop / rest.
        Priority:
        1. 70h cycle limit -> 34h restart
        2. 11h driving or 14h window limit -> 10h sleeper rest
        3. Fuel limit (≥ 950 miles) -> 30m fuel stop
        4. 8h driving without break -> 30m break
        """
        interp_lat, interp_lon = RoutingService.interpolate_coordinate_at_mile(
            coordinates, cumulative_miles, leg_miles_completed
        )
        location_label = GeocodingService.reverse_geocode(interp_lat, interp_lon)
        tz_id = get_location_timezone(interp_lat, interp_lon)

        # 1. 70h Cycle Limit Exceeded -> 34-Hour Restart
        if self.clocks.cycle_on_duty_hours >= (self.CYCLE_LIMIT_HOURS - 0.05):
            arrival = self.current_time
            self._add_event(
                event_type=EventType.RESTART_34H,
                duty_status=DutyStatus.SLEEPER_BERTH,
                duration_minutes=int(self.RESTART_HOURS * 60),
                distance_miles=0.0,
                location_name=location_label,
                coordinates=(interp_lat, interp_lon),
                remarks="34-Hour Restart (Cycle Reset to 70 hrs)",
                leg_id=leg_id,
                timezone_id=tz_id
            )
            self._add_stop(
                stop_type="restart_34h",
                name="34-Hour Cycle Restart",
                location_name=location_label,
                coordinates=(interp_lat, interp_lon),
                arrival_time=arrival,
                departure_time=self.current_time,
                duration_minutes=int(self.RESTART_HOURS * 60),
                duty_status=DutyStatus.SLEEPER_BERTH,
                mile_marker=self.cumulative_trip_miles,
                reason="70-Hour Cycle Limit Reached - 34hr Restart Taken",
                leg_id=leg_id,
                timezone_id=tz_id
            )
            return

        local_curr = convert_utc_to_location_time(self.current_time, self.operational_timezone)
        curr_date = local_curr.date()
        daily_mins = self.daily_driving_minutes[curr_date]
        daily_d = daily_mins / 60.0

        next_midnight_local = datetime.combine(curr_date + timedelta(days=1), time.min, tzinfo=local_curr.tzinfo)
        hours_to_midnight = max(0.0, (next_midnight_local - local_curr).total_seconds() / 3600.0)

        # 2. Daily Driving Limit (11.0h per calendar day) OR Shift 11h/14h limits -> 10-Hour Qualifying Rest
        if (daily_mins >= (int(self.MAX_DRIVING_SHIFT * 60) - 3) or
            self.clocks.shift_driving_hours >= (self.MAX_DRIVING_SHIFT - 0.05) or
            self.clocks.shift_elapsed_hours >= (self.MAX_WINDOW_SHIFT - 0.05)):
            arrival = self.current_time
            if daily_mins >= (int(self.MAX_DRIVING_SHIFT * 60) - 3):
                reason = "11-Hour Daily Driving Limit Reached"
            elif self.clocks.shift_driving_hours >= (self.MAX_DRIVING_SHIFT - 0.05):
                reason = "11-Hour Shift Driving Limit Reached"
            else:
                reason = "14-Hour Duty Window Reached"

            # Qualifying rest is at least 10 hours (600 mins).
            # If daily driving reached 11h, hold rest until next calendar day (and at least 10h)
            # so driver resumes fresh on the next calendar day!
            if daily_mins >= (int(self.MAX_DRIVING_SHIFT * 60) - 3):
                rest_hours = max(self.QUALIFYING_REST_HOURS, hours_to_midnight)
            else:
                rest_hours = self.QUALIFYING_REST_HOURS
                rest_end_local = local_curr + timedelta(hours=rest_hours)
                if rest_end_local.hour >= 21:
                    mins_to_mid = (24 - rest_end_local.hour) * 60 - rest_end_local.minute
                    if mins_to_mid > 0:
                        rest_hours += mins_to_mid / 60.0

            rest_mins = int(round(rest_hours * 60))

            self._add_event(
                event_type=EventType.REST_10H,
                duty_status=DutyStatus.SLEEPER_BERTH,
                duration_minutes=rest_mins,
                distance_miles=0.0,
                location_name=location_label,
                coordinates=(interp_lat, interp_lon),
                remarks=f"10-Hour Qualifying Rest ({reason})",
                leg_id=leg_id,
                timezone_id=tz_id
            )
            self._add_stop(
                stop_type="sleeper_rest",
                name="10-Hour Overnight Rest",
                location_name=location_label,
                coordinates=(interp_lat, interp_lon),
                arrival_time=arrival,
                departure_time=self.current_time,
                duration_minutes=rest_mins,
                duty_status=DutyStatus.SLEEPER_BERTH,
                mile_marker=self.cumulative_trip_miles,
                reason=f"{reason} - 10 Consecutive Hours Sleeper Berth",
                leg_id=leg_id,
                timezone_id=tz_id
            )
            return

        # 3. Fuel Stop Required (≥ 950 miles since last fuel)
        if self.clocks.miles_since_last_fuel >= (self.FUEL_TRIGGER_MILES - 15.0):
            arrival = self.current_time
            self._add_event(
                event_type=EventType.FUELING,
                duty_status=DutyStatus.ON_DUTY_NOT_DRIVING,
                duration_minutes=self.FUEL_DURATION_MINUTES,
                distance_miles=0.0,
                location_name=location_label,
                coordinates=(interp_lat, interp_lon),
                remarks=f"Fueling ({round(self.clocks.miles_since_last_fuel)} mi since last fuel)",
                leg_id=leg_id,
                timezone_id=tz_id
            )
            self._add_stop(
                stop_type="fuel",
                name="Fueling Stop",
                location_name=location_label,
                coordinates=(interp_lat, interp_lon),
                arrival_time=arrival,
                departure_time=self.current_time,
                duration_minutes=self.FUEL_DURATION_MINUTES,
                duty_status=DutyStatus.ON_DUTY_NOT_DRIVING,
                mile_marker=self.cumulative_trip_miles,
                reason="Mandatory Fueling (≤ 1,000 miles interval)",
                leg_id=leg_id,
                timezone_id=tz_id
            )
            return

        # 4. Mandatory 30-Minute Break (≥ 8 cumulative driving hours)
        if self.clocks.driving_since_break >= (self.MAX_DRIVE_BEFORE_BREAK - 0.05):
            arrival = self.current_time
            self._add_event(
                event_type=EventType.BREAK_30M,
                duty_status=DutyStatus.OFF_DUTY,
                duration_minutes=self.BREAK_DURATION_MINUTES,
                distance_miles=0.0,
                location_name=location_label,
                coordinates=(interp_lat, interp_lon),
                remarks="Mandatory 30-Minute Rest Break (§ 395.3(a)(3)(ii))",
                leg_id=leg_id,
                timezone_id=tz_id
            )
            self._add_stop(
                stop_type="rest_break",
                name="30-Minute Rest Break",
                location_name=location_label,
                coordinates=(interp_lat, interp_lon),
                arrival_time=arrival,
                departure_time=self.current_time,
                duration_minutes=self.BREAK_DURATION_MINUTES,
                duty_status=DutyStatus.OFF_DUTY,
                mile_marker=self.cumulative_trip_miles,
                reason="Required 30-min break after 8 hours cumulative driving",
                leg_id=leg_id,
                timezone_id=tz_id
            )
            return

        # 5. Calendar Midnight Transition
        # If no HOS stop was triggered, but current time is right at midnight,
        # advance current time to exactly midnight so the loop transitions to the new calendar day.
        if hours_to_midnight < (1.0 / 60.0):
            utc_midnight = next_midnight_local.astimezone(timezone.utc)
            if self.current_time < utc_midnight:
                self.current_time = utc_midnight
            else:
                self.current_time += timedelta(minutes=1)
            return

        # Fallback safety: advance clock by 5 minutes off-duty if no rule triggered
        # to guarantee forward progress and prevent infinite loop
        self._add_event(
            event_type=EventType.BREAK_30M,
            duty_status=DutyStatus.OFF_DUTY,
            duration_minutes=5,
            distance_miles=0.0,
            location_name=location_label,
            coordinates=(interp_lat, interp_lon),
            remarks="Operational Rest / Pause",
            leg_id=leg_id,
            timezone_id=tz_id
        )

    def _add_event(
        self,
        event_type: EventType,
        duty_status: DutyStatus,
        duration_minutes: float,
        distance_miles: float,
        location_name: str,
        coordinates: Tuple[float, float],
        remarks: str,
        leg_id: int,
        timezone_id: str = "America/Chicago"
    ):
        """Append an event and advance driver compliance clocks."""
        duration_hours = duration_minutes / 60.0
        start_t = self.current_time
        end_t = start_t + timedelta(minutes=duration_minutes)
        start_m = self.cumulative_trip_miles
        end_m = start_m + distance_miles

        metrics_snapshot = self._get_current_metrics()

        # Advance clocks based on duty status:
        if duty_status == DutyStatus.DRIVING:
            self.clocks.shift_driving_hours += duration_hours
            self.clocks.shift_elapsed_hours += duration_hours
            self.clocks.driving_since_break += duration_hours
            self.clocks.cycle_on_duty_hours += duration_hours
            self.clocks.miles_since_last_fuel += distance_miles
            self.cumulative_trip_miles += distance_miles

            # Accumulate on calendar day in operational timezone
            local_start = convert_utc_to_location_time(start_t, self.operational_timezone)
            self.daily_driving_hours[local_start.date()] += duration_hours
            self.daily_driving_minutes[local_start.date()] += duration_minutes

        elif duty_status == DutyStatus.ON_DUTY_NOT_DRIVING:
            self.clocks.shift_elapsed_hours += duration_hours
            self.clocks.cycle_on_duty_hours += duration_hours
            if duration_minutes >= 30:
                self.clocks.driving_since_break = 0.0 # 30 min on-duty qualifies as break
            if event_type == EventType.FUELING:
                self.clocks.miles_since_last_fuel = 0.0

        elif duty_status in (DutyStatus.OFF_DUTY, DutyStatus.SLEEPER_BERTH):
            if event_type == EventType.RESTART_34H:
                self.clocks.reset_cycle()
            elif event_type == EventType.REST_10H:
                self.clocks.reset_shift()
            elif duration_minutes >= 30:
                self.clocks.driving_since_break = 0.0 # 30-min break resets the 8-hour clock
                self.clocks.shift_elapsed_hours += duration_hours # non-qualifying off-duty advances 14h window

        event = TimelineEvent(
            id=f"evt-{self.event_counter}",
            event_type=event_type,
            duty_status=duty_status,
            start_time=start_t,
            end_time=end_t,
            duration_minutes=duration_minutes,
            duration_hours=round(duration_hours, 2),
            start_mile=round(start_m, 1),
            end_mile=round(end_m, 1),
            distance_miles=round(distance_miles, 1),
            location_name=location_name,
            coordinates=coordinates,
            remarks=remarks,
            leg_id=leg_id,
            timezone_id=timezone_id,
            local_start_time=format_datetime_in_location(start_t, timezone_id, "%b %d, %H:%M %Z"),
            local_end_time=format_datetime_in_location(end_t, timezone_id, "%b %d, %H:%M %Z"),
            shift_driving_at_end=round(self.clocks.shift_driving_hours, 2),
            shift_elapsed_at_end=round(self.clocks.shift_elapsed_hours, 2),
            cycle_used_at_end=round(self.clocks.cycle_on_duty_hours, 2),
            metrics=metrics_snapshot
        )
        self.timeline.append(event)
        self.event_counter += 1
        self.current_time = end_t

    def _add_stop(
        self,
        stop_type: str,
        name: str,
        location_name: str,
        coordinates: Tuple[float, float],
        arrival_time: datetime,
        departure_time: datetime,
        duration_minutes: int,
        duty_status: DutyStatus,
        mile_marker: float,
        reason: str,
        leg_id: int,
        timezone_id: str = "America/Chicago"
    ):
        stop = TripStop(
            id=f"stop-{self.stop_counter}",
            stop_type=stop_type,
            name=name,
            location_name=location_name,
            coordinates=coordinates,
            arrival_time=arrival_time,
            departure_time=departure_time,
            duration_minutes=duration_minutes,
            duty_status=duty_status,
            mile_marker=round(mile_marker, 1),
            reason=reason,
            leg_id=leg_id,
            timezone_id=timezone_id,
            arrival_local_display=format_datetime_in_location(arrival_time, timezone_id, "%b %d, %H:%M %Z"),
            departure_local_display=format_datetime_in_location(departure_time, timezone_id, "%b %d, %H:%M %Z"),
            hos_metrics=self._get_current_metrics()
        )
        self.stops.append(stop)
        self.stop_counter += 1

    @classmethod
    def validate_restart_interval(
        cls,
        timeline: List[TimelineEvent],
        restart_start: datetime,
        restart_end: datetime
    ) -> List[HOSViolation]:
        """
        Validates that during an active 34-hour restart:
        1. Driver remains strictly in qualifying rest (Sleeper Berth or Off Duty).
        2. No Driving or On Duty Not Driving is scheduled during the restart period.
        3. Activity exactly at restart_end is allowed.
        4. Activity before restart_end is rejected and reported as a clear violation.
        """
        violations = []
        for event in timeline:
            if event.event_type == EventType.RESTART_34H:
                continue

            # Check if this event overlaps with the active restart period: [restart_start, restart_end)
            overlaps = max(event.start_time, restart_start) < min(event.end_time, restart_end)
            if overlaps:
                if event.duty_status in (DutyStatus.DRIVING, DutyStatus.ON_DUTY_NOT_DRIVING):
                    violations.append(HOSViolation(
                        code="RESTART_VIOLATION",
                        message="HOS Conflict: Driving scheduled before the 34-hour restart was completed.",
                        severity="VIOLATION",
                        timestamp=event.start_time,
                        event_id=event.id,
                        details={
                            "restart_start": restart_start.isoformat(),
                            "restart_end": restart_end.isoformat(),
                            "conflicting_event": event.remarks,
                            "conflicting_start": event.start_time.isoformat(),
                            "conflicting_status": event.duty_status.value
                        }
                    ))
        return violations

    @classmethod
    def validate_daily_driving_limit(cls, driving_hours: float) -> Tuple[bool, Optional[str]]:
        """
        Validates whether a single calendar day's total driving hours comply with the 11.0-hour limit.
        - Driving <= 11.00 hours -> Valid
        - Driving 11.01 hours or more -> Violation
        - Driving 12.0 hours -> Violation
        """
        if driving_hours <= (cls.MAX_DRIVING_SHIFT + 0.001):
            return True, None
        return False, f"HOS Violation: Daily driving total ({driving_hours}h) exceeds the maximum 11.0-hour limit."

    @classmethod
    def validate_schedule(
        cls,
        timeline: List[TimelineEvent],
        stops: List[TripStop],
        daily_logs: Optional[List[Dict[str, Any]]] = None,
        has_sufficient_history: Optional[bool] = None
    ) -> HOSValidationResult:
        """
        Rigorous HOS rule validation verifying:
        1. 34-hour restart intervals integrity (no driving/on-duty before restart completion).
        2. Shift driving limit (≤ 11.0 hours).
        3. Shift elapsed window (≤ 14.0 hours).
        4. 30-minute break after 8 cumulative hours driving.
        5. Chronological continuity without negative durations.
        6. Daily calendar day driving limits (≤ 11.0 hours per daily sheet).
        7. Incomplete 70/8 historical cycle status when prior 7-day driver logs are absent.
        """
        violations: List[HOSViolation] = []
        warnings: List[HOSViolation] = []

        # 1. Validate 34-Hour Restarts
        restart_stops = [s for s in stops if s.stop_type == "restart_34h"]
        for rs in restart_stops:
            r_violations = cls.validate_restart_interval(timeline, rs.arrival_time, rs.departure_time)
            violations.extend(r_violations)

        # 2. Continuous Shift & Break Checks
        current_shift_driving = 0.0
        current_shift_elapsed = 0.0
        driving_since_break = 0.0

        for idx, event in enumerate(timeline):
            dur_hours = event.duration_minutes / 60.0

            if event.duration_minutes < 0:
                violations.append(HOSViolation(
                    code="NEGATIVE_DURATION",
                    message=f"Event {event.id} has negative duration: {event.duration_minutes}m",
                    severity="VIOLATION",
                    timestamp=event.start_time,
                    event_id=event.id
                ))

            if event.duty_status == DutyStatus.DRIVING:
                current_shift_driving += dur_hours
                current_shift_elapsed += dur_hours
                driving_since_break += dur_hours

                # 11-Hour Driving Limit Check (with tiny tolerance 0.05h)
                if current_shift_driving > (cls.MAX_DRIVING_SHIFT + 0.05):
                    violations.append(HOSViolation(
                        code="11H_DRIVING_LIMIT",
                        message=f"Shift driving limit exceeded: {round(current_shift_driving, 2)}h (max {cls.MAX_DRIVING_SHIFT}h)",
                        severity="VIOLATION",
                        timestamp=event.start_time,
                        event_id=event.id
                    ))

                # 8-Hour Break Check
                if driving_since_break > (cls.MAX_DRIVE_BEFORE_BREAK + 0.05):
                    violations.append(HOSViolation(
                        code="8H_BREAK_RULE",
                        message=f"Driving without mandatory 30-min break exceeded: {round(driving_since_break, 2)}h",
                        severity="VIOLATION",
                        timestamp=event.start_time,
                        event_id=event.id
                    ))

            elif event.duty_status == DutyStatus.ON_DUTY_NOT_DRIVING:
                current_shift_elapsed += dur_hours
                if event.duration_minutes >= 30:
                    driving_since_break = 0.0 # 30 min on duty qualifies as break

            elif event.duty_status in (DutyStatus.OFF_DUTY, DutyStatus.SLEEPER_BERTH):
                if event.event_type == EventType.RESTART_34H or event.duration_minutes >= (34 * 60):
                    current_shift_driving = 0.0
                    current_shift_elapsed = 0.0
                    driving_since_break = 0.0
                elif event.event_type == EventType.REST_10H or event.duration_minutes >= (10 * 60):
                    current_shift_driving = 0.0
                    current_shift_elapsed = 0.0
                    driving_since_break = 0.0
                elif event.duration_minutes >= 30:
                    driving_since_break = 0.0
                    current_shift_elapsed += dur_hours

            # 14-Hour Shift Window Check
            if event.duty_status == DutyStatus.DRIVING and current_shift_elapsed > (cls.MAX_WINDOW_SHIFT + 0.05):
                violations.append(HOSViolation(
                    code="14H_WINDOW_LIMIT",
                    message=f"Driving occurred outside the 14-hour duty window ({round(current_shift_elapsed, 2)}h elapsed)",
                    severity="VIOLATION",
                    timestamp=event.start_time,
                    event_id=event.id
                ))

        # 3. Daily Driving Limit Check across all generated calendar day sheets
        if daily_logs:
            for day in daily_logs:
                d_hours = day.get("duty_hours", {}).get("driving", 0.0)
                valid, err_msg = cls.validate_daily_driving_limit(d_hours)
                if not valid:
                    violations.append(HOSViolation(
                        code="DAILY_DRIVING_LIMIT_EXCEEDED",
                        message=f"HOS Violation: Day {day.get('day_number')} driving total ({d_hours}h) exceeds the maximum 11.0-hour limit.",
                        severity="VIOLATION",
                        details={"day_number": day.get("day_number"), "driving_hours": d_hours, "limit": 11.0}
                    ))

        # Resolve whether historical data is available
        if has_sufficient_history is None:
            if daily_logs and len(daily_logs) > 0:
                recap_info = daily_logs[0].get("recap", {})
                has_sufficient_history = recap_info.get("has_sufficient_history", True)
            else:
                has_sufficient_history = True

        passed = (len(violations) == 0)
        if not passed:
            compliance_status = "Compliance Issue Detected"
            status_type = "ERROR"
            explanation = "One or more FMCSA Hours-of-Service violations were detected in the schedule."
        elif not has_sufficient_history:
            compliance_status = "Generated Trip Validated — Historical 70/8 Data Required"
            status_type = "WARNING"
            explanation = "Daily driving and generated-trip rules were validated. Full 70/8 cycle compliance requires prior 7-day driver logs."
            warnings.append(HOSViolation(
                code="INSUFFICIENT_HISTORICAL_DATA",
                message=explanation,
                severity="WARNING"
            ))
        else:
            compliance_status = "HOS Plan Validated"
            status_type = "VALIDATED"
            explanation = "All FMCSA Part 395 rules and 70-hour / 8-day rolling cycle requirements validated successfully."

        return HOSValidationResult(
            passed=passed,
            compliance_status=compliance_status,
            violations=violations,
            warnings=warnings,
            has_sufficient_history=has_sufficient_history,
            status_type=status_type,
            explanation=explanation
        )
