"""
Unit tests for FMCSA Hours of Service Engine (49 CFR Part 395).
Covers:
- 11-hour driving limit
- 14-hour on-duty window
- 30-minute break after 8 cumulative hours
- 34-hour restart validation (driving during restart, on-duty during restart, activity at restart end, activity after restart end)
- Transparent decision metrics
"""

from datetime import datetime, timedelta, timezone
from django.test import TestCase
from apps.hos.engine import HOSSimulationEngine
from apps.hos.models import (
    DutyStatus,
    EventType,
    TimelineEvent,
    HOSMetrics
)

class HOSTestCase(TestCase):
    def setUp(self):
        self.start_time = datetime(2026, 9, 15, 8, 0, 0, tzinfo=timezone.utc)
        self.sample_locations = {
            "current": {"display_name": "Chicago, IL", "coordinates": [41.8781, -87.6298]},
            "pickup": {"display_name": "Dallas, TX", "coordinates": [32.7767, -96.7970]},
            "dropoff": {"display_name": "Atlanta, GA", "coordinates": [33.7490, -84.3880]}
        }

    def test_short_trip_compliance(self):
        """Test a short trip under 400 miles completes within 1 day without exceeding 11h driving."""
        leg1 = {
            "distance_miles": 150.0,
            "duration_hours": 2.7,
            "coordinates": [[-87.6298, 41.8781], [-86.1581, 39.7684]],
            "cumulative_miles": [0.0, 150.0]
        }
        leg2 = {
            "distance_miles": 180.0,
            "duration_hours": 3.2,
            "coordinates": [[-86.1581, 39.7684], [-82.9988, 39.9612]],
            "cumulative_miles": [0.0, 180.0]
        }

        engine = HOSSimulationEngine(start_time=self.start_time, current_cycle_used=10.0)
        res = engine.simulate(self.sample_locations, leg1, leg2)

        self.assertAlmostEqual(res["total_distance_miles"], 330.0, delta=1.0)
        self.assertLess(res["total_driving_hours"], 11.0)
        stop_types = [s.stop_type for s in res["stops"]]
        self.assertIn("pickup", stop_types)
        self.assertIn("dropoff", stop_types)
        self.assertTrue(res["validation"].passed)
        self.assertEqual(res["validation"].compliance_status, "HOS Plan Validated")

    def test_30_min_break_after_8_hours(self):
        """Test that driving over 8 hours triggers a 30-minute break."""
        leg1 = {
            "distance_miles": 550.0,
            "duration_hours": 9.5,
            "coordinates": [[-87.6298, 41.8781], [-96.7970, 32.7767]],
            "cumulative_miles": [0.0, 550.0]
        }
        leg2 = {
            "distance_miles": 100.0,
            "duration_hours": 1.8,
            "coordinates": [[-96.7970, 32.7767], [-95.3698, 29.7604]],
            "cumulative_miles": [0.0, 100.0]
        }

        engine = HOSSimulationEngine(start_time=self.start_time, current_cycle_used=5.0)
        res = engine.simulate(self.sample_locations, leg1, leg2)

        event_types = [e.event_type for e in res["timeline"]]
        self.assertIn(EventType.BREAK_30M, event_types, "30-min break must be scheduled after 8h driving")

    def test_10_hour_rest_at_11_hours_driving(self):
        """Test that reaching 11 hours driving forces a 10-hour sleeper rest."""
        leg1 = {
            "distance_miles": 750.0,
            "duration_hours": 13.0,
            "coordinates": [[-87.6298, 41.8781], [-96.7970, 32.7767]],
            "cumulative_miles": [0.0, 750.0]
        }
        leg2 = {
            "distance_miles": 200.0,
            "duration_hours": 3.5,
            "coordinates": [[-96.7970, 32.7767], [-84.3880, 33.7490]],
            "cumulative_miles": [0.0, 200.0]
        }

        engine = HOSSimulationEngine(start_time=self.start_time, current_cycle_used=15.0)
        res = engine.simulate(self.sample_locations, leg1, leg2)

        event_types = [e.event_type for e in res["timeline"]]
        self.assertIn(EventType.REST_10H, event_types, "10-hour rest must trigger after 11 hours driving")

    def test_fueling_at_least_once_every_1000_miles(self):
        """Test that fueling stops occur within every 1,000 miles."""
        leg1 = {
            "distance_miles": 1200.0,
            "duration_hours": 20.0,
            "coordinates": [[-87.6298, 41.8781], [-104.9903, 39.7392]],
            "cumulative_miles": [0.0, 1200.0]
        }
        leg2 = {
            "distance_miles": 300.0,
            "duration_hours": 5.0,
            "coordinates": [[-104.9903, 39.7392], [-112.0740, 33.4484]],
            "cumulative_miles": [0.0, 300.0]
        }

        engine = HOSSimulationEngine(start_time=self.start_time, current_cycle_used=10.0)
        res = engine.simulate(self.sample_locations, leg1, leg2)

        fuel_stops = [s for s in res["stops"] if s.stop_type == "fuel"]
        self.assertGreaterEqual(len(fuel_stops), 1, "Must schedule at least 1 fueling stop for > 1,000 miles")
        for f in fuel_stops:
            self.assertLessEqual(f.mile_marker, 1000.0, "Fueling must trigger before reaching 1,000 miles")

    # ==================== 34-HOUR RESTART SPECIFIC TESTS ====================

    def test_driving_during_restart_is_detected_as_violation(self):
        """
        Verify that if driving is scheduled during an active 34-hour restart interval,
        validate_restart_interval detects and reports it as an HOS conflict.
        """
        restart_start = datetime(2026, 9, 19, 23, 35, tzinfo=timezone.utc)
        restart_end = restart_start + timedelta(hours=34) # Sept 21, 09:35

        # Create an illegal timeline with driving scheduled inside the restart
        conflicting_driving = TimelineEvent(
            id="evt-bad-1",
            event_type=EventType.DRIVING,
            duty_status=DutyStatus.DRIVING,
            start_time=datetime(2026, 9, 20, 14, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 9, 20, 16, 0, tzinfo=timezone.utc),
            duration_minutes=120,
            duration_hours=2.0,
            start_mile=500.0,
            end_mile=600.0,
            distance_miles=100.0,
            location_name="Mid-Restart City",
            coordinates=(35.0, -90.0),
            remarks="Illegal Driving During 34h Restart",
            leg_id=2
        )

        violations = HOSSimulationEngine.validate_restart_interval(
            [conflicting_driving], restart_start, restart_end
        )
        self.assertEqual(len(violations), 1)
        self.assertIn("Driving scheduled before the 34-hour restart was completed", violations[0].message)

    def test_on_duty_during_restart_is_detected_as_violation(self):
        """
        Verify that On-Duty Not Driving activity during a 34h restart is rejected.
        """
        restart_start = datetime(2026, 9, 19, 23, 35, tzinfo=timezone.utc)
        restart_end = restart_start + timedelta(hours=34)

        conflicting_on_duty = TimelineEvent(
            id="evt-bad-2",
            event_type=EventType.FUELING,
            duty_status=DutyStatus.ON_DUTY_NOT_DRIVING,
            start_time=datetime(2026, 9, 21, 8, 0, tzinfo=timezone.utc), # Before 09:35
            end_time=datetime(2026, 9, 21, 8, 30, tzinfo=timezone.utc),
            duration_minutes=30,
            duration_hours=0.5,
            start_mile=500.0,
            end_mile=500.0,
            distance_miles=0.0,
            location_name="Fuel Stop",
            coordinates=(35.0, -90.0),
            remarks="Fueling during restart",
            leg_id=2
        )

        violations = HOSSimulationEngine.validate_restart_interval(
            [conflicting_on_duty], restart_start, restart_end
        )
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].code, "RESTART_VIOLATION")

    def test_activity_exactly_at_restart_end_is_allowed(self):
        """
        Verify that driving starting EXACTLY at restart completion (e.g. 09:35) is 100% valid.
        """
        restart_start = datetime(2026, 9, 19, 23, 35, tzinfo=timezone.utc)
        restart_end = restart_start + timedelta(hours=34) # Sept 21, 09:35:00

        valid_post_restart_driving = TimelineEvent(
            id="evt-valid-1",
            event_type=EventType.DRIVING,
            duty_status=DutyStatus.DRIVING,
            start_time=restart_end, # Exactly at 09:35
            end_time=restart_end + timedelta(hours=4),
            duration_minutes=240,
            duration_hours=4.0,
            start_mile=500.0,
            end_mile=720.0,
            distance_miles=220.0,
            location_name="Post-Restart Highway",
            coordinates=(35.0, -90.0),
            remarks="Driving after completed 34h restart",
            leg_id=2
        )

        violations = HOSSimulationEngine.validate_restart_interval(
            [valid_post_restart_driving], restart_start, restart_end
        )
        self.assertEqual(len(violations), 0, "Activity starting exactly at restart_end must be permitted.")

    def test_activity_after_restart_end_is_allowed(self):
        """
        Verify that driving starting after restart completion (e.g. 10:00) is valid.
        """
        restart_start = datetime(2026, 9, 19, 23, 35, tzinfo=timezone.utc)
        restart_end = restart_start + timedelta(hours=34)

        post_driving = TimelineEvent(
            id="evt-valid-2",
            event_type=EventType.DRIVING,
            duty_status=DutyStatus.DRIVING,
            start_time=restart_end + timedelta(minutes=25), # 10:00
            end_time=restart_end + timedelta(hours=4),
            duration_minutes=215,
            duration_hours=3.58,
            start_mile=500.0,
            end_mile=700.0,
            distance_miles=200.0,
            location_name="Highway",
            coordinates=(35.0, -90.0),
            remarks="Driving well after restart",
            leg_id=2
        )

        violations = HOSSimulationEngine.validate_restart_interval(
            [post_driving], restart_start, restart_end
        )
        self.assertEqual(len(violations), 0)

    def test_transparent_decision_metrics_captured(self):
        """
        Verify that transparent HOSMetrics (driving_used, window_elapsed, break_driving_elapsed, cycle_used)
        are populated on generated timeline events and stops.
        """
        leg1 = {
            "distance_miles": 100.0,
            "duration_hours": 1.8,
            "coordinates": [[-87.6298, 41.8781], [-86.1581, 39.7684]],
            "cumulative_miles": [0.0, 100.0]
        }
        leg2 = {
            "distance_miles": 50.0,
            "duration_hours": 0.9,
            "coordinates": [[-86.1581, 39.7684], [-85.5, 39.5]],
            "cumulative_miles": [0.0, 50.0]
        }

        engine = HOSSimulationEngine(start_time=self.start_time, current_cycle_used=24.0)
        res = engine.simulate(self.sample_locations, leg1, leg2)

        # Check stops metrics
        for s in res["stops"]:
            self.assertIsNotNone(s.hos_metrics)
            self.assertEqual(s.hos_metrics.driving_limit, 11.0)
            self.assertEqual(s.hos_metrics.cycle_limit, 70.0)

        # Check events metrics
        for e in res["timeline"]:
            self.assertIsNotNone(e.metrics)
            self.assertGreaterEqual(e.metrics.cycle_used, 24.0)

    # ==================== DAILY DRIVING LIMIT REGRESSION TESTS ====================

    def test_daily_driving_limit_exact_11_hours_valid(self):
        """Regression test: Driving exactly 11.0 hours is fully compliant/valid."""
        valid, err = HOSSimulationEngine.validate_daily_driving_limit(11.0)
        self.assertTrue(valid, "Driving exactly 11.0 hours must be valid")
        self.assertIsNone(err)

    def test_daily_driving_limit_11_01_hours_violation(self):
        """Regression test: Driving 11.01 hours is an HOS violation."""
        valid, err = HOSSimulationEngine.validate_daily_driving_limit(11.01)
        self.assertFalse(valid, "Driving 11.01 hours must produce a violation")
        self.assertIsNotNone(err)
        self.assertIn("exceeds the maximum 11.0-hour limit", err)

    def test_daily_driving_limit_12_hours_violation(self):
        """Regression test: Driving 12.0 hours is an HOS violation."""
        valid, err = HOSSimulationEngine.validate_daily_driving_limit(12.0)
        self.assertFalse(valid, "Driving 12.0 hours must produce a violation")
        self.assertIsNotNone(err)
        self.assertIn("exceeds the maximum 11.0-hour limit", err)

    def test_schedule_validation_detects_daily_driving_exceeded(self):
        """
        Verify that validate_schedule marks compliance_status as 'Compliance Issue Detected'
        and flags DAILY_DRIVING_LIMIT_EXCEEDED when daily_logs has > 11.0h driving.
        """
        fake_daily_logs = [
            {"day_number": 1, "duty_hours": {"driving": 6.5}},
            {"day_number": 2, "duty_hours": {"driving": 12.0}},
            {"day_number": 3, "duty_hours": {"driving": 8.0}},
        ]
        result = HOSSimulationEngine.validate_schedule(
            timeline=[],
            stops=[],
            daily_logs=fake_daily_logs
        )
        self.assertFalse(result.passed)
        self.assertEqual(result.compliance_status, "Compliance Issue Detected")
        v_codes = [v.code for v in result.violations]
        self.assertIn("DAILY_DRIVING_LIMIT_EXCEEDED", v_codes)
        daily_violation = next(v for v in result.violations if v.code == "DAILY_DRIVING_LIMIT_EXCEEDED")
        self.assertIn("Day 2 driving total (12.0h) exceeds the maximum 11.0-hour limit", daily_violation.message)

    def test_chicago_dallas_atlanta_schedule_stays_within_11_hours_per_day(self):
        """
        Test that for long cross-country routes (e.g. Chicago -> Dallas -> Atlanta),
        the HOS simulation never schedules more than 11.0 hours driving on any single calendar day.
        """
        leg1 = {
            "distance_miles": 920.0,
            "duration_hours": 14.5,
            "coordinates": [[-87.6298, 41.8781], [-96.7970, 32.7767]],
            "cumulative_miles": [0.0, 920.0]
        }
        leg2 = {
            "distance_miles": 780.0,
            "duration_hours": 12.0,
            "coordinates": [[-96.7970, 32.7767], [-84.3880, 33.7490]],
            "cumulative_miles": [0.0, 780.0]
        }
        # Start in Central Time (America/Chicago) at 08:00
        engine = HOSSimulationEngine(start_time=self.start_time, current_cycle_used=0.0)
        res = engine.simulate(self.sample_locations, leg1, leg2)

        from apps.logs.generator import DailyLogSheetGenerator
        daily_logs = DailyLogSheetGenerator.generate_daily_logs(
            timeline=res["timeline"],
            start_time=self.start_time,
            end_time=res["end_time"],
            initial_cycle_used=0.0,
            origin_name="Chicago, IL",
            destination_name="Atlanta, GA",
            operational_timezone="America/Chicago"
        )

        # Validate schedule with generated daily_logs
        val_res = HOSSimulationEngine.validate_schedule(
            timeline=res["timeline"],
            stops=res["stops"],
            daily_logs=daily_logs
        )

        for day in daily_logs:
            d_hours = day.get("duty_hours", {}).get("driving", 0.0)
            self.assertLessEqual(
                d_hours,
                11.0,
                f"Day {day.get('day_number')} driving ({d_hours}h) must not exceed 11.0h"
            )

        self.assertTrue(val_res.passed, f"Validation should pass, but got violations: {[v.message for v in val_res.violations]}")
        # Without prior 7-day logs entered, status informs that historical data is required
        self.assertEqual(val_res.compliance_status, "Generated Trip Validated — Historical 70/8 Data Required")
        self.assertFalse(val_res.has_sufficient_history)
        self.assertEqual(val_res.status_type, "WARNING")

    # ==================== HISTORICAL 70/8 DATA VALIDATION TESTS ====================

    def test_no_historical_logs_returns_incomplete_cycle_validation_status(self):
        """
        Verify that when prior 7-day logs are unavailable (current_cycle_used == 0.0),
        validation status is 'Generated Trip Validated — Historical 70/8 Data Required'
        with status_type 'WARNING' and an INSUFFICIENT_HISTORICAL_DATA warning.
        """
        fake_daily_logs = [
            {
                "day_number": 1,
                "duty_hours": {"driving": 8.0, "on_duty_not_driving": 2.0, "off_duty": 14.0, "sleeper_berth": 0.0},
                "recap": {"has_sufficient_history": False, "historical_hours_used": 0.0, "total_recap_hours": 10.0}
            }
        ]
        result = HOSSimulationEngine.validate_schedule(
            timeline=[],
            stops=[],
            daily_logs=fake_daily_logs,
            has_sufficient_history=False
        )
        self.assertTrue(result.passed, "Driver review must not be blocked when daily rules pass")
        self.assertFalse(result.has_sufficient_history)
        self.assertEqual(result.compliance_status, "Generated Trip Validated — Historical 70/8 Data Required")
        self.assertEqual(result.status_type, "WARNING")
        self.assertIn("Full 70/8 cycle compliance requires prior 7-day driver logs", result.explanation)
        w_codes = [w.code for w in result.warnings]
        self.assertIn("INSUFFICIENT_HISTORICAL_DATA", w_codes)

    def test_historical_logs_available_returns_full_rolling_recap_validation(self):
        """
        Verify that when prior 7-day logs are available (current_cycle_used > 0.0),
        validation status is 'HOS Plan Validated' with status_type 'VALIDATED'.
        """
        fake_daily_logs = [
            {
                "day_number": 1,
                "duty_hours": {"driving": 8.0, "on_duty_not_driving": 2.0, "off_duty": 14.0, "sleeper_berth": 0.0},
                "recap": {"has_sufficient_history": True, "historical_hours_used": 24.0, "total_recap_hours": 34.0}
            }
        ]
        result = HOSSimulationEngine.validate_schedule(
            timeline=[],
            stops=[],
            daily_logs=fake_daily_logs,
            has_sufficient_history=True
        )
        self.assertTrue(result.passed)
        self.assertTrue(result.has_sufficient_history)
        self.assertEqual(result.compliance_status, "HOS Plan Validated")
        self.assertEqual(result.status_type, "VALIDATED")
        self.assertEqual(len(result.warnings), 0)

    def test_daily_driving_limit_remains_independently_validated_even_without_history(self):
        """
        Verify that even without historical data, daily driving violations (> 11.0h)
        are independently detected, mark passed=False, and set status to 'Compliance Issue Detected'.
        """
        fake_daily_logs = [
            {
                "day_number": 1,
                "duty_hours": {"driving": 12.0, "on_duty_not_driving": 2.0, "off_duty": 10.0, "sleeper_berth": 0.0},
                "recap": {"has_sufficient_history": False, "historical_hours_used": 0.0, "total_recap_hours": 14.0}
            }
        ]
        result = HOSSimulationEngine.validate_schedule(
            timeline=[],
            stops=[],
            daily_logs=fake_daily_logs,
            has_sufficient_history=False
        )
        self.assertFalse(result.passed, "Daily driving > 11h must fail validation")
        self.assertEqual(result.compliance_status, "Compliance Issue Detected")
        self.assertEqual(result.status_type, "ERROR")
        v_codes = [v.code for v in result.violations]
        self.assertIn("DAILY_DRIVING_LIMIT_EXCEEDED", v_codes)

