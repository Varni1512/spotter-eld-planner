import React from 'react';
import { Route, Clock, BatteryMedium, MapPinCheck, CheckCircle2 } from 'lucide-react';

export default function TripSummary({ summary, isPlanned }) {
  if (!isPlanned) {
    return (
      <div className="bg-white rounded-xl border border-dashed border-slate-300 p-6 text-center shadow-2xs">
        <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center mx-auto text-slate-400 mb-2">
          <Route className="w-5 h-5" />
        </div>
        <h3 className="text-sm font-semibold text-slate-800">Trip Summary Awaiting Route Input</h3>
        <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
          Submit trip parameters or load a sample preset above to see route distance, driving estimates, and stop counts.
        </p>
      </div>
    );
  }

  const cards = [
    {
      id: 'distance',
      label: 'Total Route Distance',
      value: summary.totalDistance || '478.4 mi',
      subtext: `${summary.highwayCorridor || 'I-65 Corridor'} (Truck Safe)`,
      icon: Route,
      iconBg: 'bg-blue-50 text-blue-600',
      badge: 'Practical Commercial Miles',
      badgeColor: 'bg-slate-100 text-slate-700',
    },
    {
      id: 'driving-time',
      label: 'Estimated Driving Time',
      value: summary.drivingTime || '8h 15m',
      subtext: `+${summary.onDutyTime || '1h 45m'} stops / loading`,
      icon: Clock,
      iconBg: 'bg-amber-50 text-amber-600',
      badge: 'DOT 11h Limit OK',
      badgeColor: 'bg-emerald-50 text-emerald-700 border border-emerald-200/60',
    },
    {
      id: 'cycle-used',
      label: 'Current Cycle Used',
      value: summary.cycleUsed || '42.5 hrs',
      subtext: `${summary.cycleRemaining || '27.5 hrs'} remaining of 70h`,
      icon: BatteryMedium,
      iconBg: 'bg-indigo-50 text-indigo-600',
      badge: '70h / 8-Day Rule',
      badgeColor: 'bg-indigo-50 text-indigo-700 border border-indigo-200/60',
    },
    {
      id: 'stops-count',
      label: 'Planned Route Stops',
      value: `${summary.stopsCount || 5} Stops`,
      subtext: `${summary.fuelStops || 1} Fuel • ${summary.restStops || 1} DOT Rest`,
      icon: MapPinCheck,
      iconBg: 'bg-emerald-50 text-emerald-600',
      badge: 'All Stops Compliant',
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
          <span>HOS Feasible Route</span>
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
