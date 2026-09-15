/**
 * Preset route configurations for testing and quick selection.
 * These are real geographical queries passed to the backend calculation engine.
 */

export const ROUTE_PRESETS = [
  {
    name: 'Midwest to South (Chicago ➔ Dallas ➔ Atlanta)',
    currentLocation: 'Chicago, IL',
    pickupLocation: 'Dallas, TX',
    dropoffLocation: 'Atlanta, GA',
    cycleHoursUsed: 24.0,
  },
  {
    name: 'Coast to Coast (Los Angeles ➔ Denver ➔ New York)',
    currentLocation: 'Los Angeles, CA',
    pickupLocation: 'Denver, CO',
    dropoffLocation: 'New York, NY',
    cycleHoursUsed: 48.0,
  },
  {
    name: 'Regional Delivery (Chicago ➔ Indianapolis ➔ Columbus)',
    currentLocation: 'Chicago, IL',
    pickupLocation: 'Indianapolis, IN',
    dropoffLocation: 'Columbus, OH',
    cycleHoursUsed: 15.0,
  },
];
