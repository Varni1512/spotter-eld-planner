import React, { useState } from 'react';
import Header from './components/Header';
import TripForm from './components/TripForm';
import TripSummary from './components/TripSummary';
import RouteMap from './components/RouteMap';
import StopsTimeline from './components/StopsTimeline';
import EldLogSection from './components/EldLogSection';
import { DEFAULT_TRIP } from './data/mockTripData';

function App() {
  const [formData, setFormData] = useState({
    currentLocation: DEFAULT_TRIP.currentLocation,
    pickupLocation: DEFAULT_TRIP.pickupLocation,
    dropoffLocation: DEFAULT_TRIP.dropoffLocation,
    cycleHoursUsed: DEFAULT_TRIP.cycleHoursUsed,
  });

  const [isPlanned, setIsPlanned] = useState(true);
  const [isPlanning, setIsPlanning] = useState(false);
  const [tripData, setTripData] = useState(DEFAULT_TRIP);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handlePlanRoute = (e) => {
    if (e && e.preventDefault) e.preventDefault();
    setIsPlanning(true);

    // Simulate realistic calculation delay for UI feedback
    setTimeout(() => {
      setIsPlanning(false);
      setIsPlanned(true);
      setTripData((prev) => ({
        ...prev,
        currentLocation: formData.currentLocation || prev.currentLocation,
        pickupLocation: formData.pickupLocation || prev.pickupLocation,
        dropoffLocation: formData.dropoffLocation || prev.dropoffLocation,
        cycleHoursUsed: parseFloat(formData.cycleHoursUsed) || prev.cycleHoursUsed,
      }));
    }, 450);
  };

  const handleSelectPreset = (preset) => {
    setFormData({
      currentLocation: preset.currentLocation,
      pickupLocation: preset.pickupLocation,
      dropoffLocation: preset.dropoffLocation,
      cycleHoursUsed: preset.cycleHoursUsed,
    });
    setIsPlanned(true);
  };

  const handleReset = () => {
    setFormData({
      currentLocation: '',
      pickupLocation: '',
      dropoffLocation: '',
      cycleHoursUsed: 0,
    });
    setIsPlanned(false);
  };

  const handleLoadDefault = () => {
    setFormData({
      currentLocation: DEFAULT_TRIP.currentLocation,
      pickupLocation: DEFAULT_TRIP.pickupLocation,
      dropoffLocation: DEFAULT_TRIP.dropoffLocation,
      cycleHoursUsed: DEFAULT_TRIP.cycleHoursUsed,
    });
    setIsPlanned(true);
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans selection:bg-blue-100 selection:text-blue-900">
      {/* 1. HEADER */}
      <Header
        onSelectPreset={handleSelectPreset}
        onReset={handleReset}
        isPlanned={isPlanned}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 space-y-7">
        
        {/* Top Notification / Orientation Banner */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white border border-slate-200/90 rounded-xl px-4 sm:px-5 py-3 shadow-2xs">
          <div className="flex items-center gap-3">
            <span className="flex h-2.5 w-2.5 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-blue-600"></span>
            </span>
            <p className="text-xs sm:text-sm text-slate-700">
              <strong>Active Trip Planner:</strong> Plan commercial truck runs with automatic HOS cycle checks and mandatory DOT rest stop scheduling.
            </p>
          </div>

          <div className="flex items-center gap-2 self-start sm:self-auto shrink-0">
            <span className="text-[11px] font-medium text-slate-500 bg-slate-100 px-2.5 py-1 rounded-md border border-slate-200">
              Commercial Routing Engine v2.4
            </span>
          </div>
        </div>

        {/* 2. TRIP PLANNING & 4. ROUTE MAP (Upper Grid) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          
          {/* Left Column: Trip Planning Form (5 columns on desktop) */}
          <div className="lg:col-span-5 w-full">
            <TripForm
              formData={formData}
              onChange={handleInputChange}
              onSubmit={handlePlanRoute}
              onLoadDefault={handleLoadDefault}
              isPlanning={isPlanning}
            />
          </div>

          {/* Right Column: Trip Summary & Route Map (7 columns on desktop) */}
          <div className="lg:col-span-7 w-full space-y-6">
            {/* 3. TRIP SUMMARY */}
            <TripSummary
              summary={tripData.summary}
              isPlanned={isPlanned}
            />

            {/* 4. ROUTE MAP SECTION */}
            <RouteMap
              isPlanned={isPlanned}
              onPlanSample={handleLoadDefault}
            />
          </div>

        </div>

        {/* 5. STOPS & TIMELINE SECTION */}
        <section aria-labelledby="stops-timeline-heading">
          <StopsTimeline
            stops={tripData.stops}
            isPlanned={isPlanned}
            onPlanSample={handleLoadDefault}
          />
        </section>

        {/* 6. DAILY ELD LOGS SECTION */}
        <section aria-labelledby="eld-logs-heading">
          <EldLogSection />
        </section>

      </main>

      {/* FOOTER */}
      <footer className="border-t border-slate-200 bg-white py-6 mt-12 text-slate-500 text-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-800">Spotter ELD</span>
            <span>• Fleet Route Planning &amp; Hours of Service Assistant</span>
          </div>
          <div className="text-slate-400 text-center sm:text-right">
            Designed for commercial motor vehicle operators &amp; dispatch operations
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
