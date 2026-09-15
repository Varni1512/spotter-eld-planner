import React from 'react';
import {
  MapPin,
  Clock,
  Fuel,
  Coffee,
  Building2,
  Flag,
  Navigation,
  Milestone,
} from 'lucide-react';

export default function StopsTimeline({ stops, isPlanned, onPlanSample }) {
  if (!isPlanned || !stops || stops.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-slate-200/90 shadow-xs p-6 text-center">
        <div className="w-12 h-12 rounded-xl bg-slate-50 border border-slate-200 text-slate-400 flex items-center justify-center mx-auto mb-3">
          <Milestone className="w-6 h-6 text-slate-400" />
        </div>
        <h3 className="text-sm font-semibold text-slate-900">Stops &amp; Schedule Timeline</h3>
        <p className="text-xs text-slate-500 max-w-md mx-auto mt-1 mb-4">
          Once your trip parameters are submitted, your complete sequence of departure, loading, commercial fueling, 30-minute DOT rest breaks, and consignee delivery will be detailed here.
        </p>
        <button
          type="button"
          onClick={onPlanSample}
          className="text-xs font-medium text-blue-600 hover:text-blue-800 bg-blue-50 hover:bg-blue-100/80 px-3 py-1.5 rounded-md transition-colors"
        >
          View Example Stops Timeline
        </button>
      </div>
    );
  }

  // Icon and badge styling helpers
  const getStopTypeDetails = (type) => {
    switch (type) {
      case 'origin':
        return {
          icon: Navigation,
          iconBg: 'bg-blue-600 text-white',
          badgeStyle: 'bg-blue-50 text-blue-700 border-blue-200',
        };
      case 'pickup':
        return {
          icon: Building2,
          iconBg: 'bg-amber-600 text-white',
          badgeStyle: 'bg-amber-50 text-amber-700 border-amber-200',
        };
      case 'fuel':
        return {
          icon: Fuel,
          iconBg: 'bg-purple-600 text-white',
          badgeStyle: 'bg-purple-50 text-purple-700 border-purple-200',
        };
      case 'rest':
        return {
          icon: Coffee,
          iconBg: 'bg-sky-600 text-white',
          badgeStyle: 'bg-sky-50 text-sky-700 border-sky-200',
        };
      case 'dropoff':
        return {
          icon: Flag,
          iconBg: 'bg-emerald-600 text-white',
          badgeStyle: 'bg-emerald-50 text-emerald-700 border-emerald-200',
        };
      default:
        return {
          icon: MapPin,
          iconBg: 'bg-slate-600 text-white',
          badgeStyle: 'bg-slate-50 text-slate-700 border-slate-200',
        };
    }
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200/90 shadow-xs overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-slate-900">
            Planned Stops &amp; Timeline Schedule
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Chronological route segments with FMCSA compliance breaks &amp; facility windows
          </p>
        </div>
        <span className="text-xs font-medium px-2.5 py-1 rounded-md bg-slate-100 text-slate-700 border border-slate-200">
          5 Sequenced Stops
        </span>
      </div>

      {/* Timeline List */}
      <div className="p-4 sm:p-6 space-y-6">
        <div className="relative">
          {/* Vertical connecting line */}
          <div className="absolute top-4 bottom-4 left-4 sm:left-5 -ml-px w-0.5 bg-slate-200" aria-hidden="true" />

          <div className="space-y-6 sm:space-y-7">
            {stops.map((stop) => {
              const { icon: StopIcon, iconBg, badgeStyle } = getStopTypeDetails(stop.type);

              return (
                <div key={stop.id} className="relative flex items-start gap-4 sm:gap-5 group">
                  {/* Stop Marker Icon */}
                  <div
                    className={`relative z-10 w-8 h-8 sm:w-10 sm:h-10 rounded-full ${iconBg} flex items-center justify-center shadow-xs ring-4 ring-white shrink-0`}
                  >
                    <StopIcon className="w-4 h-4 sm:w-4 sm:h-4" />
                  </div>

                  {/* Stop Card Content */}
                  <div className="flex-1 bg-slate-50/70 hover:bg-slate-50 border border-slate-200/80 rounded-xl p-4 sm:p-4.5 transition-all">
                    
                    {/* Top row: Badge, Stop Title, and Mileage */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 pb-2 border-b border-slate-200/60">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-[11px] font-bold text-slate-500 font-mono">
                          STOP #{stop.stepNumber}
                        </span>
                        <span className={`text-xs font-semibold px-2 py-0.5 rounded-md border ${badgeStyle}`}>
                          {stop.badgeText}
                        </span>
                        <h4 className="text-sm font-semibold text-slate-900">
                          {stop.title}
                        </h4>
                      </div>

                      <div className="text-xs text-slate-500 font-medium">
                        {stop.cumulativeDistance !== "0.0 mi" ? (
                          <span>{stop.legDistance} leg • <strong className="text-slate-700">{stop.cumulativeDistance}</strong></span>
                        ) : (
                          <span className="text-slate-400">Departure origin</span>
                        )}
                      </div>
                    </div>

                    {/* Middle row: Address & Time / Activity */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-3">
                      <div>
                        <div className="text-xs text-slate-600 flex items-start gap-1.5">
                          <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />
                          <span>{stop.address}</span>
                        </div>
                        <div className="text-xs text-slate-500 mt-2 flex items-center gap-1.5">
                          <Clock className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                          <span>ETA: <strong className="text-slate-800 font-semibold">{stop.eta}</strong></span>
                          <span className="text-slate-300">•</span>
                          <span>ETD: <strong className="text-slate-800 font-semibold">{stop.etd}</strong></span>
                        </div>
                      </div>

                      <div className="bg-white rounded-lg border border-slate-200/70 p-2.5 text-xs flex flex-col justify-between">
                        <div className="flex items-center justify-between text-slate-700 mb-1">
                          <span className="font-semibold text-slate-900">{stop.activity}</span>
                          <span className="text-[11px] font-medium text-slate-500 px-1.5 py-0.5 bg-slate-100 rounded">
                            {stop.duration}
                          </span>
                        </div>
                        <div className="text-[11px] text-slate-500">
                          Duty Status: <span className="font-medium text-slate-700">{stop.hosStatus}</span>
                        </div>
                      </div>
                    </div>

                    {/* Operational Notes */}
                    {stop.notes && (
                      <div className="mt-2.5 pt-2 border-t border-slate-200/50 text-[11px] text-slate-500 italic">
                        Dispatcher note: {stop.notes}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
