/**
 * API service communicating directly with Django REST Framework backend.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api';

export async function checkBackendHealth() {
  try {
    const res = await fetch(`${API_BASE_URL}/health/`);
    if (!res.ok) throw new Error(`Health check failed (${res.status})`);
    return await res.json();
  } catch (err) {
    console.warn('Backend health check warning:', err.message);
    return null;
  }
}

export async function planTripApi({
  currentLocation,
  pickupLocation,
  dropoffLocation,
  cycleHoursUsed,
}) {
  const payload = {
    current_location: currentLocation,
    pickup_location: pickupLocation,
    dropoff_location: dropoffLocation,
    current_cycle_used: parseFloat(cycleHoursUsed) || 0.0,
  };

  const response = await fetch(`${API_BASE_URL}/plan-trip/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    const message =
      errData.error ||
      (typeof errData === 'object' ? Object.values(errData).flat().join(', ') : null) ||
      `Server error (${response.status})`;
    throw new Error(message);
  }

  return await response.json();
}

export async function validateLogApi({
  dayNumber,
  dutyHours,
  remarks = [],
  dailyLogs = [],
}) {
  const payload = {
    day_number: dayNumber,
    duty_hours: dutyHours,
    remarks: remarks,
    daily_logs: dailyLogs,
  };

  const response = await fetch(`${API_BASE_URL}/validate-log/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    return {
      valid: false,
      status: 'VIOLATION',
      errors: data.errors || [data.error || `Validation failed (${response.status})`],
      warnings: data.warnings || [],
    };
  }

  return data;
}
