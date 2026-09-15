import React from 'react';
import { Navigation, ArrowRight, Clock, Building2, Flag, Sparkles } from 'lucide-react';

export default function TripForm({
  formData,
  onChange,
  onSubmit,
  onLoadDefault,
  isPlanning,
}) {
  const cycleLimit = 70.0;
  const currentCycle = parseFloat(formData.cycleHoursUsed) || 0;
  const remainingCycle = Math.max(0, cycleLimit - currentCycle).toFixed(1);
  const cyclePercent = Math.min(100, Math.round((currentCycle / cycleLimit) * 100));

  return (
    <div className="bg-white rounded-xl border border-slate-200/90 shadow-xs p-5 sm:p-6 transition-all">
      <div className="flex items-center justify-between pb-4 mb-5 border-b border-slate-100">
        <div>
          <h2 className="text-base sm:text-lg font-semibold text-slate-900 flex items-center gap-2">
            <span>Trip Parameters</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Enter dispatch locations and driver cycle hours to plan compliant route
          </p>
        </div>

        <button
          type="button"
          onClick={onLoadDefault}
          className="text-xs text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1 hover:underline py-1 px-2 rounded hover:bg-blue-50 transition-colors"
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>Fill Example</span>
        </button>
      </div>

      <form onSubmit={onSubmit} className="space-y-4">
        {/* Field 1: Current Driver Location */}
        <div>
          <label htmlFor="currentLocation" className="block text-xs font-semibold text-slate-700 mb-1.5 uppercase tracking-wider">
            Current Driver Location
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
              placeholder="e.g. Chicago, IL (Terminal 4 Yard)"
              className="block w-full rounded-lg border border-slate-300 py-2.5 pl-9 pr-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-600 focus:ring-2 focus:ring-blue-600/15 focus:outline-none transition-all"
            />
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Starting point or current terminal dispatch origin</p>
        </div>

        {/* Field 2: Pickup Location */}
        <div>
          <label htmlFor="pickupLocation" className="block text-xs font-semibold text-slate-700 mb-1.5 uppercase tracking-wider">
            Pickup Location (Shipper)
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
              placeholder="e.g. Indianapolis, IN (Apex Cold Storage)"
              className="block w-full rounded-lg border border-slate-300 py-2.5 pl-9 pr-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-600 focus:ring-2 focus:ring-blue-600/15 focus:outline-none transition-all"
            />
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Shipper facility, warehouse, or cross-dock loading dock</p>
        </div>

        {/* Field 3: Dropoff Location */}
        <div>
          <label htmlFor="dropoffLocation" className="block text-xs font-semibold text-slate-700 mb-1.5 uppercase tracking-wider">
            Dropoff Location (Consignee)
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
              placeholder="e.g. Nashville, TN (Mid-South Distribution Center)"
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
              placeholder="42.5"
              className="block w-full rounded-lg border border-slate-300 py-2.5 pl-9 pr-14 text-sm text-slate-900 placeholder:text-slate-400 focus:border-blue-600 focus:ring-2 focus:ring-blue-600/15 focus:outline-none transition-all"
            />
            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3 text-xs text-slate-400 font-medium">
              / 70 hrs
            </div>
          </div>

          {/* Cycle Meter Bar */}
          <div className="mt-2">
            <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden border border-slate-200">
              <div
                className={`h-full transition-all duration-300 rounded-full ${
                  cyclePercent > 85 ? 'bg-rose-500' : cyclePercent > 70 ? 'bg-amber-500' : 'bg-blue-600'
                }`}
                style={{ width: `${cyclePercent}%` }}
              ></div>
            </div>
            <div className="flex justify-between items-center text-[11px] text-slate-500 mt-1">
              <span>0 hrs</span>
              <span className="font-medium text-slate-700">{cyclePercent}% of 70-Hour Rule</span>
              <span>70.0 hrs</span>
            </div>
          </div>
        </div>

        {/* Submit Button */}
        <div className="pt-3">
          <button
            type="submit"
            disabled={isPlanning}
            className="w-full inline-flex items-center justify-center gap-2 px-5 py-3 rounded-lg bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-medium text-sm shadow-sm transition-all focus:ring-2 focus:ring-blue-600 focus:ring-offset-2 cursor-pointer disabled:opacity-75 disabled:cursor-not-allowed"
          >
            {isPlanning ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                <span>Calculating Optimal Route...</span>
              </>
            ) : (
              <>
                <span>Plan Route</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
