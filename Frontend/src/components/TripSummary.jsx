import React from 'react';
import { Route, Clock, BatteryMedium, MapPinCheck, CheckCircle2 } from 'lucide-react';

function formatHours(hoursFloat) {
  if (!hoursFloat && hoursFloat !== 0) return '0h 00m';
  const h = Math.floor(hoursFloat);
  const m = Math.round((hoursFloat - h) * 60);
  return `${h}h ${String(m).padStart(2, '0')}m`;
}

export default function TripSummary({ summary, isPlanned }) {
  if (!isPlanned || !summary) {
    return (
      <div className="bg-white rounded-xl border border-dashed border-slate-300 p-6 text-center shadow-2xs">
        <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center mx-auto text-slate-400 mb-2">
          <Route className="w-5 h-5" />
        </div>
        <h3 className="text-sm font-semibold text-slate-800">Trip Summary Awaiting Route Calculation</h3>
        <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
          Enter trip locations and current cycle hours, then click "Plan Route" to generate real distance, driving duration, and HOS compliance metrics.
        </p>
      </div>
    );
  }

  const counts = summary.counts || {};
  const cards = [
    {
      id: 'distance',
      label: 'Total Route Distance',
      value: `${summary.total_distance_miles?.toLocaleString() || 0} mi`,
      subtext: `Leg 1: ${summary.leg1_distance_miles || 0} mi • Leg 2: ${summary.leg2_distance_miles || 0} mi`,
      icon: Route,
      iconBg: 'bg-blue-50 text-blue-600',
      badge: `${summary.total_calendar_days || 1} Calendar Days`,
      badgeColor: 'bg-blue-50 text-blue-700 border border-blue-200/60',
    },
    {
      id: 'driving-time',
      label: 'Total Driving Duration',
      value: formatHours(summary.total_driving_hours),
      subtext: `On-Duty Total: ${formatHours(summary.total_on_duty_hours)}`,
      icon: Clock,
      iconBg: 'bg-amber-50 text-amber-600',
      badge: '11h Shift Limit Enforced',
      badgeColor: 'bg-emerald-50 text-emerald-700 border border-emerald-200/60',
    },
    {
      id: 'cycle-used',
      label: 'Current Cycle Used',
      value: `${summary.current_cycle_used_hours?.toFixed(1) || 0} hrs`,
      subtext: `${summary.cycle_remaining_hours?.toFixed(1) || 0} hrs remaining of 70h`,
      icon: BatteryMedium,
      iconBg: 'bg-indigo-50 text-indigo-600',
      badge: '70h / 8-Day Cycle Rule',
      badgeColor: 'bg-indigo-50 text-indigo-700 border border-indigo-200/60',
    },
    {
      id: 'stops-count',
      label: 'Scheduled Route Stops',
      value: `${counts.total_stops || 0} Stops`,
      subtext: `${counts.fuel_stops || 0} Fuel (≤1k mi) • ${counts.rest_breaks || 0} Break • ${counts.sleeper_rests || 0} Sleep`,
      icon: MapPinCheck,
      iconBg: 'bg-emerald-50 text-emerald-600',
      badge: 'FMCSA Part 395 Verified',
      badgeColor: 'bg-emerald-50 text-emerald-700 border border-emerald-200/60',
    },
  ];

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-800 uppercase tracking-wider">
          Route Overview &amp; HOS Metrics
        </h2>
        <span className="text-xs text-emerald-600 font-medium flex items-center gap-1">
          <CheckCircle2 className="w-3.5 h-3.5" />
          <span>Real Backend Calculated Route</span>
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        {cards.map((card) => {
          const Icon = card.icon;
          return (
            <div
              key={card.id}
              className="bg-white rounded-xl border border-slate-200/90 p-4 shadow-xs hover:border-slate-300 transition-all flex flex-col justify-between"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="text-xs font-medium text-slate-500 line-clamp-1">{card.label}</div>
                <div className={`w-8 h-8 rounded-lg ${card.iconBg} flex items-center justify-center shrink-0`}>
                  <Icon className="w-4 h-4" />
                </div>
              </div>

              <div className="mt-2.5 mb-1.5">
                <div className="text-2xl font-bold tracking-tight text-slate-900">
                  {card.value}
                </div>
                <div className="text-xs text-slate-500 mt-0.5 font-normal">
                  {card.subtext}
                </div>
              </div>

              <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
                <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${card.badgeColor}`}>
                  {card.badge}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
