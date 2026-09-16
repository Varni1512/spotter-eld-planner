import React, { useState } from 'react';
import {
  FileText,
  Calendar,
  Printer,
  Download,
  CheckCircle2,
  ShieldCheck,
  AlertTriangle,
  Clock,
  Edit3,
  Check,
  Plus,
  Info,
  HelpCircle,
  XCircle,
  Eye
} from 'lucide-react';
import { validateLogApi } from '../services/api';

export default function EldLogSection({ dailyLogs = [], isPlanned, validation }) {
  const [selectedDayIndex, setSelectedDayIndex] = useState(0);

  // Driver Review Workflow states: 'GENERATED' -> 'EDITING' -> 'APPROVED'
  const [reviewState, setReviewState] = useState('GENERATED');
  const [approvedTimestamps, setApprovedTimestamps] = useState({});
  const [isEditingRemarks, setIsEditingRemarks] = useState(false);
  const [newRemarkText, setNewRemarkText] = useState('');
  const [newRemarkTime, setNewRemarkTime] = useState('12:00');
  const [newRemarkStatus, setNewRemarkStatus] = useState('On Duty (Not Driving)');
  const [customRemarksByDay, setCustomRemarksByDay] = useState({});
  const [hoveredSegment, setHoveredSegment] = useState(null);
  const [validationAlert, setValidationAlert] = useState(null);

  if (!isPlanned || !dailyLogs || dailyLogs.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-slate-200/90 shadow-xs p-6 text-center">
        <div className="w-12 h-12 rounded-xl bg-slate-50 border border-slate-200 text-slate-400 flex items-center justify-center mx-auto mb-3">
          <FileText className="w-6 h-6 text-slate-400" />
        </div>
        <h3 className="text-sm font-semibold text-slate-900">Daily ELD Driver Log Sheets (RODS)</h3>
        <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
          Once your trip route is planned, 24-hour midnight-to-midnight paper log sheets will be generated with the FMCSA 4-tier grid, step lines, and 70-hour recap for every day of the trip.
        </p>
      </div>
    );
  }

  const currentLog = dailyLogs[selectedDayIndex] || dailyLogs[0];
  const hours = currentLog.duty_hours || { off_duty: 0, sleeper_berth: 0, driving: 0, on_duty_not_driving: 0, total: 24.0 };
  const recap = currentLog.recap || { line_a_on_duty_today: 0, line_b_total_last_7_days: 0, line_c_available_tomorrow: 70 };
  const logValidation = currentLog.validation || { status: 'VALIDATED', errors: [], is_complete_24h: true };

  const dayNumber = currentLog.day_number;
  const isDayApproved = !!approvedTimestamps[dayNumber];
  const customRemarks = customRemarksByDay[dayNumber] || [];
  const displayRemarks = [...(currentLog.remarks || []), ...customRemarks];

  const hasDailyDrivingViolation = (hours.driving > 11.001);
  const hasGlobalViolations = validation ? !validation.passed : false;
  const isCompliant = !hasGlobalViolations && !hasDailyDrivingViolation && logValidation.status !== 'VIOLATION';
  const isWarningState = isCompliant && (validation?.status_type === 'WARNING' || validation?.has_sufficient_history === false || recap?.has_sufficient_history === false);
  const complianceStatusText = validation?.compliance_status || (
    isCompliant
      ? (isWarningState ? 'Generated Trip Validated — Historical 70/8 Data Required' : 'HOS Plan Validated')
      : 'Compliance Issue Detected'
  );
  const canApprove = isCompliant;

  let approvalBlockReason = null;
  if (hasDailyDrivingViolation) {
    approvalBlockReason = `Daily driving limit exceeded on Day ${dayNumber} (${hours.driving} hrs > 11.0 hrs limit).`;
  } else if (hasGlobalViolations) {
    const v = validation?.violations?.[0];
    approvalBlockReason = v ? `${v.message}` : "Active HOS violations exist in trip schedule.";
  } else if (logValidation.status === 'VIOLATION') {
    approvalBlockReason = "Daily log validation error detected.";
  }

  const handlePrint = () => {
    window.print();
  };

  const handleDownloadSvg = () => {
    if (!currentLog.svg_markup) return;
    const blob = new Blob([currentLog.svg_markup], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `Spotter_ELD_Log_Day_${currentLog.day_number}_${currentLog.formatted_date.replace(/\//g, '-')}.svg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleApproveDay = () => {
    if (!canApprove) {
      setValidationAlert(approvalBlockReason || "Cannot approve log: Active HOS compliance issues or invalid daily hours exist.");
      return;
    }
    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    setApprovedTimestamps((prev) => ({
      ...prev,
      [dayNumber]: timeStr,
    }));
    setReviewState('APPROVED');
    setValidationAlert(null);
  };

  const handleAddRemark = (e) => {
    e.preventDefault();
    if (!newRemarkText.trim()) return;

    const newRemark = {
      time: newRemarkTime,
      location: currentLog.origin || 'En Route',
      duty_status: newRemarkStatus,
      remark: newRemarkText.trim(),
    };

    setCustomRemarksByDay((prev) => ({
      ...prev,
      [dayNumber]: [...(prev[dayNumber] || []), newRemark],
    }));

    setNewRemarkText('');
    setIsEditingRemarks(false);
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200/90 shadow-xs overflow-hidden print:border-none print:shadow-none">
      {/* 1. Header Bar with Simulation Mode Banner */}
      <div className="px-5 py-4 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-blue-50 text-blue-700 flex items-center justify-center shrink-0">
            <FileText className="w-5 h-5" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-base font-semibold text-slate-900">
                Driver's Daily Log (24 Hours • 49 CFR § 395.8)
              </h2>
              {/* Prominent Simulation / Planned Mode Indicator */}
              <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-sky-50 text-sky-700 border border-sky-200">
                Planned Log — Simulation Mode
              </span>

              {/* Synchronized HOS Validation Badge */}
              <span
                className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full border flex items-center gap-1 ${
                  !isCompliant
                    ? 'bg-rose-50 text-rose-700 border-rose-200'
                    : isWarningState
                    ? 'bg-amber-50 text-amber-800 border-amber-300'
                    : 'bg-emerald-50 text-emerald-700 border-emerald-200'
                }`}
              >
                {!isCompliant ? (
                  <AlertTriangle className="w-3 h-3 text-rose-600" />
                ) : isWarningState ? (
                  <AlertTriangle className="w-3 h-3 text-amber-600" />
                ) : (
                  <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                )}
                <span>{complianceStatusText}</span>
              </span>

              {isDayApproved ? (
                <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                  <span>Driver Approved ({approvedTimestamps[dayNumber]})</span>
                </span>
              ) : (
                <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200">
                  Awaiting Driver Review
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Deterministic 4-tier grid, 15-min sub-intervals, duty transitions &amp; rolling 70h/8d recap
            </p>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2 print:hidden">
          <button
            type="button"
            onClick={handlePrint}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-xs font-semibold text-slate-700 transition cursor-pointer"
            title="Print Log Sheet"
          >
            <Printer className="w-3.5 h-3.5" />
            <span>Print Sheet</span>
          </button>
          <button
            type="button"
            onClick={handleDownloadSvg}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-blue-200 bg-blue-50 hover:bg-blue-100/80 text-xs font-semibold text-blue-700 transition cursor-pointer"
            title="Download Vector SVG"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export SVG</span>
          </button>
        </div>
      </div>

      {/* 2. Driver Review Workflow Control Panel */}
      <div className="bg-slate-900 text-white px-5 py-3 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs print:hidden">
        <div className="flex items-center gap-2.5">
          <span className="font-semibold text-slate-200 flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-blue-400" />
            Driver Review Workflow:
          </span>
          <span className="text-slate-400">
            Day {currentLog.day_number} of {dailyLogs.length} • {currentLog.date_display || currentLog.formatted_date}
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => setIsEditingRemarks(!isEditingRemarks)}
            className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition flex items-center gap-1 cursor-pointer"
          >
            <Edit3 className="w-3.5 h-3.5" />
            <span>{isEditingRemarks ? 'Cancel Remark' : 'Add Remark'}</span>
          </button>

          {!isDayApproved ? (
            <div className="flex flex-wrap items-center gap-2">
              {approvalBlockReason ? (
                <span className="text-[11px] text-rose-300 bg-rose-950/70 border border-rose-800/80 px-2.5 py-1 rounded flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                  <span>{approvalBlockReason}</span>
                </span>
              ) : isWarningState ? (
                <span
                  className="text-[11px] text-amber-200 bg-amber-950/70 border border-amber-700/80 px-2.5 py-1 rounded flex items-center gap-1.5"
                  title="Daily driving and generated-trip rules were validated. Full 70/8 cycle compliance requires prior 7-day driver logs."
                >
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                  <span>Note: Generated trip history only (Prior 7-day logs required for full cycle)</span>
                </span>
              ) : null}
              <button
                type="button"
                onClick={handleApproveDay}
                disabled={!canApprove}
                title={approvalBlockReason || `Confirm & approve Day ${dayNumber} log sheet`}
                className={`px-3 py-1 rounded font-semibold transition flex items-center gap-1 ${
                  canApprove
                    ? 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-xs cursor-pointer'
                    : 'bg-slate-800 text-slate-500 border border-slate-700 cursor-not-allowed opacity-60'
                }`}
              >
                <Check className="w-3.5 h-3.5" />
                <span>Confirm &amp; Approve Day {dayNumber}</span>
              </button>
            </div>
          ) : (
            <span className="px-2.5 py-1 rounded bg-emerald-900/60 text-emerald-300 border border-emerald-700 flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Approved by Driver</span>
            </span>
          )}
        </div>
      </div>

      {/* Inline Add Remark Form */}
      {isEditingRemarks && (
        <form onSubmit={handleAddRemark} className="bg-slate-50 border-b border-slate-200 p-4 text-xs space-y-3 print:hidden">
          <div className="font-semibold text-slate-800 flex items-center gap-1.5">
            <Edit3 className="w-4 h-4 text-blue-600" />
            <span>Add Driver Remark to Day {dayNumber} Log Sheet</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block text-slate-600 mb-1 font-medium">Time (Local)</label>
              <input
                type="time"
                value={newRemarkTime}
                onChange={(e) => setNewRemarkTime(e.target.value)}
                className="w-full bg-white border border-slate-300 rounded px-2.5 py-1.5 text-slate-800"
                required
              />
            </div>
            <div>
              <label className="block text-slate-600 mb-1 font-medium">Duty Status</label>
              <select
                value={newRemarkStatus}
                onChange={(e) => setNewRemarkStatus(e.target.value)}
                className="w-full bg-white border border-slate-300 rounded px-2.5 py-1.5 text-slate-800"
              >
                <option value="Off Duty">Off Duty</option>
                <option value="Sleeper Berth">Sleeper Berth</option>
                <option value="Driving">Driving</option>
                <option value="On Duty (Not Driving)">On Duty (Not Driving)</option>
              </select>
            </div>
            <div>
              <label className="block text-slate-600 mb-1 font-medium">Remark Description</label>
              <input
                type="text"
                placeholder="e.g. Safety inspection / shipper dock wait"
                value={newRemarkText}
                onChange={(e) => setNewRemarkText(e.target.value)}
                className="w-full bg-white border border-slate-300 rounded px-2.5 py-1.5 text-slate-800"
                required
              />
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={() => setIsEditingRemarks(false)}
              className="px-3 py-1 text-slate-600 hover:text-slate-800"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-3 py-1 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded"
            >
              Save Remark
            </button>
          </div>
        </form>
      )}

      {/* Validation Alert Banner if error exists */}
      {(validationAlert || logValidation.status === 'VIOLATION' || hasGlobalViolations) && (
        <div className="mx-5 mt-4 p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-start gap-2.5 print:hidden">
          <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <div className="font-bold text-rose-900">
              {logValidation.status === 'VIOLATION' ? 'Daily Log Validation Issue Detected' : 'HOS Conflict Notice'}
            </div>
            <p className="text-rose-700">
              {validationAlert || (logValidation.errors && logValidation.errors[0]) || 'Driving or on-duty activity conflict detected in current HOS plan.'}
            </p>
          </div>
        </div>
      )}

      <div className="p-5 sm:p-6 space-y-6">
        {/* Day Selector Tabs for Multi-Day Trips with Highlighted States */}
        <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-50 border border-slate-200/80 rounded-xl p-3 print:hidden">
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-blue-600" />
            <span className="text-xs font-semibold text-slate-800">Trip Calendar Days:</span>
            <span className="text-xs text-slate-500 font-medium">
              ({dailyLogs.length} Day{dailyLogs.length > 1 ? 's' : ''} Generated)
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {dailyLogs.map((sheet, index) => {
              const isSelected = selectedDayIndex === index;
              const isApproved = !!approvedTimestamps[sheet.day_number];

              return (
                <button
                  key={index}
                  type="button"
                  onClick={() => {
                    setSelectedDayIndex(index);
                    setValidationAlert(null);
                  }}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer flex items-center gap-1.5 ${
                    isSelected
                      ? 'bg-blue-600 text-white shadow-xs ring-2 ring-blue-600/30'
                      : 'bg-white text-slate-700 border border-slate-200 hover:bg-slate-100/80'
                  }`}
                >
                  <span>Day {sheet.day_number}</span>
                  <span className={`text-[10px] opacity-80`}>({sheet.formatted_date})</span>
                  {isApproved && (
                    <Check className="w-3 h-3 text-emerald-300 shrink-0" />
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Interactive Segment Hover Inspector */}
        {currentLog.segments && currentLog.segments.length > 0 && (
          <div className="bg-slate-50 border border-slate-200/80 rounded-xl p-3 text-xs print:hidden space-y-2">
            <div className="flex items-center justify-between text-slate-700 font-semibold">
              <span className="flex items-center gap-1.5">
                <Eye className="w-3.5 h-3.5 text-blue-600" />
                <span>Hover Timeline Segments Inspector:</span>
              </span>
              <span className="text-[11px] text-slate-500 font-normal">
                {currentLog.segments.length} duty intervals on this date
              </span>
            </div>

            {/* Segment blocks bar */}
            <div className="flex h-6 rounded-lg overflow-hidden border border-slate-300">
              {currentLog.segments.map((seg, idx) => {
                const widthPercent = Math.max(2, (seg.duration_hours / 24.0) * 100);
                let bg = 'bg-slate-300';
                if (seg.status === 'DRIVING') bg = 'bg-blue-600';
                else if (seg.status === 'ON_DUTY_NOT_DRIVING') bg = 'bg-amber-500';
                else if (seg.status === 'SLEEPER_BERTH') bg = 'bg-indigo-600';
                else if (seg.status === 'OFF_DUTY') bg = 'bg-slate-400';

                return (
                  <div
                    key={idx}
                    onMouseEnter={() => setHoveredSegment(seg)}
                    onMouseLeave={() => setHoveredSegment(null)}
                    style={{ width: `${widthPercent}%` }}
                    className={`${bg} h-full transition hover:brightness-110 cursor-pointer`}
                    title={`${seg.status}: ${seg.duration_hours}h`}
                  />
                );
              })}
            </div>

            {/* Hovered details display */}
            {hoveredSegment ? (
              <div className="p-2 rounded bg-white border border-slate-200 flex flex-wrap items-center justify-between text-xs animate-in fade-in">
                <div>
                  <strong>Status: </strong>
                  <span className="font-semibold text-blue-700">{hoveredSegment.status}</span>
                  <span className="text-slate-400 mx-1.5">•</span>
                  <span>Duration: <strong>{hoveredSegment.duration_hours} hrs</strong></span>
                  {hoveredSegment.distance_miles > 0 && (
                    <>
                      <span className="text-slate-400 mx-1.5">•</span>
                      <span>Miles: <strong>{hoveredSegment.distance_miles} mi</strong></span>
                    </>
                  )}
                </div>
                <div className="text-slate-500 italic">
                  {hoveredSegment.remarks || hoveredSegment.location_name || 'Rest period'}
                </div>
              </div>
            ) : (
              <div className="text-[11px] text-slate-400 italic text-center">
                Hover over the timeline bar to inspect duty intervals, driving miles, and transitions.
              </div>
            )}
          </div>
        )}

        {/* 3. Rendered Official SVG Driver Log Sheet */}
        <div className="border border-slate-200 rounded-xl overflow-hidden shadow-2xs bg-white">
          <div
            className="w-full overflow-x-auto"
            dangerouslySetInnerHTML={{ __html: currentLog.svg_markup }}
          />
        </div>

        {/* 4. Tabular Summary & 70-Hour Driver Recap */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 print:hidden">
          {/* Duty Status Hours */}
          <div className="bg-slate-50/70 border border-slate-200/80 rounded-xl p-4 text-xs space-y-2.5">
            <div className="flex items-center justify-between pb-2 border-b border-slate-200 font-semibold text-slate-800">
              <span>Day {currentLog.day_number} Duty Status Hours</span>
              <span className="text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 font-mono">
                Sum: {hours.total || 24.0} / 24.0 Hours
              </span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span>1. Off Duty:</span>
              <span className="font-mono font-semibold text-slate-900">{hours.off_duty} hrs</span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span>2. Sleeper Berth:</span>
              <span className="font-mono font-semibold text-slate-900">{hours.sleeper_berth} hrs</span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span>3. Driving (Miles: {currentLog.miles_driving_today || 0} mi):</span>
              <span className="font-mono font-semibold text-blue-700">{hours.driving} hrs</span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span>4. On Duty (Not Driving):</span>
              <span className="font-mono font-semibold text-amber-700">{hours.on_duty_not_driving} hrs</span>
            </div>
          </div>

          {/* 70-Hour Rolling Recap with Explanatory Tooltip */}
          <div className="bg-slate-50/70 border border-slate-200/80 rounded-xl p-4 text-xs space-y-2.5">
            <div className="flex items-center justify-between pb-2 border-b border-slate-200 font-semibold text-slate-800">
              <span className="flex items-center gap-1.5">
                <span>70-Hour / 8-Day Driver Recap</span>
                <span
                  className="cursor-help text-slate-400 hover:text-slate-600"
                  title={
                    recap.has_sufficient_history
                      ? `70h / 8-Day Cycle Recap:\n• Historical baseline hours: ${recap.historical_hours_used || 0}h\n• Generated trip on-duty hours: ${recap.generated_trip_hours || 0}h\n• Total recap hours: ${recap.total_recap_hours || recap.line_b_total_last_7_days}h\n• Available cycle hours: ${recap.available_cycle_hours || recap.line_c_available_tomorrow}h`
                      : `Generated Trip History Only:\n• Historical hours: ${recap.historical_hours_used || 0}h (No prior 7-day logs entered)\n• Generated trip on-duty hours: ${recap.generated_trip_hours || recap.line_b_total_last_7_days}h\n• Total recap hours: ${recap.total_recap_hours || recap.line_b_total_last_7_days}h\n• Available cycle hours: ${recap.available_cycle_hours || recap.line_c_available_tomorrow}h\n\nFull 7/8-day rolling recap requires prior 7 days of historical driver logs.`
                  }
                >
                  <HelpCircle className="w-3.5 h-3.5" />
                </span>
              </span>
              <span className="text-slate-500 font-normal">Property-Carrying</span>
            </div>

            {/* If insufficient historical data, show explicit alert indicator */}
            {recap.has_sufficient_history === false && (
              <div className="text-[11px] text-amber-800 bg-amber-50 px-2.5 py-2 rounded-lg border border-amber-200/80 space-y-1">
                <div className="flex items-center justify-between font-semibold">
                  <span className="flex items-center gap-1">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                    Generated Trip Validated — Historical 70/8 Data Required
                  </span>
                  <span className="text-amber-700 font-mono">Trip: {recap.generated_trip_hours || recap.line_b_total_last_7_days}h</span>
                </div>
                <p className="text-[10px] text-amber-700 leading-tight">
                  Daily driving and generated-trip rules were validated. Full 70/8 cycle compliance requires prior 7-day driver logs.
                </p>
              </div>
            )}

            <div className="flex justify-between text-slate-600">
              <span>Line A: On-duty hours today:</span>
              <span className="font-mono font-semibold text-slate-900">{recap.line_a_on_duty_today} hrs</span>
            </div>
            <div className="flex justify-between text-slate-600">
              <span>
                {recap.has_sufficient_history === false
                  ? 'Line B: Generated trip history only:'
                  : 'Line B: Total on-duty last 7 days + today:'}
              </span>
              <span className="font-mono font-semibold text-slate-900">
                {recap.has_sufficient_history === false
                  ? `${recap.generated_trip_hours ?? recap.line_b_total_last_7_days} hrs (Trip Only)`
                  : `${recap.total_recap_hours ?? recap.line_b_total_last_7_days} hrs`}
              </span>
            </div>
            <div className="flex justify-between font-semibold text-emerald-700 pt-1 border-t border-slate-200">
              <span>Line C: Total hours available tomorrow:</span>
              <span className="font-mono text-sm">{recap.available_cycle_hours ?? recap.line_c_available_tomorrow} hrs</span>
            </div>

            {recap.explanation && (
              <div className="text-[11px] text-slate-500 italic mt-1 pt-1 border-t border-slate-200/60 flex items-start gap-1">
                <Info className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />
                <span>{recap.explanation}</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
