import React from 'react';
import { Navigation, ArrowRight, Clock, Building2, Flag, Sparkles, AlertTriangle } from 'lucide-react';
import { ROUTE_PRESETS } from '../data/presets';

export default function TripForm({
  formData,
  onChange,
  onSubmit,
  onSelectPreset,
  isPlanning,
  errorMessage,
}) {
  const cycleLimit = 70.0;
  const currentCycle = parseFloat(formData.cycleHoursUsed) || 0;
  const remainingCycle = Math.max(0, cycleLimit - currentCycle).toFixed(1);
  const cyclePercent = Math.min(100, Math.round((currentCycle / cycleLimit) * 100));

  return (
    <div className="bg-white rounded-xl border border-slate-200/90 shadow-xs p-5 sm:p-6 transition-all">
      <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-100">
        <div>
          <h2 className="text-base sm:text-lg font-semibold text-slate-900 flex items-center gap-2">
            <span>Trip Parameters</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Enter dispatch locations and driver cycle hours to calculate real compliant route
          </p>
        </div>
        <span className="text-[11px] font-semibold px-2.5 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
          FMCSA 70h/8d
        </span>
      </div>

      {/* Preset Buttons for Quick Testing */}
      <div className="mb-5">
        <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-2 flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-amber-500" /> Quick Load Presets
        </label>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          {ROUTE_PRESETS.map((p, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => onSelectPreset && onSelectPreset(p)}
              disabled={isPlanning}
              className="text-left p-2.5 rounded-lg border border-slate-200 hover:border-blue-400 bg-slate-50/70 hover:bg-blue-50/40 transition text-xs cursor-pointer disabled:opacity-50"
            >
              <div className="font-semibold text-slate-800 truncate">{p.name.split('(')[0]}</div>
              <div className="text-[11px] text-slate-500 truncate mt-0.5">
                {p.currentLocation} → {p.dropoffLocation}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Error Message Display */}
      {errorMessage && (
        <div className="mb-4 p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <span className="font-bold">Error: </span>
            {errorMessage}
          </div>
        </div>
      )}

      <form onSubmit={onSubmit} className="space-y-4">
        {/* Field 1: Current Driver Location */}
        <div>
          <label htmlFor="currentLocation" className="block text-xs font-semibold text-slate-700 mb-1.5 uppercase tracking-wider">
            Current Driver Location (Origin)
          </label>
          <div className="relative rounded-lg shadow-xs">
            <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400">
              <Navigation className="h-4 w-4 text-blue-600" />
            </div>
            <input
              type="text"
              id="currentLocation"
              name="currentLocation"
              required
              value={formData.currentLocation}
              onChange={onChange}
              placeholder="e.g. Chicago, IL"
              className="block w-full rounded-lg border border-slate-300 py-2.5 pl-9 pr-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-600 focus:ring-2 focus:ring-blue-600/15 focus:outline-none transition-all"
            />
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Starting point or current terminal dispatch origin</p>
        </div>

        {/* Field 2: Pickup Location */}
        <div>
          <label htmlFor="pickupLocation" className="block text-xs font-semibold text-slate-700 mb-1.5 uppercase tracking-wider flex items-center justify-between">
            <span>Pickup Location (Shipper)</span>
            <span className="text-[11px] text-amber-700 font-medium bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200">
              1 hr on-duty load
            </span>
          </label>
          <div className="relative rounded-lg shadow-xs">
            <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400">
              <Building2 className="h-4 w-4 text-amber-600" />
            </div>
            <input
              type="text"
              id="pickupLocation"
              name="pickupLocation"
              required
              value={formData.pickupLocation}
              onChange={onChange}
              placeholder="e.g. Dallas, TX"
              className="block w-full rounded-lg border border-slate-300 py-2.5 pl-9 pr-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-600 focus:ring-2 focus:ring-blue-600/15 focus:outline-none transition-all"
            />
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Shipper facility, warehouse, or cross-dock loading dock</p>
        </div>

        {/* Field 3: Dropoff Location */}
        <div>
          <label htmlFor="dropoffLocation" className="block text-xs font-semibold text-slate-700 mb-1.5 uppercase tracking-wider flex items-center justify-between">
            <span>Dropoff Location (Consignee)</span>
            <span className="text-[11px] text-emerald-700 font-medium bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
              1 hr on-duty unload
            </span>
          </label>
          <div className="relative rounded-lg shadow-xs">
            <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400">
              <Flag className="h-4 w-4 text-emerald-600" />
            </div>
            <input
              type="text"
              id="dropoffLocation"
              name="dropoffLocation"
              required
              value={formData.dropoffLocation}
              onChange={onChange}
              placeholder="e.g. Atlanta, GA"
              className="block w-full rounded-lg border border-slate-300 py-2.5 pl-9 pr-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-600 focus:ring-2 focus:ring-blue-600/15 focus:outline-none transition-all"
            />
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Final delivery destination or receiver location</p>
        </div>

        {/* Field 4: Current Cycle Used (Hours) */}
        <div className="pt-1">
          <div className="flex items-center justify-between mb-1.5">
            <label htmlFor="cycleHoursUsed" className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
              Current Cycle Used (Hours)
            </label>
            <span className="text-xs font-medium text-slate-500">
              <strong className="text-slate-800">{remainingCycle} hrs</strong> remaining in 70h/8d cycle
            </span>
          </div>

          <div className="relative rounded-lg shadow-xs">
            <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400">
              <Clock className="h-4 w-4 text-slate-500" />
            </div>
            <input
              type="number"
              id="cycleHoursUsed"
              name="cycleHoursUsed"
              min="0"
              max="70"
              step="0.5"
              required
              value={formData.cycleHoursUsed}
              onChange={onChange}
              placeholder="24.0"
              className="block w-full rounded-lg border border-slate-300 py-2.5 pl-9 pr-14 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-600 focus:ring-2 focus:ring-blue-600/15 focus:outline-none transition-all"
            />
            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3 text-xs text-slate-400 font-medium">
              / 70 hrs
            </div>
          </div>

          {/* Range Slider for Cycle */}
          <div className="mt-2">
            <input
              type="range"
              min="0"
              max="70"
              step="0.5"
              value={currentCycle}
              onChange={(e) => onChange({ target: { name: 'cycleHoursUsed', value: parseFloat(e.target.value) } })}
              className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
            />
            <div className="flex justify-between items-center text-[11px] text-slate-500 mt-1">
              <span>0 hrs (Fresh)</span>
              <span className="font-medium text-slate-700">{cyclePercent}% of 70h Used</span>
              <span>70.0 hrs (Limit)</span>
            </div>
          </div>
        </div>

        {/* Submit Button */}
        <div className="pt-2">
          <button
            type="submit"
            disabled={isPlanning}
            className="w-full inline-flex items-center justify-center gap-2 px-5 py-3 rounded-lg bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-semibold text-sm shadow-sm transition-all cursor-pointer disabled:opacity-75 disabled:cursor-not-allowed"
          >
            {isPlanning ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                <span>Calculating Route &amp; ELD Logs via Backend...</span>
              </>
            ) : (
              <>
                <span>Plan Route &amp; Generate ELD Logs</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
