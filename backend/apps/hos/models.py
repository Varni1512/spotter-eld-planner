"""
Data models and Enums for FMCSA Hours of Service (Part 395).
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple

class DutyStatus(str, Enum):
    OFF_DUTY = "OFF_DUTY"                           # Line 1 on standard paper log
    SLEEPER_BERTH = "SLEEPER_BERTH"                 # Line 2 on standard paper log
    DRIVING = "DRIVING"                             # Line 3 on standard paper log
    ON_DUTY_NOT_DRIVING = "ON_DUTY_NOT_DRIVING"     # Line 4 on standard paper log

    @property
    def line_number(self) -> int:
        return {
            DutyStatus.OFF_DUTY: 1,
            DutyStatus.SLEEPER_BERTH: 2,
            DutyStatus.DRIVING: 3,
            DutyStatus.ON_DUTY_NOT_DRIVING: 4,
        }[self]

    @property
    def display_label(self) -> str:
        return {
            DutyStatus.OFF_DUTY: "Off Duty",
            DutyStatus.SLEEPER_BERTH: "Sleeper Berth",
            DutyStatus.DRIVING: "Driving",
            DutyStatus.ON_DUTY_NOT_DRIVING: "On Duty (Not Driving)",
        }[self]

class EventType(str, Enum):
    PRE_TRIP = "PRE_TRIP"
    DRIVING = "DRIVING"
    BREAK_30M = "BREAK_30M"
    FUELING = "FUELING"
    REST_10H = "REST_10H"
    RESTART_34H = "RESTART_34H"
    PICKUP = "PICKUP"
    DROPOFF = "DROPOFF"
    POST_TRIP = "POST_TRIP"

@dataclass
class TimelineEvent:
    id: str
    event_type: EventType
    duty_status: DutyStatus
    start_time: datetime
    end_time: datetime
    duration_minutes: float
    duration_hours: float
    start_mile: float
    end_mile: float
    distance_miles: float
    location_name: str
    coordinates: Tuple[float, float]
    remarks: str
    leg_id: int
    shift_driving_at_end: float = 0.0
    shift_elapsed_at_end: float = 0.0
    cycle_used_at_end: float = 0.0

@dataclass
class TripStop:
    id: str
    stop_type: str
    name: str
    location_name: str
    coordinates: Tuple[float, float]
    arrival_time: datetime
    departure_time: datetime
    duration_minutes: int
    duty_status: DutyStatus
    mile_marker: float
    reason: str
    leg_id: int = 1

@dataclass
class DriverClocks:
    """Tracks running FMCSA Part 395 compliance clocks."""
    shift_driving_hours: float = 0.0      # Max 11.0 hours
    shift_elapsed_hours: float = 0.0      # Max 14.0 hours from start of duty
    driving_since_break: float = 0.0      # Max 8.0 hours before 30-min break
    cycle_on_duty_hours: float = 0.0      # Max 70.0 hours in 8 days
    miles_since_last_fuel: float = 0.0    # Max 1,000 miles before fueling

    def reset_shift(self):
        """Called after 10+ consecutive hours off-duty/sleeper."""
        self.shift_driving_hours = 0.0
        self.shift_elapsed_hours = 0.0
        self.driving_since_break = 0.0

    def reset_cycle(self):
        """Called after 34+ consecutive hours off-duty restart."""
        self.reset_shift()
        self.cycle_on_duty_hours = 0.0
