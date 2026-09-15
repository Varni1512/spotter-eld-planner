"""
URL routing for Spotter ELD API.
"""

from django.urls import path
from .views import HealthCheckView, GeocodeView, PlanTripView

urlpatterns = [
    path('health/', HealthCheckView.as_view(), name='api-health'),
    path('geocode/', GeocodeView.as_view(), name='api-geocode'),
    path('plan-trip/', PlanTripView.as_view(), name='api-plan-trip'),
]
