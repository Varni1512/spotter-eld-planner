import React from 'react';
import { Map, ZoomIn, ZoomOut, Navigation2, Compass } from 'lucide-react';

export default function RouteMap({ isPlanned, onPlanSample }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200/90 shadow-xs overflow-hidden">
      {/* Header bar */}
      <div className="px-5 py-3.5 border-b border-slate-100 flex flex-wrap items-center justify-between gap-3 bg-white">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-slate-100 text-slate-700 flex items-center justify-center">
            <Map className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm sm:text-base font-semibold text-slate-900 leading-tight">
              Route Map &amp; Commercial Corridor
            </h2>
            <p className="text-xs text-slate-500">
              Commercial vehicle routing with bridge clearances and truck weight limits
            </p>
          </div>
        </div>

        {/* Map controls & status */}
        <div className="flex items-center gap-2">
          {isPlanned && (
            <span className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-600"></span>
              I-65 Corridor Active
            </span>
          )}
          <div className="flex items-center rounded-lg border border-slate-200 bg-slate-50 p-0.5 text-slate-600">
            <button
              type="button"
              className="p-1.5 hover:bg-white hover:text-slate-900 rounded transition-colors"
              title="Zoom In (Preview)"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              className="p-1.5 hover:bg-white hover:text-slate-900 rounded transition-colors"
              title="Zoom Out (Preview)"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Map Content Canvas */}
      <div className="relative w-full h-[320px] sm:h-[380px] bg-slate-100/80 flex items-center justify-center overflow-hidden select-none">
        
        {/* Subtle grid pattern background */}
        <div
          className="absolute inset-0 opacity-[0.45]"
          style={{
            backgroundImage: `radial-gradient(#94a3b8 1px, transparent 1px), radial-gradient(#94a3b8 1px, #f8fafc 1px)`,
            backgroundSize: '24px 24px',
            backgroundPosition: '0 0, 12px 12px',
          }}
        ></div>

        {/* State border / geography subtle contour lines (mock cartography) */}
        <svg
          className="absolute inset-0 w-full h-full pointer-events-none opacity-25"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M -20,140 Q 180,110 320,160 T 700,120 T 1200,150"
            fill="none"
            stroke="#64748b"
            strokeWidth="1.5"
            strokeDasharray="4,4"
          />
          <path
            d="M 280,-20 Q 300,180 340,320 T 360,500"
            fill="none"
            stroke="#64748b"
            strokeWidth="1.5"
            strokeDasharray="4,4"
          />
          <path
            d="M 680,-20 Q 640,160 620,380"
            fill="none"
            stroke="#64748b"
            strokeWidth="1.5"
            strokeDasharray="4,4"
          />
        </svg>

        {isPlanned ? (
          /* Planned Route Visualization */
          <div className="relative w-full h-full p-4 sm:p-6 flex flex-col justify-between z-10">
            {/* Top map overlay tags */}
            <div className="flex justify-between items-start">
              <div className="bg-white/95 backdrop-blur-xs border border-slate-200/90 rounded-lg p-2.5 shadow-xs text-xs space-y-1 max-w-xs">
                <div className="font-semibold text-slate-900 flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                  Truck Route Verified
                </div>
                <div className="text-slate-600 text-[11px] leading-tight">
                  STAA Highway Network • 53ft Trailer Approved • No Low Clearance Obstacles
                </div>
              </div>

              {/* Highway corridor badge */}
              <div className="bg-slate-900 text-white text-xs font-mono font-semibold px-2.5 py-1.5 rounded-md shadow-xs flex items-center gap-2 border border-slate-700">
                <div className="w-4 h-4 rounded bg-blue-600 text-[10px] font-bold flex items-center justify-center text-white">
                  65
                </div>
                <span>I-65 S Corridor (478.4 mi)</span>
              </div>
            </div>

            {/* Schematic Route Line SVG */}
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <svg
                viewBox="0 0 900 320"
                className="w-full h-full max-w-4xl"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                {/* Secondary road network faint lines */}
                <path d="M 120 70 L 220 180 L 360 210" stroke="#cbd5e1" strokeWidth="2" strokeDasharray="3,3" />
                <path d="M 450 140 L 590 80 L 780 120" stroke="#cbd5e1" strokeWidth="2" strokeDasharray="3,3" />
                <path d="M 380 270 L 560 220 L 720 280" stroke="#cbd5e1" strokeWidth="2" strokeDasharray="3,3" />

                {/* Main Highway Route Glow / Casing */}
                <path
                  d="M 140 85 C 240 100, 310 160, 420 175 C 530 190, 600 230, 760 250"
                  stroke="#93c5fd"
                  strokeWidth="8"
                  strokeLinecap="round"
                  opacity="0.6"
                />

                {/* Main Route Path Line */}
                <path
                  d="M 140 85 C 240 100, 310 160, 420 175 C 530 190, 600 230, 760 250"
                  stroke="#2563eb"
                  strokeWidth="4"
                  strokeLinecap="round"
                />

                {/* Mile markers along corridor */}
                <circle cx="280" cy="135" r="3" fill="#1e40af" />
                <circle cx="580" cy="205" r="3" fill="#1e40af" />

                {/* Node 1: Origin (Chicago) */}
                <g transform="translate(140, 85)">
                  <circle r="12" fill="#2563eb" fillOpacity="0.2" />
                  <circle r="7" fill="#2563eb" stroke="#ffffff" strokeWidth="2.5" />
                  <rect x="-42" y="-32" width="84" height="20" rx="4" fill="#0f172a" />
                  <text x="0" y="-18" fill="#ffffff" fontSize="10" fontWeight="600" textAnchor="middle" fontFamily="Inter, sans-serif">
                    Chicago, IL
                  </text>
                </g>

                {/* Node 2: Pickup (Indianapolis) */}
                <g transform="translate(360, 165)">
                  <circle r="12" fill="#d97706" fillOpacity="0.2" />
                  <circle r="7" fill="#d97706" stroke="#ffffff" strokeWidth="2.5" />
                  <rect x="-48" y="-32" width="96" height="20" rx="4" fill="#78350f" />
                  <text x="0" y="-18" fill="#ffffff" fontSize="10" fontWeight="600" textAnchor="middle" fontFamily="Inter, sans-serif">
                    Pickup (Indy)
                  </text>
                </g>

                {/* Node 3: Fuel Stop (Columbus) */}
                <g transform="translate(480, 185)">
                  <circle r="10" fill="#7c3aed" fillOpacity="0.2" />
                  <circle r="6" fill="#7c3aed" stroke="#ffffff" strokeWidth="2" />
                  <rect x="-35" y="16" width="70" height="18" rx="4" fill="#4c1d95" />
                  <text x="0" y="29" fill="#ffffff" fontSize="9" fontWeight="600" textAnchor="middle" fontFamily="Inter, sans-serif">
                    Fuel (Exit 68)
                  </text>
                </g>

                {/* Node 4: DOT Rest (Bowling Green) */}
                <g transform="translate(630, 230)">
                  <circle r="10" fill="#0284c7" fillOpacity="0.2" />
                  <circle r="6" fill="#0284c7" stroke="#ffffff" strokeWidth="2" />
                  <rect x="-40" y="-30" width="80" height="18" rx="4" fill="#075985" />
                  <text x="0" y="-17" fill="#ffffff" fontSize="9" fontWeight="600" textAnchor="middle" fontFamily="Inter, sans-serif">
                    DOT Break (KY)
                  </text>
                </g>

                {/* Node 5: Destination (Nashville) */}
                <g transform="translate(760, 250)">
                  <circle r="14" fill="#059669" fillOpacity="0.25" />
                  <circle r="8" fill="#059669" stroke="#ffffff" strokeWidth="2.5" />
                  <rect x="-48" y="-34" width="96" height="22" rx="4" fill="#064e3b" />
                  <text x="0" y="-19" fill="#ffffff" fontSize="10" fontWeight="600" textAnchor="middle" fontFamily="Inter, sans-serif">
                    Nashville, TN
                  </text>
                </g>
              </svg>
            </div>

            {/* Bottom map legend & info */}
            <div className="flex flex-wrap items-center justify-between gap-2 z-20">
              <div className="bg-white/95 backdrop-blur-xs border border-slate-200/90 rounded-lg px-3 py-1.5 shadow-xs flex items-center gap-4 text-xs font-medium text-slate-700">
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-blue-600"></span> Departure
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-600"></span> Shipper
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-purple-600"></span> Fuel
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-sky-600"></span> DOT Rest
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-600"></span> Consignee
                </span>
              </div>

              <div className="text-[11px] text-slate-500 bg-white/90 px-2.5 py-1 rounded border border-slate-200/80">
                Vector Cartography Preview • Commercial Profile: 80,000 lbs GVWR
              </div>
            </div>
          </div>
        ) : (
          /* Clean Empty State */
          <div className="text-center p-6 max-w-md z-10">
            <div className="w-12 h-12 rounded-xl bg-white border border-slate-200 shadow-xs flex items-center justify-center mx-auto text-slate-400 mb-3">
              <Compass className="w-6 h-6 text-blue-500" />
            </div>
            <h3 className="text-base font-semibold text-slate-900 mb-1">
              Interactive Route Map Visualization
            </h3>
            <p className="text-xs text-slate-500 leading-relaxed mb-4">
              Enter driver origin, pickup, dropoff locations, and cycle hours in the trip form, then click <strong>"Plan Route"</strong> to generate the commercial route visualization, waypoints, and interstate corridor geometry.
            </p>
            <button
              type="button"
              onClick={onPlanSample}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 text-xs font-medium shadow-2xs transition-colors cursor-pointer"
            >
              <Navigation2 className="w-3.5 h-3.5 text-blue-600" />
              <span>Preview Sample Route Map</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
