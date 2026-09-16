import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import TripForm from './components/TripForm';
import TripSummary from './components/TripSummary';
import RouteMap from './components/RouteMap';
import StopsTimeline from './components/StopsTimeline';
import EldLogSection from './components/EldLogSection';
import { planTripApi, checkBackendHealth } from './services/api';
import { ROUTE_PRESETS } from './data/presets';

function App() {
  const [formData, setFormData] = useState({
    currentLocation: '',
    pickupLocation: '',
    dropoffLocation: '',
    cycleHoursUsed: 0,
  });

  const [isPlanned, setIsPlanned] = useState(false);
  const [isPlanning, setIsPlanning] = useState(false);
  const [isBackendConnected, setIsBackendConnected] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  // Real backend calculated state
  const [tripSummary, setTripSummary] = useState(null);
  const [routeGeometry, setRouteGeometry] = useState(null);
  const [stops, setStops] = useState([]);
  const [dailyLogs, setDailyLogs] = useState([]);
  const [validation, setValidation] = useState(null);

  // Check backend health on mount (do not automatically plan a route)
  useEffect(() => {
    checkBackendHealth()
      .then((res) => {
        if (res && res.status === 'ok') {
          setIsBackendConnected(true);
        }
      })
      .catch(() => setIsBackendConnected(false));
  }, []);

  const executePlanRoute = async (params) => {
    setIsPlanning(true);
    setErrorMessage(null);

    try {
      const data = await planTripApi(params);
      if (data && data.status === 'success') {
        setTripSummary(data.summary);
        setRouteGeometry(data.route_geometry);
        setStops(data.stops || []);
        setDailyLogs(data.daily_logs || []);
        setValidation(data.validation || null);
        setIsPlanned(true);
        setIsBackendConnected(true);
      } else {
        throw new Error(data.error || 'Trip planning calculation failed.');
      }
    } catch (err) {
      console.error('Plan route error:', err);
      setErrorMessage(
        err.message ||
          'Failed to connect to the backend server. Please verify the Django backend is running at http://127.0.0.1:8000/'
      );
    } finally {
      setIsPlanning(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handlePlanRoute = (e) => {
    if (e && e.preventDefault) e.preventDefault();
    executePlanRoute(formData);
  };

  const handleSelectPreset = (preset) => {
    const newForm = {
      currentLocation: preset.currentLocation,
      pickupLocation: preset.pickupLocation,
      dropoffLocation: preset.dropoffLocation,
      cycleHoursUsed: preset.cycleHoursUsed,
    };
    setFormData(newForm);
    executePlanRoute(newForm);
  };

  const handleReset = () => {
    setFormData({
      currentLocation: '',
      pickupLocation: '',
      dropoffLocation: '',
      cycleHoursUsed: 0,
    });
    setTripSummary(null);
    setRouteGeometry(null);
    setStops([]);
    setDailyLogs([]);
    setValidation(null);
    setIsPlanned(false);
  };

  const isCompliant = validation ? validation.passed : true;

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans selection:bg-blue-100 selection:text-blue-900">
      {/* 1. HEADER */}
      <Header
        onReset={handleReset}
        isPlanned={isPlanned}
        isBackendConnected={isBackendConnected}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 space-y-7">
        {/* Top Notification / Orientation Banner */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white border border-slate-200/90 rounded-xl px-4 sm:px-5 py-3 shadow-2xs">
          <div className="flex items-center gap-3">
            <span className="flex h-2.5 w-2.5 relative">
              <span
                className={`animate-ping absolute inline-flex h-full w-full rounded-full ${
                  isBackendConnected ? 'bg-emerald-400 opacity-75' : 'bg-blue-400 opacity-75'
                }`}
              ></span>
              <span
                className={`relative inline-flex rounded-full h-2.5 w-2.5 ${
                  isBackendConnected ? 'bg-emerald-600' : 'bg-blue-600'
                }`}
              ></span>
            </span>
            <p className="text-xs sm:text-sm text-slate-700">
              <strong>Planned Trip (Simulation Mode):</strong> Real road geometry via OSRM, automated FMCSA Hours of Service scheduling, and 24.0-hour daily log generation.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 self-start sm:self-auto shrink-0">
            <span className="text-[11px] font-semibold text-slate-700 bg-slate-100 px-2.5 py-1 rounded-md border border-slate-200">
              Simulation Mode
            </span>
            <span className={`text-[11px] font-semibold px-2.5 py-1 rounded-md border ${
              isCompliant
                ? 'text-emerald-700 bg-emerald-50 border-emerald-200'
                : 'text-rose-700 bg-rose-50 border-rose-200'
            }`}>
              {validation?.compliance_status || '49 CFR § 395 Verified'}
            </span>
          </div>
        </div>

        {/* 2. TRIP PLANNING & 3. ROUTE MAP */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Trip Planning Form (5 columns on desktop) */}
          <div className="lg:col-span-5 w-full">
            <TripForm
              formData={formData}
              onChange={handleInputChange}
              onSubmit={handlePlanRoute}
              onSelectPreset={handleSelectPreset}
              isPlanning={isPlanning}
              errorMessage={errorMessage}
            />
          </div>

          {/* Right Column: Trip Summary & Route Map (7 columns on desktop) */}
          <div className="lg:col-span-7 w-full space-y-6">
            {/* TRIP SUMMARY */}
            <TripSummary
              summary={tripSummary}
              isPlanned={isPlanned}
              validation={validation}
            />

            {/* ROUTE MAP SECTION */}
            <RouteMap
              isPlanned={isPlanned}
              routeGeometry={routeGeometry}
              stops={stops}
              summary={tripSummary}
              onPlanSample={() => handleSelectPreset(ROUTE_PRESETS[0])}
            />
          </div>
        </div>

        {/* 4. STOPS & SCHEDULE TIMELINE SECTION */}
        <section aria-labelledby="stops-timeline-heading">
          <StopsTimeline
            stops={stops}
            isPlanned={isPlanned}
          />
        </section>

        {/* 5. DAILY ELD LOGS SECTION */}
        <section aria-labelledby="eld-logs-heading">
          <EldLogSection
            dailyLogs={dailyLogs}
            isPlanned={isPlanned}
            validation={validation}
          />
        </section>
      </main>

      {/* FOOTER */}
      <footer className="border-t border-slate-200 bg-white py-6 mt-12 text-slate-500 text-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-800">Spotter ELD</span>
            <span>• Fleet Route Planning &amp; FMCSA Hours of Service Assistant</span>
          </div>
          <div className="text-slate-400 text-center sm:text-right">
            OpenStreetMap &bull; OSRM Engine &bull; Property-Carrying 70h/8d Standard
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
