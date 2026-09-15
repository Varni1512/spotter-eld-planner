import React, { useEffect, useRef } from 'react';
import { Map, Layers, Navigation2, Compass } from 'lucide-react';
import L from 'leaflet';

export default function RouteMap({
  isPlanned,
  routeGeometry,
  stops = [],
  summary,
  onPlanSample,
}) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const layerGroupRef = useRef(null);

  // Initialize Leaflet map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    const map = L.map(mapContainerRef.current, {
      center: [39.5, -98.35], // Geographic center of US
      zoom: 4,
      zoomControl: true,
      scrollWheelZoom: true,
    });

    // Clean, high-performance standard OpenStreetMap tiles (100% free, no API key required)
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(map);

    const layerGroup = L.layerGroup().addTo(map);
    mapInstanceRef.current = map;
    layerGroupRef.current = layerGroup;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Update map polyline and markers when data changes
  useEffect(() => {
    const map = mapInstanceRef.current;
    const layerGroup = layerGroupRef.current;
    if (!map || !layerGroup) return;

    layerGroup.clearLayers();

    const bounds = L.latLngBounds([]);

    // 1. Draw Real Route Polyline
    if (routeGeometry && routeGeometry.coordinates && routeGeometry.coordinates.length > 0) {
      // GeoJSON is [lon, lat], Leaflet requires [lat, lon]
      const latLngs = routeGeometry.coordinates.map(([lon, lat]) => [lat, lon]);

      // Outer glow line for high visibility
      L.polyline(latLngs, {
        color: '#60a5fa',
        weight: 6,
        opacity: 0.6,
        lineCap: 'round',
        lineJoin: 'round',
      }).addTo(layerGroup);

      // Core route line
      L.polyline(latLngs, {
        color: '#2563eb',
        weight: 3.5,
        opacity: 0.95,
        lineCap: 'round',
        lineJoin: 'round',
      }).addTo(layerGroup);

      latLngs.forEach((coord) => bounds.extend(coord));
    }

    // 2. Add Stop Markers
    if (stops && stops.length > 0) {
      stops.forEach((stop, index) => {
        if (!stop.coordinates || stop.coordinates.length < 2) return;
        const [lat, lon] = stop.coordinates;
        bounds.extend([lat, lon]);

        // Badge styling based on stop type
        let badgeBg = '#2563eb';
        let label = `${index + 1}`;
        let iconSymbol = `${index + 1}`;

        if (stop.stop_type === 'current_location') {
          badgeBg = '#1e293b';
          iconSymbol = 'A';
        } else if (stop.stop_type === 'pickup') {
          badgeBg = '#d97706';
          iconSymbol = 'P';
        } else if (stop.stop_type === 'dropoff') {
          badgeBg = '#059669';
          iconSymbol = 'D';
        } else if (stop.stop_type === 'fuel') {
          badgeBg = '#7c3aed';
          iconSymbol = '⛽';
        } else if (stop.stop_type === 'rest_break') {
          badgeBg = '#0284c7';
          iconSymbol = '☕';
        } else if (stop.stop_type === 'sleeper_rest' || stop.stop_type === 'restart_34h') {
          badgeBg = '#4338ca';
          iconSymbol = '🛏️';
        }

        const customIcon = L.divIcon({
          className: 'custom-leaflet-marker',
          html: `
            <div style="
              background-color: ${badgeBg};
              width: 30px;
              height: 30px;
              border-radius: 50%;
              display: flex;
              align-items: center;
              justify-content: center;
              color: #ffffff;
              font-weight: 700;
              font-size: 12px;
              font-family: sans-serif;
              box-shadow: 0 3px 8px rgba(0,0,0,0.3);
              border: 2px solid #ffffff;
              cursor: pointer;
            ">
              ${iconSymbol}
            </div>
          `,
          iconSize: [30, 30],
          iconAnchor: [15, 15],
          popupAnchor: [0, -16],
        });

        const marker = L.marker([lat, lon], { icon: customIcon }).addTo(layerGroup);

        const arrTime = stop.arrival_time
          ? new Date(stop.arrival_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          : '';
        const depTime = stop.departure_time
          ? new Date(stop.departure_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          : '';

        marker.bindPopup(`
          <div style="font-family: Inter, sans-serif; min-width: 200px; padding: 3px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
              <span style="font-size: 10px; font-weight: 700; background: ${badgeBg}; color: white; padding: 2px 6px; border-radius: 4px;">
                STOP #${index + 1}
              </span>
              <span style="font-size: 11px; color: #64748b; font-weight: 600;">
                Mile ${stop.mile_marker || 0}
              </span>
            </div>
            <div style="font-weight: 700; color: #0f172a; font-size: 13px; margin-bottom: 2px;">
              ${stop.name}
            </div>
            <div style="color: #475569; font-size: 11px; margin-bottom: 6px;">
              ${stop.location_name}
            </div>
            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 4px; padding: 4px 6px; font-size: 11px; color: #334155;">
              <div><strong>Status:</strong> ${stop.duty_status_display || stop.duty_status}</div>
              ${arrTime ? `<div><strong>Schedule:</strong> ${arrTime} – ${depTime} (${stop.duration_minutes}m)</div>` : ''}
              ${stop.reason ? `<div style="color: #64748b; margin-top: 2px;"><em>${stop.reason}</em></div>` : ''}
            </div>
          </div>
        `);
      });
    }

    if (bounds.isValid()) {
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 13 });
    } else {
      map.setView([39.5, -98.35], 4);
    }
  }, [routeGeometry, stops]);

  return (
    <div className="bg-white rounded-xl border border-slate-200/90 shadow-xs overflow-hidden">
      {/* Header Bar */}
      <div className="px-5 py-3.5 border-b border-slate-100 flex flex-wrap items-center justify-between gap-3 bg-white">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-700 flex items-center justify-center">
            <Map className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm sm:text-base font-semibold text-slate-900 leading-tight">
              Route Map &amp; Commercial Road Corridor
            </h2>
            <p className="text-xs text-slate-500">
              Real OpenStreetMap &amp; OSRM road geometry with FMCSA scheduled stops
            </p>
          </div>
        </div>

        {isPlanned && summary && (
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-pulse"></span>
              {summary.total_distance_miles} mi Calculated Route
            </span>
          </div>
        )}
      </div>

      {/* Map Content Canvas */}
      <div className="relative w-full h-[360px] sm:h-[420px] bg-slate-100">
        <div ref={mapContainerRef} className="w-full h-full" />

        {/* Bottom Legend */}
        {isPlanned && stops.length > 0 && (
          <div className="absolute bottom-3 left-3 z-[1000] bg-white/95 backdrop-blur-xs border border-slate-200/90 rounded-lg px-3 py-1.5 shadow-xs flex flex-wrap items-center gap-3 text-xs font-medium text-slate-700">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-slate-900"></span> Departure
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-600"></span> Pickup
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-purple-600"></span> Fuel
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-sky-600"></span> 30m Rest
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-indigo-700"></span> 10h Sleep
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-600"></span> Dropoff
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
