"""
Unit tests for FMCSA Hours of Service Engine (49 CFR Part 395).
"""

from datetime import datetime, timezone
from django.test import TestCase
from apps.hos.engine import HOSSimulationEngine
from apps.hos.models import DutyStatus, EventType

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

        # Driving hours should be sum of driving legs (~5.9h), well under 11h
        self.assertAlmostEqual(res["total_distance_miles"], 330.0, delta=1.0)
        self.assertLess(res["total_driving_hours"], 11.0)
        # Should have Pre-trip, Pickup (1h), Dropoff (1h), and Post-trip stops
        stop_types = [s.stop_type for s in res["stops"]]
        self.assertIn("pickup", stop_types)
        self.assertIn("dropoff", stop_types)

    def test_30_min_break_after_8_hours(self):
        """Test that driving over 8 hours triggers a 30-minute break."""
        leg1 = {
            "distance_miles": 550.0,
            "duration_hours": 9.5, # > 8 hours of driving
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
            "duration_hours": 13.0, # Exceeds 11 hours limit
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
            "distance_miles": 1200.0, # Exceeds 1,000 miles
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

        fuel_events = [e for e in res["timeline"] if e.event_type == EventType.FUELING]
        self.assertGreaterEqual(len(fuel_events), 1, "Must schedule at least 1 fueling stop for > 1,000 miles")

    def test_34_hour_restart_when_70_hour_cycle_exhausted(self):
        """Test that 34-hour restart triggers when driver starts with high cycle used."""
        leg1 = {
            "distance_miles": 500.0,
            "duration_hours": 8.5,
            "coordinates": [[-87.6298, 41.8781], [-96.7970, 32.7767]],
            "cumulative_miles": [0.0, 500.0]
        }
        leg2 = {
            "distance_miles": 400.0,
            "duration_hours": 7.0,
            "coordinates": [[-96.7970, 32.7767], [-84.3880, 33.7490]],
            "cumulative_miles": [0.0, 400.0]
        }

        # Driver already used 65.0 hours out of 70.0 hours
        engine = HOSSimulationEngine(start_time=self.start_time, current_cycle_used=65.0)
        res = engine.simulate(self.sample_locations, leg1, leg2)

        event_types = [e.event_type for e in res["timeline"]]
        self.assertIn(EventType.RESTART_34H, event_types, "34-hour restart must be triggered when 70h cycle is reached")
