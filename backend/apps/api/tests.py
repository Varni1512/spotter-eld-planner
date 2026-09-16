"""
API integration tests for Spotter ELD Route Planner endpoints.
"""

from rest_framework.test import APITestCase
from rest_framework import status

class SpotterAPITestCase(APITestCase):
    def test_health_check_endpoint(self):
        """Verify /api/health/ returns 200 OK with FMCSA ruleset metadata."""
        response = self.client.get('/api/health/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "ok")
        self.assertIn("fmcsa_ruleset", response.data)
        self.assertEqual(response.data["fmcsa_ruleset"]["driving_limit"], "11 hours")

    def test_geocode_endpoint(self):
        """Verify /api/geocode/ resolves location queries."""
        response = self.client.get('/api/geocode/?q=Chicago')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("latitude", response.data)
        self.assertIn("longitude", response.data)
        self.assertAlmostEqual(response.data["latitude"], 41.87, delta=0.1)

    def test_plan_trip_endpoint(self):
        """Verify /api/plan-trip/ performs full routing, HOS simulation, and daily log generation."""
        payload = {
            "current_location": "Chicago, IL",
            "pickup_location": "Dallas, TX",
            "dropoff_location": "Atlanta, GA",
            "current_cycle_used": 24.0,
            "start_time": "2026-09-15T08:00:00Z"
        }
        response = self.client.post('/api/plan-trip/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "success")
        self.assertEqual(response.data["mode"], "SIMULATION_MODE")
        self.assertIn("validation", response.data)

        # Verify summary
        summary = response.data["summary"]
        self.assertGreater(summary["total_distance_miles"], 1000)
        self.assertGreater(summary["total_driving_hours"], 20)
        self.assertGreaterEqual(summary["total_calendar_days"], 2)

        # Verify stops exist with required types
        stops = response.data["stops"]
        stop_types = [s["stop_type"] for s in stops]
        self.assertIn("current_location", stop_types)
        self.assertIn("pickup", stop_types)
        self.assertIn("dropoff", stop_types)
        self.assertIn("fuel", stop_types, "Long trip must have fueling stop(s)")
        self.assertIn("sleeper_rest", stop_types, "Multi-day trip must have 10-hour sleeper rests")

        # Verify timezone and metrics annotations on stops
        for s in stops:
            self.assertIn("timezone_id", s)
            self.assertIn("arrival_local_display", s)
            self.assertIn("hos_metrics", s)

        # Verify validation fields
        val = response.data["validation"]
        self.assertTrue(val["passed"])
        self.assertEqual(val["compliance_status"], "HOS Plan Validated")
        self.assertEqual(val["status_type"], "VALIDATED")
        self.assertTrue(val["has_sufficient_history"])

        # Verify daily ELD logs
        daily_logs = response.data["daily_logs"]
        self.assertGreaterEqual(len(daily_logs), 2)
        for log in daily_logs:
            hours = log["duty_hours"]
            total = hours["off_duty"] + hours["sleeper_berth"] + hours["driving"] + hours["on_duty_not_driving"]
            self.assertEqual(round(total, 2), 24.0)
            self.assertTrue(log["svg_markup"].startswith("<svg"))

    def test_plan_trip_insufficient_history_status(self):
        """Verify that when current_cycle_used is 0.0, API returns incomplete 70/8 cycle warning status."""
        payload = {
            "current_location": "Chicago, IL",
            "pickup_location": "Dallas, TX",
            "dropoff_location": "Atlanta, GA",
            "current_cycle_used": 0.0,
            "start_time": "2026-09-15T08:00:00Z"
        }
        response = self.client.post('/api/plan-trip/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        val = response.data["validation"]
        self.assertTrue(val["passed"])
        self.assertFalse(val["has_sufficient_history"])
        self.assertEqual(val["compliance_status"], "Generated Trip Validated — Historical 70/8 Data Required")
        self.assertEqual(val["status_type"], "WARNING")
        self.assertIn("Full 70/8 cycle compliance requires prior 7-day driver logs", val["explanation"])
        self.assertTrue(any(w["code"] == "INSUFFICIENT_HISTORICAL_DATA" for w in val["warnings"]))

    def test_validate_log_endpoint_valid_case(self):
        """Verify /api/validate-log/ accepts a valid 24-hour log update."""
        payload = {
            "day_number": 1,
            "duty_hours": {
                "off_duty": 10.0,
                "sleeper_berth": 0.0,
                "driving": 11.0,
                "on_duty_not_driving": 3.0
            }
        }
        response = self.client.post('/api/validate-log/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["valid"])
        self.assertEqual(response.data["total_hours"], 24.0)
        self.assertEqual(response.data["status"], "VALIDATED")

    def test_validate_log_endpoint_invalid_sum(self):
        """Verify /api/validate-log/ rejects an invalid total duration (> 24.0h)."""
        payload = {
            "day_number": 1,
            "duty_hours": {
                "off_duty": 12.0,
                "sleeper_berth": 0.0,
                "driving": 11.0,
                "on_duty_not_driving": 3.0 # Total 26h
            }
        }
        response = self.client.post('/api/validate-log/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertFalse(response.data["valid"])
        self.assertEqual(response.data["status"], "VIOLATION")
        self.assertIn("must equal exactly 24.0 hours", response.data["errors"][0])
