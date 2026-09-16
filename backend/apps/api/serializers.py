"""
DRF Serializers for Spotter ELD Route Planner API.
"""

from rest_framework import serializers

class GeocodeRequestSerializer(serializers.Serializer):
    query = serializers.CharField(required=True, max_length=255)

class PlanTripRequestSerializer(serializers.Serializer):
    current_location = serializers.CharField(
        required=True,
        max_length=255,
        help_text="Current driver location (e.g. 'Chicago, IL' or coordinate '41.8781, -87.6298')"
    )
    pickup_location = serializers.CharField(
        required=True,
        max_length=255,
        help_text="Pickup location (e.g. 'Dallas, TX')"
    )
    dropoff_location = serializers.CharField(
        required=True,
        max_length=255,
        help_text="Dropoff location (e.g. 'Atlanta, GA')"
    )
    current_cycle_used = serializers.FloatField(
        required=True,
        min_value=0.0,
        max_value=70.0,
        help_text="Current 70-hour cycle hours consumed (0.0 to 70.0)"
    )
    start_time = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text="Trip departure time in ISO 8601 format (defaults to current time)"
    )
    carrier_name = serializers.CharField(
        required=False,
        default="Spotter Freight Logistics",
        max_length=100
    )
    truck_number = serializers.CharField(
        required=False,
        default="TRK-408",
        max_length=50
    )
    trailer_number = serializers.CharField(
        required=False,
        default="TLR-9201",
        max_length=50
    )

    def validate_current_cycle_used(self, value):
        if value < 0.0 or value > 70.0:
            raise serializers.ValidationError("Current cycle hours must be between 0.0 and 70.0 under FMCSA 70h/8d regulations.")
        return value

class ValidateLogRequestSerializer(serializers.Serializer):
    day_number = serializers.IntegerField(required=True, min_value=1)
    duty_hours = serializers.DictField(required=True)
    remarks = serializers.ListField(child=serializers.DictField(), required=False, default=list)
    daily_logs = serializers.ListField(child=serializers.DictField(), required=False, default=list)
