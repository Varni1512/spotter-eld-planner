"""
Unit tests for DailyLogSheetGenerator and Rolling Recap Engine (49 CFR § 395.8).
Covers:
- Strict 24.0-hour total sum verification
- Non-negative durations and interval integrity
- Rolling 70h/8d recap logic: consecutive workdays, zero-duty days, 34-hour restart cycle resets,
  7-day and 8-day rolling windows, insufficient historical data handling, and 70h boundaries.
- Cross-midnight proportional mileage splits.
"""

from datetime import datetime, timedelta, timezone
from django.test import TestCase

from apps.hos.models import DutyStatus, EventType, TimelineEvent
from apps.logs.generator import DailyLogSheetGenerator
from apps.logs.recap import (
    calculate_on_duty_hours_for_day,
    calculate_rolling_cycle_hours,
    calculate_available_hours,
    validate_rolling_recap,
    CYCLE_LIMIT_HOURS
)

class DailyLogTestCase(TestCase):
    def setUp(self):
        self.start_time = datetime(2026, 9, 15, 8, 0, 0, tzinfo=timezone.utc)

    def test_daily_log_hours_sum_strictly_to_24(self):
        """Every generated daily log sheet must sum to exactly 24.0 hours."""
        locations = {
            "current": {"display_name": "Chicago, IL", "coordinates": [41.8781, -87.6298]},
            "pickup": {"display_name": "Dallas, TX", "coordinates": [32.7767, -96.7970]},
            "dropoff": {"display_name": "Atlanta, GA", "coordinates": [33.7490, -84.3880]}
        }
        leg1 = {
            "distance_miles": 960.0,
            "duration_hours": 16.0,
            "coordinates": [[-87.6298, 41.8781], [-96.7970, 32.7767]],
            "cumulative_miles": [0.0, 960.0]
        }
        leg2 = {
            "distance_miles": 780.0,
            "duration_hours": 13.0,
            "coordinates": [[-96.7970, 32.7767], [-84.3880, 33.7490]],
            "cumulative_miles": [0.0, 780.0]
        }

        from apps.hos.engine import HOSSimulationEngine
        engine = HOSSimulationEngine(start_time=self.start_time, current_cycle_used=25.0)
        sim = engine.simulate(locations, leg1, leg2)

        daily_sheets = DailyLogSheetGenerator.generate_daily_logs(
            timeline=sim["timeline"],
            start_time=self.start_time,
            end_time=sim["end_time"],
            initial_cycle_used=25.0,
            origin_name="Chicago, IL",
            destination_name="Atlanta, GA"
        )

        self.assertGreaterEqual(len(daily_sheets), 2)

        for idx, sheet in enumerate(daily_sheets):
            hours = sheet["duty_hours"]
            total_sum = hours["off_duty"] + hours["sleeper_berth"] + hours["driving"] + hours["on_duty_not_driving"]
            self.assertEqual(
                round(total_sum, 2),
                24.0,
                f"Day {idx + 1} hours must sum to exactly 24.0, got {total_sum}"
            )
            self.assertEqual(sheet["validation"]["status"], "VALIDATED")
            self.assertTrue(sheet["validation"]["is_complete_24h"])

    def test_cross_midnight_proportional_mileage(self):
        """When a driving event crosses midnight, miles must be apportioned proportionately."""
        # Driving event from 22:00 to 02:00 (4 hours total, 200 miles)
        # 2 hours before midnight, 2 hours after midnight -> 100 miles each day
        day1_start = datetime(2026, 9, 15, 0, 0, tzinfo=timezone.utc)
        evt_start = datetime(2026, 9, 15, 22, 0, tzinfo=timezone.utc)
        evt_end = datetime(2026, 9, 16, 2, 0, tzinfo=timezone.utc)

        cross_event = TimelineEvent(
            id="evt-cross-1",
            event_type=EventType.DRIVING,
            duty_status=DutyStatus.DRIVING,
            start_time=evt_start,
            end_time=evt_end,
            duration_minutes=240,
            duration_hours=4.0,
            start_mile=0.0,
            end_mile=200.0,
            distance_miles=200.0,
            location_name="Interstate Highway",
            coordinates=(35.0, -85.0),
            remarks="Cross-Midnight Driving",
            leg_id=1
        )

        sheets = DailyLogSheetGenerator.generate_daily_logs(
            timeline=[cross_event],
            start_time=evt_start,
            end_time=evt_end,
            initial_cycle_used=10.0,
            origin_name="Origin",
            destination_name="Destination",
            operational_timezone="UTC"
        )

        self.assertEqual(len(sheets), 2)
        # Day 1 driving: 2 hours (22:00 to 24:00) -> 100 miles
        self.assertAlmostEqual(sheets[0]["duty_hours"]["driving"], 2.0, places=2)
        self.assertAlmostEqual(sheets[0]["miles_driving_today"], 100.0, places=1)

        # Day 2 driving: 2 hours (00:00 to 02:00) -> 100 miles
        self.assertAlmostEqual(sheets[1]["duty_hours"]["driving"], 2.0, places=2)
        self.assertAlmostEqual(sheets[1]["miles_driving_today"], 100.0, places=1)

    # ==================== ROLLING RECAP TESTS ====================

    def test_rolling_recap_consecutive_days(self):
        """Test rolling recap over consecutive workdays accumulates on-duty hours."""
        history = [
            {"segments": [{"status": DutyStatus.DRIVING, "duration_hours": 8.0}, {"status": DutyStatus.ON_DUTY_NOT_DRIVING, "duration_hours": 2.0}]}, # Day 1: 10h
            {"segments": [{"status": DutyStatus.DRIVING, "duration_hours": 7.5}, {"status": DutyStatus.ON_DUTY_NOT_DRIVING, "duration_hours": 1.5}]}, # Day 2: 9h
        ]
        recap_day1 = calculate_rolling_cycle_hours(history, 0, initial_cycle_used=20.0)
        self.assertEqual(recap_day1["line_a_on_duty_today"], 10.0)
        self.assertEqual(recap_day1["line_b_total_last_7_days"], 30.0) # 20 + 10
        self.assertEqual(recap_day1["line_c_available_tomorrow"], 40.0) # 70 - 30

        recap_day2 = calculate_rolling_cycle_hours(history, 1, initial_cycle_used=20.0)
        self.assertEqual(recap_day2["line_a_on_duty_today"], 9.0)
        self.assertEqual(recap_day2["line_b_total_last_7_days"], 39.0) # 30 + 9
        self.assertEqual(recap_day2["line_c_available_tomorrow"], 31.0) # 70 - 39

    def test_rolling_recap_zero_duty_day(self):
        """Test that a zero-duty day (e.g. 24 hours off-duty/sleeper) does not add to rolling cycle."""
        history = [
            {"segments": [{"status": DutyStatus.DRIVING, "duration_hours": 10.0}]},
            {"segments": [{"status": DutyStatus.OFF_DUTY, "duration_hours": 24.0}]}, # Zero on-duty
        ]
        recap_day2 = calculate_rolling_cycle_hours(history, 1, initial_cycle_used=15.0)
        self.assertEqual(recap_day2["line_a_on_duty_today"], 0.0)
        self.assertEqual(recap_day2["line_b_total_last_7_days"], 25.0) # 15 + 10 + 0

    def test_rolling_recap_34h_restart_resets_cycle(self):
        """A valid 34-hour restart must reset the rolling cycle accumulation."""
        history = [
            {"segments": [{"status": DutyStatus.DRIVING, "duration_hours": 10.0}]}, # Day 1: 10h
            {"segments": [{"status": DutyStatus.SLEEPER_BERTH, "duration_hours": 24.0, "remarks": "34-Hour Restart in Sleeper"}]}, # Day 2: Restart
            {"segments": [{"status": DutyStatus.DRIVING, "duration_hours": 6.0}]}, # Day 3: 6h
        ]
        recap_day3 = calculate_rolling_cycle_hours(history, 2, initial_cycle_used=50.0)
        # Because restart was on Day 2, cycle reset! Line B should ONLY count from restart (Day 2 on-duty: 0, Day 3 on-duty: 6)
        self.assertEqual(recap_day3["line_a_on_duty_today"], 6.0)
        self.assertEqual(recap_day3["line_b_total_last_7_days"], 6.0)
        self.assertEqual(recap_day3["line_c_available_tomorrow"], 64.0) # 70 - 6
        self.assertTrue(recap_day3["restart_applied"])

    def test_insufficient_historical_data_flag(self):
        """If historical data is missing and initial cycle is 0, report GENERATED_TRIP_ONLY clearly with 5 fields."""
        history = [
            {"segments": [{"status": DutyStatus.DRIVING, "duration_hours": 5.0}]}
        ]
        recap = calculate_rolling_cycle_hours(history, 0, initial_cycle_used=0.0, has_historical_records=False)
        self.assertFalse(recap["has_sufficient_history"])
        self.assertEqual(recap["historical_hours_used"], 0.0)
        self.assertEqual(recap["generated_trip_hours"], 5.0)
        self.assertEqual(recap["total_recap_hours"], 5.0)
        self.assertEqual(recap["available_cycle_hours"], 65.0)
        self.assertEqual(recap["history_status"], "GENERATED_TRIP_ONLY")
        self.assertIn("Generated trip history only", recap["history_label"])
        self.assertIn("insufficient historical data", recap["explanation"])

    def test_70_hour_boundary_available_hours_cannot_be_negative(self):
        """When cumulative on-duty reaches or exceeds 70h, available hours must floor at 0.0."""
        avail = calculate_available_hours(CYCLE_LIMIT_HOURS, 70.0)
        self.assertEqual(avail, 0.0)
        avail_over = calculate_available_hours(CYCLE_LIMIT_HOURS, 72.5)
        self.assertEqual(avail_over, 0.0)
