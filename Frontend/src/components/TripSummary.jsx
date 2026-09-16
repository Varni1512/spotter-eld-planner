import React, { useState } from 'react';
import { Route, Clock, BatteryMedium, MapPinCheck, CheckCircle2, AlertTriangle, ShieldCheck, ChevronDown, ChevronUp, Info } from 'lucide-react';

function formatHours(hoursFloat) {
  if (!hoursFloat && hoursFloat !== 0) return '0h 00m';
  const h = Math.floor(hoursFloat);
  const m = Math.round((hoursFloat - h) * 60);
  return `${h}h ${String(m).padStart(2, '0')}m`;
}

export default function TripSummary({ summary, isPlanned, validation }) {
  const [showHOSDetails, setShowHOSDetails] = useState(false);

  if (!isPlanned || !summary) {
    return (
      <div className="bg-white rounded-xl border border-dashed border-slate-300 p-6 text-center shadow-2xs">
        <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center mx-auto text-slate-400 mb-2">
          <Route className="w-5 h-5" />
        </div>
        <h3 className="text-sm font-semibold text-slate-800">Trip Summary Awaiting Route Calculation</h3>
        <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
          Enter trip locations and current cycle hours, then click "Plan Route &amp; Generate ELD Logs" to generate real distance, driving duration, and HOS compliance metrics.
        </p>
      </div>
    );
  }

  const counts = summary.counts || {};
  const isCompliant = validation ? validation.passed : true;
  const complianceStatusText = validation?.compliance_status || (isCompliant ? 'HOS Plan Validated' : 'Compliance Issue Detected');
  const isDailyLimitExceeded = validation?.violations?.some(
    (v) => v.code === 'DAILY_DRIVING_LIMIT_EXCEEDED' || v.code === '11H_DRIVING_LIMIT'
  );

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
      badge: isDailyLimitExceeded ? '11h Limit Exceeded' : '11h Shift Limit Enforced',
      badgeColor: isDailyLimitExceeded
        ? 'bg-rose-50 text-rose-700 border border-rose-200/60 font-semibold'
        : 'bg-emerald-50 text-emerald-700 border border-emerald-200/60',
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
      badge: isCompliant ? 'FMCSA Part 395 Verified' : 'Review Required',
      badgeColor: isCompliant
        ? 'bg-emerald-50 text-emerald-700 border border-emerald-200/60'
        : 'bg-rose-50 text-rose-700 border border-rose-200/60',
    },
  ];

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-slate-800 uppercase tracking-wider">
          Route Overview &amp; HOS Metrics
        </h2>

        <div className="flex items-center gap-2">
          {/* Dynamic Compliance Badge */}
          <span
            className={`text-xs font-semibold px-2.5 py-1 rounded-md border flex items-center gap-1.5 ${
              isCompliant
                ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                : 'bg-rose-50 text-rose-700 border-rose-200'
            }`}
          >
            {isCompliant ? (
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
            ) : (
              <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
            )}
            <span>{complianceStatusText}</span>
          </span>

          <button
            type="button"
            onClick={() => setShowHOSDetails(!showHOSDetails)}
            className="text-xs font-medium text-blue-600 hover:text-blue-800 bg-blue-50/70 hover:bg-blue-100/70 border border-blue-200 px-2.5 py-1 rounded-md transition flex items-center gap-1 cursor-pointer"
          >
            <Info className="w-3.5 h-3.5" />
            <span>{showHOSDetails ? 'Hide HOS Rules' : 'HOS Rule Details'}</span>
            {showHOSDetails ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* Prominent HOS Violations Banner */}
      {!isCompliant && validation?.violations?.length > 0 && (
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-3.5 text-xs space-y-1.5 animate-in fade-in">
          <div className="flex items-center gap-2 font-bold text-rose-900">
            <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>Compliance Issue Detected ({validation.violations.length} {validation.violations.length === 1 ? 'Violation' : 'Violations'})</span>
          </div>
          <ul className="list-disc list-inside space-y-1 text-rose-800 pl-1">
            {validation.violations.map((violation, idx) => (
              <li key={idx} className="leading-relaxed">
                <span className="font-semibold">{violation.code}:</span> {violation.message}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Expandable HOS Rule Transparency Drawer */}
      {showHOSDetails && (
        <div className="bg-slate-900 text-slate-100 rounded-xl p-4 shadow-sm border border-slate-800 text-xs animate-in fade-in duration-200 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <span className="font-semibold text-sm flex items-center gap-1.5 text-white">
              <ShieldCheck className="w-4 h-4 text-blue-400" />
              FMCSA 49 CFR Part 395 Deterministic Calculation Limits
            </span>
            <span className="text-[11px] text-slate-400">Property-Carrying Standard</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            <div className="bg-slate-800/80 rounded-lg p-3 border border-slate-700/60">
              <div className="text-slate-400 font-medium">11-Hour Driving Limit</div>
              <div className="text-sm font-bold text-white mt-1">11.00 hrs max per shift</div>
              <div className="text-[11px] text-slate-400 mt-1">Driving stops automatically and schedules 10h rest upon reaching 11h.</div>
              <div className="text-[10px] font-semibold text-emerald-400 mt-2">STATUS: STRICTLY ENFORCED</div>
            </div>

            <div className="bg-slate-800/80 rounded-lg p-3 border border-slate-700/60">
              <div className="text-slate-400 font-medium">14-Hour Duty Window</div>
              <div className="text-sm font-bold text-white mt-1">14.00 consecutive hrs</div>
              <div className="text-[11px] text-slate-400 mt-1">Cannot drive after 14th hour following 10 consecutive hours off-duty.</div>
              <div className="text-[10px] font-semibold text-emerald-400 mt-2">STATUS: STRICTLY ENFORCED</div>
            </div>

            <div className="bg-slate-800/80 rounded-lg p-3 border border-slate-700/60">
              <div className="text-slate-400 font-medium">30-Minute Rest Break</div>
              <div className="text-sm font-bold text-white mt-1">Every 8.00 hrs driving</div>
              <div className="text-[11px] text-slate-400 mt-1">Mandatory 30-min break taken as Off Duty before resuming driving.</div>
              <div className="text-[10px] font-semibold text-emerald-400 mt-2">STATUS: SCHEDULED AUTOMATICALLY</div>
            </div>

            <div className="bg-slate-800/80 rounded-lg p-3 border border-slate-700/60">
              <div className="text-slate-400 font-medium">70-Hour / 8-Day Cycle</div>
              <div className="text-sm font-bold text-white mt-1">70.00 hrs max on-duty</div>
              <div className="text-[11px] text-slate-400 mt-1">Cumulative on-duty time tracks against 70h cycle. Available tomorrow is 70 - Line B.</div>
              <div className="text-[10px] font-semibold text-indigo-400 mt-2">CURRENT REMAINING: {summary.cycle_remaining_hours || 0} hrs</div>
            </div>

            <div className="bg-slate-800/80 rounded-lg p-3 border border-slate-700/60">
              <div className="text-slate-400 font-medium">34-Hour Cycle Restart</div>
              <div className="text-sm font-bold text-white mt-1">34.00 consecutive hrs rest</div>
              <div className="text-[11px] text-slate-400 mt-1">Full qualifying rest resets cycle hours to 70. Driving during restart is strictly prohibited.</div>
              <div className="text-[10px] font-semibold text-purple-400 mt-2">
                RESTARTS SCHEDULED: {counts.cycle_restarts || 0}
              </div>
            </div>

            <div className="bg-slate-800/80 rounded-lg p-3 border border-slate-700/60">
              <div className="text-slate-400 font-medium">Mandatory Fueling</div>
              <div className="text-sm font-bold text-white mt-1">Every ≤ 1,000 miles</div>
              <div className="text-[11px] text-slate-400 mt-1">30-minute on-duty fueling stops planned along commercial route corridor.</div>
              <div className="text-[10px] font-semibold text-amber-400 mt-2">
                FUEL STOPS: {counts.fuel_stops || 0}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 4 Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        {cards.map((card) => {
          const Icon = card.icon;
          return (
            <div
              key={card.id}
              className="bg-white rounded-xl border border-slate-200/90 p-4 shadow-xs hover:border-slate-300 transition-all flex flex-col justify-between"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="text-xs font-semibold text-slate-600 whitespace-nowrap overflow-visible">
                  {card.label}
                </div>
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
