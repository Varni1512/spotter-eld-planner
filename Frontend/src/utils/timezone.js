/**
 * Timezone utilities ensuring exact timestamp consistency between
 * Planned Stops & Timeline Schedule and the Driver's Daily Log sheets.
 */

export function formatStopSchedule(stop) {
  if (!stop) return { arrival: '—', departure: '—', display: '—' };

  if (stop.arrival_local_display && stop.departure_local_display) {
    return {
      arrival: stop.arrival_local_display,
      departure: stop.departure_local_display,
      display: `${stop.arrival_local_display} – ${stop.departure_local_display}`,
      timezone: stop.timezone_id || 'America/Chicago',
    };
  }

  // Fallback to ISO string formatting if local display is absent
  const arr = stop.arrival_time ? new Date(stop.arrival_time) : null;
  const dep = stop.departure_time ? new Date(stop.departure_time) : null;

  const fmt = (d) => {
    if (!d) return '—';
    return d.toLocaleString([], {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return {
    arrival: fmt(arr),
    departure: fmt(dep),
    display: `${fmt(arr)} – ${fmt(dep)}`,
    timezone: stop.timezone_id || 'Local',
  };
}
