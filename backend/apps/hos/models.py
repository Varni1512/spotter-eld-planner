"""
Data models, Enums, and Metrics for FMCSA Hours of Service (Part 395).
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any

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
class HOSMetrics:
    """Transparent snapshot of FMCSA limits and used clocks at any decision point."""
    driving_used: float = 0.0
    driving_limit: float = 11.0
    window_elapsed: float = 0.0
    window_limit: float = 14.0
    break_driving_elapsed: float = 0.0
    break_required_after: float = 8.0
    cycle_used: float = 0.0
    cycle_limit: float = 70.0
    miles_since_fuel: float = 0.0
    fuel_limit: float = 1000.0

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
    timezone_id: str = "America/Chicago"
    local_start_time: str = ""
    local_end_time: str = ""
    shift_driving_at_end: float = 0.0
    shift_elapsed_at_end: float = 0.0
    cycle_used_at_end: float = 0.0
    metrics: Optional[HOSMetrics] = None

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
    timezone_id: str = "America/Chicago"
    arrival_local_display: str = ""
    departure_local_display: str = ""
    hos_metrics: Optional[HOSMetrics] = None

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

@dataclass
class HOSViolation:
    code: str
    message: str
    severity: str  # "VIOLATION" or "WARNING"
    timestamp: Optional[datetime] = None
    event_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

@dataclass
class HOSValidationResult:
    passed: bool
    compliance_status: str # "HOS Plan Validated" or "Compliance Issue Detected"
    violations: List[HOSViolation] = field(default_factory=list)
    warnings: List[HOSViolation] = field(default_factory=list)

class HOSConflictError(Exception):
    """Raised when an illegal schedule or activity is detected in the HOS plan."""
    def __init__(self, message: str, violation: Optional[HOSViolation] = None):
        super().__init__(message)
        self.violation = violation
