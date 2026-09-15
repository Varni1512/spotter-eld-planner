import React from 'react';
import { FileText, Clock, Info, CheckCircle } from 'lucide-react';

export default function EldLogSection() {

  return (
    <div className="bg-white rounded-xl border border-slate-200/90 shadow-xs overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-slate-100 text-slate-700 flex items-center justify-center">
            <FileText className="w-5 h-5 text-blue-600" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-semibold text-slate-900">
                Daily ELD Driver Log Sheet
              </h2>
              <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                Preview Placeholder
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Standard 24-hour graphical duty status grid &amp; hours recap
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="inline-flex items-center gap-1.5 text-xs font-medium text-amber-800 bg-amber-50 px-2.5 py-1 rounded-md border border-amber-200/80">
            <Info className="w-3.5 h-3.5 text-amber-600 shrink-0" />
            <span>Pending Backend HOS Integration</span>
          </div>
        </div>
      </div>

      <div className="p-5 sm:p-6 space-y-6">
        {/* Notice Card */}
        <div className="bg-blue-50/60 border border-blue-100 rounded-xl p-4 text-xs text-slate-600 flex flex-col sm:flex-row gap-3 items-start sm:items-center justify-between">
          <div className="space-y-1">
            <p className="font-semibold text-blue-900">
              Automated 24-Hour Driver Logs Will Appear Here
            </p>
            <p className="text-slate-600 leading-relaxed">
              Once route calculation and HOS rules are integrated with the backend, this section will automatically render driver log sheets with graph grids, duty totals, and recap hours for every day of your trip.
            </p>
          </div>
          <div className="text-[11px] font-mono text-blue-700 bg-white px-2.5 py-1.5 rounded border border-blue-200 shrink-0">
            49 CFR §395 Format
          </div>
        </div>

        {/* Visual 24-Hour ELD Grid Wireframe Placeholder */}
        <div className="border border-slate-200 rounded-xl p-4 sm:p-5 bg-slate-50/50">
          <div className="flex items-center justify-between mb-3 text-xs">
            <span className="font-semibold text-slate-700 uppercase tracking-wider">
              24-Hour Duty Status Graph Grid (Preview Wireframe)
            </span>
            <span className="text-slate-500 font-mono">
              Date: YYYY-MM-DD • Day 1 of Trip
            </span>
          </div>

          {/* Grid Container */}
          <div className="overflow-x-auto">
            <div className="min-w-[640px] border border-slate-300 rounded-lg bg-white p-3 select-none">
              
              {/* Hours Header Row */}
              <div className="grid grid-cols-24 border-b border-slate-200 pb-1 text-[10px] font-mono text-slate-400 text-center">
                {Array.from({ length: 24 }).map((_, i) => (
                  <div key={i} className="border-r border-slate-100 last:border-r-0">
                    {i === 0 ? 'M' : i === 12 ? 'N' : i % 2 === 0 ? i : ''}
                  </div>
                ))}
              </div>

              {/* 4 Standard FMCSA Status Rows */}
              <div className="space-y-0 text-xs">
                {/* Row 1: Off Duty */}
                <div className="flex items-center border-b border-slate-200 py-1.5">
                  <div className="w-24 shrink-0 font-semibold text-slate-700 text-[11px] pl-1">
                    1. OFF DUTY
                  </div>
                  <div className="flex-1 relative h-6 bg-slate-50/60 rounded flex items-center">
                    <div className="absolute inset-0 grid grid-cols-24 pointer-events-none opacity-20">
                      {Array.from({ length: 24 }).map((_, i) => (
                        <div key={i} className="border-r border-slate-400 h-full"></div>
                      ))}
                    </div>
                    {/* Placeholder illustrative wireframe bar */}
                    <div className="h-1.5 w-[25%] bg-slate-300 rounded-full mx-1"></div>
                  </div>
                  <div className="w-16 text-right font-mono text-xs text-slate-500 pr-2">
                    -- hrs
                  </div>
                </div>

                {/* Row 2: Sleeper Berth */}
                <div className="flex items-center border-b border-slate-200 py-1.5">
                  <div className="w-24 shrink-0 font-semibold text-slate-700 text-[11px] pl-1">
                    2. SLEEPER
                  </div>
                  <div className="flex-1 relative h-6 bg-slate-50/60 rounded flex items-center">
                    <div className="absolute inset-0 grid grid-cols-24 pointer-events-none opacity-20">
                      {Array.from({ length: 24 }).map((_, i) => (
                        <div key={i} className="border-r border-slate-400 h-full"></div>
                      ))}
                    </div>
                    <div className="h-1.5 w-[15%] bg-slate-200 rounded-full ml-[60%]"></div>
                  </div>
                  <div className="w-16 text-right font-mono text-xs text-slate-500 pr-2">
                    -- hrs
                  </div>
                </div>

                {/* Row 3: Driving */}
                <div className="flex items-center border-b border-slate-200 py-1.5">
                  <div className="w-24 shrink-0 font-semibold text-blue-800 text-[11px] pl-1">
                    3. DRIVING
                  </div>
                  <div className="flex-1 relative h-6 bg-blue-50/40 rounded flex items-center">
                    <div className="absolute inset-0 grid grid-cols-24 pointer-events-none opacity-20">
                      {Array.from({ length: 24 }).map((_, i) => (
                        <div key={i} className="border-r border-slate-400 h-full"></div>
                      ))}
                    </div>
                    {/* Placeholder driving timeline line */}
                    <div className="h-2 w-[40%] bg-blue-400/60 rounded-full ml-[26%]"></div>
                  </div>
                  <div className="w-16 text-right font-mono text-xs text-blue-700 font-semibold pr-2">
                    -- hrs
                  </div>
                </div>

                {/* Row 4: On Duty (Not Driving) */}
                <div className="flex items-center py-1.5">
                  <div className="w-24 shrink-0 font-semibold text-slate-700 text-[11px] pl-1">
                    4. ON DUTY
                  </div>
                  <div className="flex-1 relative h-6 bg-slate-50/60 rounded flex items-center">
                    <div className="absolute inset-0 grid grid-cols-24 pointer-events-none opacity-20">
                      {Array.from({ length: 24 }).map((_, i) => (
                        <div key={i} className="border-r border-slate-400 h-full"></div>
                      ))}
                    </div>
                    <div className="h-1.5 w-[10%] bg-amber-300 rounded-full ml-[10%]"></div>
                  </div>
                  <div className="w-16 text-right font-mono text-xs text-slate-500 pr-2">
                    -- hrs
                  </div>
                </div>
              </div>

              {/* Total Summary Footer */}
              <div className="border-t border-slate-200 mt-2 pt-2 flex items-center justify-between text-[11px] text-slate-500">
                <div className="flex items-center gap-4">
                  <span>Cycle Type: <strong>70 Hours / 8 Days</strong></span>
                  <span>Mandatory 30-min break: <strong>Scheduled</strong></span>
                </div>
                <div className="font-mono text-slate-700 font-semibold">
                  Total Calculated: 24.0 Hours
                </div>
              </div>

            </div>
          </div>

          <p className="text-[11px] text-slate-400 mt-2 text-center italic">
            Visual mockup wireframe showing standard FMCSA 4-tier duty status charting format.
          </p>
        </div>

        {/* Feature Capabilities Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5 pt-1">
          <div className="bg-slate-50 rounded-lg p-3.5 border border-slate-200/80">
            <div className="text-xs font-semibold text-slate-800 flex items-center gap-1.5 mb-1">
              <Clock className="w-3.5 h-3.5 text-blue-600" />
              <span>11-Hour Driving Rule</span>
            </div>
            <p className="text-[11px] text-slate-500 leading-relaxed">
              Monitors continuous driving hours after 10 consecutive hours off duty to prevent exceeding commercial drive limits.
            </p>
          </div>

          <div className="bg-slate-50 rounded-lg p-3.5 border border-slate-200/80">
            <div className="text-xs font-semibold text-slate-800 flex items-center gap-1.5 mb-1">
              <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
              <span>30-Min DOT Break Tracking</span>
            </div>
            <p className="text-[11px] text-slate-500 leading-relaxed">
              Verifies that a 30-minute consecutive rest or meal break is inserted before reaching 8 cumulative hours of driving.
            </p>
          </div>

          <div className="bg-slate-50 rounded-lg p-3.5 border border-slate-200/80">
            <div className="text-xs font-semibold text-slate-800 flex items-center gap-1.5 mb-1">
              <FileText className="w-3.5 h-3.5 text-indigo-600" />
              <span>Inspector-Ready PDF Export</span>
            </div>
            <p className="text-[11px] text-slate-500 leading-relaxed">
              Will allow drivers and safety managers to export compliant daily logs for roadside DOT inspections and safety audits.
            </p>
          </div>
        </div>

        {/* Non-compliance disclaimer */}
        <div className="text-center pt-2 text-[11px] text-slate-400">
          Disclaimer: This application is currently in development. It does not certify official FMCSA compliance until certified by the registry.
        </div>
      </div>
    </div>
  );
}
