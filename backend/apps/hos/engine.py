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
"""

import math
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Tuple

from apps.routing.services import RoutingService
from apps.geocoding.services import GeocodingService
from .models import DutyStatus, EventType, TimelineEvent, TripStop, DriverClocks

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

    def __init__(self, start_time: datetime, current_cycle_used: float = 0.0):
        self.start_time = start_time
        self.current_time = start_time
        self.clocks = DriverClocks(cycle_on_duty_hours=min(70.0, max(0.0, current_cycle_used)))
        self.timeline: List[TimelineEvent] = []
        self.stops: List[TripStop] = []
        self.event_counter = 1
        self.stop_counter = 1
        self.cumulative_trip_miles = 0.0

    def simulate(
        self,
        locations: Dict[str, Any],
        leg1_route: Dict[str, Any],
        leg2_route: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Simulate full trip across Leg 1 (Current -> Pickup) and Leg 2 (Pickup -> Dropoff).
        """
        # 1. Pre-trip vehicle inspection at origin
        curr_loc = locations["current"]
        self._add_event(
            event_type=EventType.PRE_TRIP,
            duty_status=DutyStatus.ON_DUTY_NOT_DRIVING,
            duration_minutes=self.PRE_TRIP_MINUTES,
            distance_miles=0.0,
            location_name=curr_loc["display_name"],
            coordinates=(curr_loc["coordinates"][0], curr_loc["coordinates"][1]),
            remarks="Pre-Trip Vehicle Inspection",
            leg_id=1
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
            leg_id=1
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
        pickup_arrival = self.current_time
        self._add_event(
            event_type=EventType.PICKUP,
            duty_status=DutyStatus.ON_DUTY_NOT_DRIVING,
            duration_minutes=self.PICKUP_DURATION_MINUTES,
            distance_miles=0.0,
            location_name=pickup_loc["display_name"],
            coordinates=(pickup_loc["coordinates"][0], pickup_loc["coordinates"][1]),
            remarks="Shipper Loading (1 hr On-Duty)",
            leg_id=1
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
            leg_id=1
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
        dropoff_arrival = self.current_time
        self._add_event(
            event_type=EventType.DROPOFF,
            duty_status=DutyStatus.ON_DUTY_NOT_DRIVING,
            duration_minutes=self.DROPOFF_DURATION_MINUTES,
            distance_miles=0.0,
            location_name=dropoff_loc["display_name"],
            coordinates=(dropoff_loc["coordinates"][0], dropoff_loc["coordinates"][1]),
            remarks="Consignee Unloading (1 hr On-Duty)",
            leg_id=2
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
            leg_id=2
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
            leg_id=2
        )

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
        }

    def _simulate_driving_leg(
        self,
        leg_id: int,
        route: Dict[str, Any],
        origin_name: str,
        dest_name: str
    ):
        """
        Simulate driving along a single route leg with continuous FMCSA compliance checks.
        """
        leg_distance = route.get("distance_miles", 0.0)
        leg_duration_hours = route.get("duration_hours", 0.0)
        coordinates = route.get("coordinates", [])
        cumulative_miles = route.get("cumulative_miles", [])

        if leg_distance <= 0.0:
            return

        # Average commercial driving speed along this leg
        speed_mph = leg_distance / leg_duration_hours if leg_duration_hours > 0 else 55.0
        speed_mph = max(40.0, min(65.0, speed_mph))

        leg_miles_completed = 0.0

        while leg_miles_completed < (leg_distance - 0.1):
            miles_remaining_in_leg = leg_distance - leg_miles_completed

            # Check remaining allowances before any FMCSA threshold:
            # 1. Remaining driving before 8h cumulative limit
            drive_avail_before_break = max(0.0, self.MAX_DRIVE_BEFORE_BREAK - self.clocks.driving_since_break)

            # 2. Remaining driving before 11h daily driving limit
            drive_avail_before_11h = max(0.0, self.MAX_DRIVING_SHIFT - self.clocks.shift_driving_hours)

            # 3. Remaining driving before 14h elapsed shift window limit
            drive_avail_before_14h = max(0.0, self.MAX_WINDOW_SHIFT - self.clocks.shift_elapsed_hours)

            # 4. Remaining driving before 70h cycle limit
            drive_avail_before_cycle = max(0.0, self.CYCLE_LIMIT_HOURS - self.clocks.cycle_on_duty_hours)

            # 5. Remaining distance before fueling
            miles_avail_before_fuel = max(0.0, self.FUEL_TRIGGER_MILES - self.clocks.miles_since_last_fuel)
            drive_avail_before_fuel = miles_avail_before_fuel / speed_mph

            # What is the maximum driving time we can safely do before an event is triggered?
            driving_time_allowed = min(
                miles_remaining_in_leg / speed_mph,
                drive_avail_before_break,
                drive_avail_before_11h,
                drive_avail_before_14h,
                drive_avail_before_cycle,
                drive_avail_before_fuel
            )

            # If driving_time_allowed is zero or tiny (< 5 minutes), handle the triggering event immediately!
            if driving_time_allowed < (5.0 / 60.0):
                self._handle_trigger_event(coordinates, cumulative_miles, leg_miles_completed, leg_id)
                continue

            # Drive this chunk!
            chunk_miles = min(miles_remaining_in_leg, driving_time_allowed * speed_mph)
            chunk_duration_minutes = round((chunk_miles / speed_mph) * 60.0)

            # Interpolate coordinates along route
            interp_lat, interp_lon = RoutingService.interpolate_coordinate_at_mile(
                coordinates, cumulative_miles, leg_miles_completed + chunk_miles
            )

            self._add_event(
                event_type=EventType.DRIVING,
                duty_status=DutyStatus.DRIVING,
                duration_minutes=chunk_duration_minutes,
                distance_miles=chunk_miles,
                location_name=f"En Route ({round(leg_miles_completed + chunk_miles)} mi on Leg {leg_id})",
                coordinates=(interp_lat, interp_lon),
                remarks=f"Driving ({round(chunk_miles)} mi)",
                leg_id=leg_id
            )

            leg_miles_completed += chunk_miles

            # If we haven't reached destination, handle whatever limit was reached
            if leg_miles_completed < (leg_distance - 0.1):
                self._handle_trigger_event(coordinates, cumulative_miles, leg_miles_completed, leg_id)

    def _handle_trigger_event(
        self,
        coordinates: List[List[float]],
        cumulative_miles: List[float],
        leg_miles_completed: float,
        leg_id: int
    ):
        """
        Evaluate which FMCSA limit has been met and schedule the required stop / rest.
        Priority:
        1. 70h cycle limit -> 34h restart
        2. 11h driving or 14h window limit -> 10h sleeper rest
        3. 8h driving without break -> 30m break
        4. Fuel limit (≥ 950 miles) -> 30m fuel stop
        """
        interp_lat, interp_lon = RoutingService.interpolate_coordinate_at_mile(
            coordinates, cumulative_miles, leg_miles_completed
        )
        location_label = GeocodingService.reverse_geocode(interp_lat, interp_lon)

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
                leg_id=leg_id
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
                leg_id=leg_id
            )
            return

        # 2. 11h Driving Limit OR 14h Window Limit -> 10-Hour Qualifying Rest
        if (self.clocks.shift_driving_hours >= (self.MAX_DRIVING_SHIFT - 0.05) or
            self.clocks.shift_elapsed_hours >= (self.MAX_WINDOW_SHIFT - 0.05)):
            arrival = self.current_time
            reason = "11-Hour Driving Limit Reached" if self.clocks.shift_driving_hours >= (self.MAX_DRIVING_SHIFT - 0.05) else "14-Hour Duty Window Reached"
            self._add_event(
                event_type=EventType.REST_10H,
                duty_status=DutyStatus.SLEEPER_BERTH,
                duration_minutes=int(self.QUALIFYING_REST_HOURS * 60),
                distance_miles=0.0,
                location_name=location_label,
                coordinates=(interp_lat, interp_lon),
                remarks=f"10-Hour Qualifying Rest ({reason})",
                leg_id=leg_id
            )
            self._add_stop(
                stop_type="sleeper_rest",
                name="10-Hour Overnight Rest",
                location_name=location_label,
                coordinates=(interp_lat, interp_lon),
                arrival_time=arrival,
                departure_time=self.current_time,
                duration_minutes=int(self.QUALIFYING_REST_HOURS * 60),
                duty_status=DutyStatus.SLEEPER_BERTH,
                mile_marker=self.cumulative_trip_miles,
                reason=f"{reason} - 10 Consecutive Hours Sleeper Berth",
                leg_id=leg_id
            )
            return

        # 3. Fuel Stop Required (≥ 950 miles since last fuel)
        if self.clocks.miles_since_last_fuel >= self.FUEL_TRIGGER_MILES:
            arrival = self.current_time
            self._add_event(
                event_type=EventType.FUELING,
                duty_status=DutyStatus.ON_DUTY_NOT_DRIVING,
                duration_minutes=self.FUEL_DURATION_MINUTES,
                distance_miles=0.0,
                location_name=location_label,
                coordinates=(interp_lat, interp_lon),
                remarks=f"Fueling ({round(self.clocks.miles_since_last_fuel)} mi since last fuel)",
                leg_id=leg_id
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
                leg_id=leg_id
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
                leg_id=leg_id
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
                leg_id=leg_id
            )
            return

    def _add_event(
        self,
        event_type: EventType,
        duty_status: DutyStatus,
        duration_minutes: float,
        distance_miles: float,
        location_name: str,
        coordinates: Tuple[float, float],
        remarks: str,
        leg_id: int
    ):
        """Append an event and advance driver compliance clocks."""
        duration_hours = duration_minutes / 60.0
        start_t = self.current_time
        end_t = start_t + timedelta(minutes=duration_minutes)
        start_m = self.cumulative_trip_miles
        end_m = start_m + distance_miles

        # Advance clocks based on duty status:
        if duty_status == DutyStatus.DRIVING:
            self.clocks.shift_driving_hours += duration_hours
            self.clocks.shift_elapsed_hours += duration_hours
            self.clocks.driving_since_break += duration_hours
            self.clocks.cycle_on_duty_hours += duration_hours
            self.clocks.miles_since_last_fuel += distance_miles
            self.cumulative_trip_miles += distance_miles

        elif duty_status == DutyStatus.ON_DUTY_NOT_DRIVING:
            self.clocks.shift_elapsed_hours += duration_hours
            self.clocks.cycle_on_duty_hours += duration_hours
            if duration_minutes >= 30:
                self.clocks.driving_since_break = 0.0 # 30 min on-duty qualifies as break under 2020 rules
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
            shift_driving_at_end=round(self.clocks.shift_driving_hours, 2),
            shift_elapsed_at_end=round(self.clocks.shift_elapsed_hours, 2),
            cycle_used_at_end=round(self.clocks.cycle_on_duty_hours, 2)
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
        leg_id: int
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
            leg_id=leg_id
        )
        self.stops.append(stop)
        self.stop_counter += 1
