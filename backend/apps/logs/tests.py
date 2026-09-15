"""
Unit tests for DailyLogSheetGenerator (49 CFR § 395.8 paper log compliance).
"""

from datetime import datetime, timezone
from django.test import TestCase
from apps.hos.engine import HOSSimulationEngine
from apps.logs.generator import DailyLogSheetGenerator

class DailyLogTestCase(TestCase):
    def test_daily_log_hours_sum_strictly_to_24(self):
        """Every generated daily log sheet must sum to exactly 24.0 hours."""
        start_time = datetime(2026, 9, 15, 8, 0, 0, tzinfo=timezone.utc)
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

        engine = HOSSimulationEngine(start_time=start_time, current_cycle_used=25.0)
        sim = engine.simulate(locations, leg1, leg2)

        daily_sheets = DailyLogSheetGenerator.generate_daily_logs(
            timeline=sim["timeline"],
            start_time=start_time,
            end_time=sim["end_time"],
            initial_cycle_used=25.0,
            origin_name="Chicago, IL",
            destination_name="Atlanta, GA"
        )

        self.assertGreaterEqual(len(daily_sheets), 2, "Trip should span multiple calendar days")

        for idx, sheet in enumerate(daily_sheets):
            hours = sheet["duty_hours"]
            total_sum = hours["off_duty"] + hours["sleeper_berth"] + hours["driving"] + hours["on_duty_not_driving"]
            self.assertEqual(
                round(total_sum, 2),
                24.0,
                f"Day {idx + 1} hours must sum to exactly 24.0, got {total_sum} (Off: {hours['off_duty']}, Sleeper: {hours['sleeper_berth']}, Drv: {hours['driving']}, On: {hours['on_duty_not_driving']})"
            )
            # Verify SVG markup is non-empty
            self.assertTrue(sheet["svg_markup"].startswith("<svg"))
            self.assertIn("DRIVER'S DAILY LOG", sheet["svg_markup"])
            # Verify recap exists
            self.assertIn("line_a_on_duty_today", sheet["recap"])
            self.assertIn("line_b_total_last_7_days", sheet["recap"])
            self.assertIn("line_c_available_tomorrow", sheet["recap"])
