import React, { useState } from 'react';
import { FileText, Calendar, Printer, Download, CheckCircle2, ShieldCheck } from 'lucide-react';

export default function EldLogSection({ dailyLogs = [], isPlanned }) {
  const [selectedDayIndex, setSelectedDayIndex] = useState(0);

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

  return (
    <div className="bg-white rounded-xl border border-slate-200/90 shadow-xs overflow-hidden print:border-none print:shadow-none">
      {/* Header */}
      <div className="px-5 py-4 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-blue-50 text-blue-700 flex items-center justify-center">
            <FileText className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-semibold text-slate-900">
                Driver's Daily Log (24 Hours • 49 CFR § 395.8)
              </h2>
              <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                FMCSA Compliant
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Standard 4-tier graphical duty grid with 15-min sub-intervals, duty transitions, &amp; rolling recap
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

      <div className="p-5 sm:p-6 space-y-6">
        {/* Day Selector Tabs for Multi-Day Trips */}
        <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-50 border border-slate-200/80 rounded-xl p-3 print:hidden">
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-blue-600" />
            <span className="text-xs font-semibold text-slate-800">Trip Calendar Days:</span>
            <span className="text-xs text-slate-500 font-medium">
              ({dailyLogs.length} Day{dailyLogs.length > 1 ? 's' : ''} Generated)
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {dailyLogs.map((sheet, index) => (
              <button
                key={sheet.day_number || index}
                type="button"
                onClick={() => setSelectedDayIndex(index)}
                className={`text-xs px-3.5 py-1.5 rounded-lg font-semibold border transition cursor-pointer ${
                  selectedDayIndex === index
                    ? 'bg-blue-600 text-white border-blue-600 shadow-xs'
                    : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-100'
                }`}
              >
                Day {sheet.day_number} ({sheet.formatted_date})
              </button>
            ))}
          </div>
        </div>

        {/* Real Backend Vector SVG Log Sheet */}
        {currentLog.svg_markup && (
          <div className="border border-slate-300 rounded-xl overflow-hidden shadow-2xs bg-white p-2 sm:p-4">
            <div
              className="w-full overflow-x-auto"
              dangerouslySetInnerHTML={{ __html: currentLog.svg_markup }}
            />
          </div>
        )}

        {/* Daily Breakdown Summary & Recap Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Daily 4-Status Hours Card */}
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-2.5">
            <div className="flex items-center justify-between border-b border-slate-200 pb-2">
              <span className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                Day {currentLog.day_number} Duty Status Hours
              </span>
              <span className="text-xs font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                Sum: {hours.total.toFixed(1)} / 24.0 Hours
              </span>
            </div>

            <div className="space-y-1.5 text-xs text-slate-700">
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span>1. Off Duty:</span>
                <strong className="font-mono">{hours.off_duty.toFixed(1)} hrs</strong>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span>2. Sleeper Berth:</span>
                <strong className="font-mono">{hours.sleeper_berth.toFixed(1)} hrs</strong>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span>3. Driving (Miles: {currentLog.miles_driving_today} mi):</span>
                <strong className="font-mono text-blue-700">{hours.driving.toFixed(1)} hrs</strong>
              </div>
              <div className="flex justify-between py-1">
                <span>4. On Duty (Not Driving):</span>
                <strong className="font-mono text-amber-700">{hours.on_duty_not_driving.toFixed(1)} hrs</strong>
              </div>
            </div>
          </div>

          {/* 70-Hour / 8-Day Recap Card */}
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-2.5">
            <div className="flex items-center justify-between border-b border-slate-200 pb-2">
              <span className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                70-Hour / 8-Day Driver Recap
              </span>
              <span className="text-xs font-medium text-slate-600 bg-white px-2 py-0.5 rounded border border-slate-200">
                Property-Carrying
              </span>
            </div>

            <div className="space-y-1.5 text-xs text-slate-700">
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span>Line A: On-duty hours today:</span>
                <strong className="font-mono text-slate-900">{recap.line_a_on_duty_today} hrs</strong>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span>Line B: Total on-duty last 7 days + today:</span>
                <strong className="font-mono text-slate-900">{recap.line_b_total_last_7_days} hrs</strong>
              </div>
              <div className="flex justify-between py-1 text-emerald-700 font-semibold bg-emerald-50/70 px-2 rounded">
                <span>Line C: Total hours available tomorrow:</span>
                <strong className="font-mono text-sm">{recap.line_c_available_tomorrow} hrs</strong>
              </div>
            </div>
          </div>
        </div>

        {/* Inspector roadside compliance footer */}
        <div className="text-center pt-1 text-xs text-slate-500 flex items-center justify-center gap-1.5">
          <ShieldCheck className="w-4 h-4 text-emerald-600" />
          <span>Electronic Logging Device (ELD) RODS Record • Fully Compliant with 49 CFR Part 395</span>
        </div>
      </div>
    </div>
  );
}
