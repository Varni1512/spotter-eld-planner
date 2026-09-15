import React from 'react';
import { Truck, RefreshCw, UserCheck } from 'lucide-react';
import { SAMPLE_PRESETS } from '../data/mockTripData';

export default function Header({ onSelectPreset, onReset, isPlanned }) {
  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between py-3.5 gap-3.5">
          
          {/* Logo & Application Title */}
          <div className="flex items-center gap-3.5">
            <div className="w-10 h-10 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-sm ring-1 ring-blue-700/20 shrink-0">
              <Truck className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-lg text-slate-900 tracking-tight">Spotter ELD</span>
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200/80">
                  Route Planner
                </span>
              </div>
              <p className="text-xs text-slate-500 font-normal">
                Commercial Fleet Trip Planning &amp; Hours of Service Preview
              </p>
            </div>
          </div>

          {/* Status & Quick Actions */}
          <div className="flex flex-wrap items-center gap-2 sm:gap-3 text-xs">
            {/* Driver & Unit status pill */}
            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-md bg-slate-50 border border-slate-200 text-slate-700">
              <UserCheck className="w-3.5 h-3.5 text-slate-500" />
              <span className="font-medium">Unit #408</span>
              <span className="text-slate-300">|</span>
              <span className="text-slate-600">J. Miller (Driver)</span>
            </div>

            {/* System Readiness */}
            <div className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-emerald-50 text-emerald-800 border border-emerald-200/70">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span className="font-medium">ELD Dispatch Ready</span>
            </div>

            {/* Preset Selector Dropdown */}
            <div className="flex items-center gap-1.5">
              <select
                aria-label="Load Sample Trip Preset"
                className="bg-white border border-slate-300 hover:border-slate-400 text-slate-700 rounded-md px-2.5 py-1.5 text-xs font-medium focus:ring-2 focus:ring-blue-500 focus:outline-none transition-colors cursor-pointer"
                defaultValue=""
                onChange={(e) => {
                  if (e.target.value !== "") {
                    const preset = SAMPLE_PRESETS[parseInt(e.target.value, 10)];
                    if (preset) onSelectPreset(preset);
                  }
                }}
              >
                <option value="" disabled>Load Sample Route...</option>
                {SAMPLE_PRESETS.map((p, idx) => (
                  <option key={idx} value={idx}>{p.name}</option>
                ))}
              </select>

              {isPlanned && (
                <button
                  type="button"
                  onClick={onReset}
                  title="Reset to blank form"
                  className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-md border border-slate-200 transition-colors"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                </button>
              )}
            </div>

          </div>

        </div>
      </div>
    </header>
  );
}
