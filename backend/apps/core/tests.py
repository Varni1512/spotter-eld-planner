"""
Unit tests for timezone resolution and UTC-to-local conversion.
"""

from datetime import datetime, timezone
from django.test import TestCase
from apps.core.timezones import (
    get_location_timezone,
    convert_utc_to_location_time,
    format_datetime_in_location
)

class TimezoneTestCase(TestCase):
    def test_state_and_coordinate_resolutions(self):
        # California (Los Angeles)
        self.assertEqual(get_location_timezone(34.0522, -118.2437, "CA"), "America/Los_Angeles")
        # Arizona (Phoenix - no DST)
        self.assertEqual(get_location_timezone(33.4484, -112.0740, "AZ"), "America/Phoenix")
        # Colorado (Denver)
        self.assertEqual(get_location_timezone(39.7392, -104.9903, "CO"), "America/Denver")
        # Texas (Dallas)
        self.assertEqual(get_location_timezone(32.7767, -96.7970, "TX"), "America/Chicago")
        # Illinois (Chicago)
        self.assertEqual(get_location_timezone(41.8781, -87.6298, "IL"), "America/Chicago")
        # Tennessee (Nashville)
        self.assertEqual(get_location_timezone(36.1627, -86.7816, "TN"), "America/Chicago")
        # New York (NYC)
        self.assertEqual(get_location_timezone(40.7128, -74.0060, "NY"), "America/New_York")
        # Virginia (Richmond)
        self.assertEqual(get_location_timezone(37.5407, -77.4360, "VA"), "America/New_York")
        # Indiana (Indianapolis)
        self.assertEqual(get_location_timezone(39.7684, -86.1581, "IN"), "America/Indiana/Indianapolis")

    def test_dst_handling(self):
        # Summer date (July) - NY should be EDT (UTC-4)
        summer_utc = datetime(2026, 7, 15, 16, 0, tzinfo=timezone.utc)
        ny_summer = convert_utc_to_location_time(summer_utc, "America/New_York")
        self.assertEqual(ny_summer.hour, 12) # 16:00 UTC - 4 = 12:00 EDT

        # Winter date (January) - NY should be EST (UTC-5)
        winter_utc = datetime(2026, 1, 15, 17, 0, tzinfo=timezone.utc)
        ny_winter = convert_utc_to_location_time(winter_utc, "America/New_York")
        self.assertEqual(ny_winter.hour, 12) # 17:00 UTC - 5 = 12:00 EST

        # Arizona should stay UTC-7 all year round
        az_summer = convert_utc_to_location_time(summer_utc, "America/Phoenix")
        self.assertEqual(az_summer.hour, 9) # 16:00 UTC - 7 = 09:00 MST
        az_winter = convert_utc_to_location_time(winter_utc, "America/Phoenix")
        self.assertEqual(az_winter.hour, 10) # 17:00 UTC - 7 = 10:00 MST

    def test_formatted_string_includes_tz_abbreviation(self):
        dt_utc = datetime(2026, 9, 15, 14, 30, tzinfo=timezone.utc)
        formatted = format_datetime_in_location(dt_utc, "America/Chicago", "%b %d, %Y %H:%M %Z")
        self.assertIn("09:30", formatted) # 14:30 UTC - 5 = 09:30 CDT
        self.assertIn("CDT", formatted)
