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

        # Verify daily ELD logs
        daily_logs = response.data["daily_logs"]
        self.assertGreaterEqual(len(daily_logs), 2)
        for log in daily_logs:
            hours = log["duty_hours"]
            total = hours["off_duty"] + hours["sleeper_berth"] + hours["driving"] + hours["on_duty_not_driving"]
            self.assertEqual(round(total, 2), 24.0)
            self.assertTrue(log["svg_markup"].startswith("<svg"))
            self.assertIn("recap", log)
