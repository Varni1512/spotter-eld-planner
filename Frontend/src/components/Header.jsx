import React from 'react';
import { Truck, RefreshCw, UserCheck } from 'lucide-react';

export default function Header({ onReset, isPlanned, isBackendConnected }) {
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
                Hours of Service (HOS) route compliance &amp; automated daily driver logs
              </p>
            </div>
          </div>

          {/* Status & Actions */}
          <div className="flex flex-wrap items-center gap-2 sm:gap-3 text-xs">
            {/* Unit Info */}
            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-md bg-slate-50 border border-slate-200 text-slate-700">
              <UserCheck className="w-3.5 h-3.5 text-slate-500" />
              <span className="font-medium">Unit #TRK-408</span>
              <span className="text-slate-300">|</span>
              <span className="text-slate-600">Spotter Fleet Logistics</span>
            </div>

            {/* Backend connection status */}
            <div
              className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-md font-medium border ${
                isBackendConnected
                  ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                  : 'bg-amber-50 text-amber-800 border-amber-200'
              }`}
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  isBackendConnected ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'
                }`}
              ></span>
              <span>{isBackendConnected ? 'Backend Connected' : 'Connecting to API...'}</span>
            </div>

            {isPlanned && (
              <button
                type="button"
                onClick={onReset}
                title="Reset to blank form"
                className="flex items-center gap-1.5 px-2.5 py-1.5 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-md border border-slate-200 transition-colors cursor-pointer"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Reset</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
