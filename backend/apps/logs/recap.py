"""
Isolated 70-Hour / 8-Day Rolling Recap Engine for FMCSA Property-Carrying Commercial Drivers.
Computes Line A (On-duty today), Line B (Total last 7 days + today), and Line C (Available tomorrow).
Strictly exposes:
- has_sufficient_history: bool
- historical_hours_used: float
- generated_trip_hours: float
- total_recap_hours: float
- available_cycle_hours: float
- history_label: str
- explanation: str
"""

from typing import Dict, Any, List, Optional
from apps.hos.models import DutyStatus

CYCLE_LIMIT_HOURS = 70.0
ROLLING_WINDOW_DAYS = 8 # 70-hour / 8-day rule

def calculate_on_duty_hours_for_day(day_segments: List[Dict[str, Any]]) -> float:
    """
    Calculates total on-duty hours (Driving + On Duty Not Driving) for a 24-hour day sheet.
    """
    on_duty_total = 0.0
    for seg in day_segments:
        status = seg.get("status")
        if status in (DutyStatus.DRIVING, DutyStatus.ON_DUTY_NOT_DRIVING, "DRIVING", "ON_DUTY_NOT_DRIVING"):
            on_duty_total += seg.get("duration_hours", 0.0)
    return round(on_duty_total, 2)

def calculate_available_hours(cycle_limit: float, rolling_on_duty: float) -> float:
    """
    Available on-duty hours for tomorrow (Line C = 70.0 - Line B).
    Cannot fall below 0.0.
    """
    return max(0.0, round(cycle_limit - rolling_on_duty, 2))

def calculate_rolling_cycle_hours(
    daily_history: List[Dict[str, Any]],
    current_day_index: int,
    initial_cycle_used: float = 0.0,
    has_historical_records: bool = True
) -> Dict[str, Any]:
    """
    Calculates the 70-hour / 8-day rolling recap for the specified day.
    """
    if current_day_index < 0 or current_day_index >= len(daily_history):
        return {
            "line_a_on_duty_today": 0.0,
            "line_b_total_last_7_days": 0.0,
            "line_c_available_tomorrow": CYCLE_LIMIT_HOURS,
            "has_sufficient_history": False,
            "historical_hours_used": 0.0,
            "generated_trip_hours": 0.0,
            "total_recap_hours": 0.0,
            "available_cycle_hours": CYCLE_LIMIT_HOURS,
            "history_status": "INSUFFICIENT_HISTORY",
            "history_label": "Insufficient historical data",
            "message": "Insufficient historical data",
            "explanation": "No log sheet exists for the requested day index.",
            "restart_applied": False
        }

    current_sheet = daily_history[current_day_index]
    on_duty_today = current_sheet.get("duty_hours", {}).get("on_duty_today")
    if on_duty_today is None:
        on_duty_today = calculate_on_duty_hours_for_day(current_sheet.get("segments", []))

    # Check if a 34-hour restart was completed on or prior to this day
    restart_day_index: Optional[int] = None
    for d_idx in range(current_day_index, -1, -1):
        sheet = daily_history[d_idx]
        segments = sheet.get("segments", [])
        had_restart = any(
            ("34-Hour Restart" in seg.get("remarks", "") or "34hr Restart" in seg.get("remarks", ""))
            for seg in segments
        )
        if had_restart:
            restart_day_index = d_idx
            break

    # Sum generated trip hours
    start_accumulation_idx = restart_day_index if restart_day_index is not None else 0
    generated_trip_hours = 0.0
    for d_idx in range(start_accumulation_idx, current_day_index + 1):
        sheet = daily_history[d_idx]
        s_on_duty = calculate_on_duty_hours_for_day(sheet.get("segments", []))
        generated_trip_hours += s_on_duty
    generated_trip_hours = round(generated_trip_hours, 2)

    if restart_day_index is not None:
        # Restart reset historical hours to 0
        historical_hours_used = 0.0
        total_recap_hours = generated_trip_hours
        avail = calculate_available_hours(CYCLE_LIMIT_HOURS, total_recap_hours)

        return {
            "line_a_on_duty_today": on_duty_today,
            "line_b_total_last_7_days": total_recap_hours,
            "line_c_available_tomorrow": avail,
            "has_sufficient_history": True,
            "historical_hours_used": 0.0,
            "generated_trip_hours": generated_trip_hours,
            "total_recap_hours": total_recap_hours,
            "available_cycle_hours": avail,
            "history_status": "RESTART_RESET",
            "history_label": f"Cycle reset by 34h restart on Day {restart_day_index + 1}",
            "restart_applied": True,
            "explanation": (
                f"34-hour restart reset cycle on Day {restart_day_index + 1}. "
                f"Cycle accumulation started fresh: {total_recap_hours}h accumulated towards 70h limit."
            )
        }

    # No restart: combine historical baseline + generated trip hours
    historical_hours_used = round(float(initial_cycle_used), 2)
    has_history = (historical_hours_used > 0.0 and has_historical_records)

    total_recap_hours = round(historical_hours_used + generated_trip_hours, 2)
    avail = calculate_available_hours(CYCLE_LIMIT_HOURS, total_recap_hours)

    if has_history:
        history_status = "WITH_HISTORICAL_BASELINE"
        history_label = f"Historical baseline ({historical_hours_used}h) + Generated trip ({generated_trip_hours}h)"
        explanation = (
            f"Total on-duty hours accumulated: {historical_hours_used}h prior cycle used + "
            f"{generated_trip_hours}h generated trip on-duty hours = {total_recap_hours}h used ({avail}h available tomorrow)."
        )
    else:
        history_status = "GENERATED_TRIP_ONLY"
        history_label = "Generated trip history only (No prior 7-day logs entered)"
        explanation = (
            f"Generated trip history only: {generated_trip_hours}h accumulated during this trip. "
            f"Prior 7-day driver logs were not provided (insufficient historical data for full 7/8-day recap)."
        )

    return {
        "line_a_on_duty_today": on_duty_today,
        "line_b_total_last_7_days": total_recap_hours,
        "line_c_available_tomorrow": avail,
        "has_sufficient_history": has_history,
        "historical_hours_used": historical_hours_used,
        "generated_trip_hours": generated_trip_hours,
        "total_recap_hours": total_recap_hours,
        "available_cycle_hours": avail,
        "history_status": history_status,
        "history_label": history_label,
        "message": history_label,
        "restart_applied": False,
        "explanation": explanation
    }

def validate_rolling_recap(recap_data: Dict[str, Any]) -> List[str]:
    """
    Validates recap consistency:
    1. Line A <= Line B
    2. Line B + Line C == 70.0 (unless Line B > 70.0 where Line C == 0.0)
    """
    errors = []
    line_a = recap_data.get("line_a_on_duty_today", 0.0)
    line_b = recap_data.get("line_b_total_last_7_days", 0.0)
    line_c = recap_data.get("line_c_available_tomorrow", 0.0)

    if line_a > line_b + 0.01:
        errors.append(f"On-duty today ({line_a}h) cannot exceed cumulative cycle ({line_b}h).")

    expected_avail = max(0.0, round(CYCLE_LIMIT_HOURS - line_b, 2))
    if abs(line_c - expected_avail) > 0.05:
        errors.append(f"Available tomorrow mismatch: expected {expected_avail}h, got {line_c}h.")

    return errors
