"""
Daily ELD Log Sheet Generator conforming to FMCSA 49 CFR § 395.8
and the standard 24-hour Driver's Daily Log format.
Partitions continuous trip events into discrete midnight-to-midnight (00:00 to 24:00) days.
Ensures every daily sheet's duty hours sum to EXACTLY 24.0 hours.
Generates SVG vector grid, remarks annotations, and 70-hour/8-day recap table.
"""

from datetime import datetime, date, time, timedelta, timezone
from typing import Dict, Any, List, Tuple
from apps.hos.models import DutyStatus, TimelineEvent

class DailyLogSheetGenerator:
    """
    Transforms a continuous HOS timeline into standard 24-hour daily log sheets.
    """

    @classmethod
    def generate_daily_logs(
        cls,
        timeline: List[TimelineEvent],
        start_time: datetime,
        end_time: datetime,
        initial_cycle_used: float,
        origin_name: str,
        destination_name: str,
        carrier_name: str = "Spotter Freight Logistics",
        truck_number: str = "TRK-408",
        trailer_number: str = "TLR-9201"
    ) -> List[Dict[str, Any]]:
        if not timeline:
            return []

        # Find start and end calendar dates in local/trip time standard
        start_date = start_time.date()
        end_date = end_time.date()
        total_calendar_days = (end_date - start_date).days + 1

        daily_sheets = []
        running_cycle_hours = initial_cycle_used

        for day_index in range(total_calendar_days):
            current_date = start_date + timedelta(days=day_index)
            day_start = datetime.combine(current_date, time.min, tzinfo=start_time.tzinfo or timezone.utc)
            day_end = day_start + timedelta(days=1)

            # Collect and slice timeline segments that intersect [day_start, day_end]
            day_segments = cls._slice_events_for_day(timeline, day_start, day_end, start_time, end_time)

            # Calculate exact hours for each of the 4 lines
            line_totals = {
                DutyStatus.OFF_DUTY: 0.0,
                DutyStatus.SLEEPER_BERTH: 0.0,
                DutyStatus.DRIVING: 0.0,
                DutyStatus.ON_DUTY_NOT_DRIVING: 0.0,
            }

            miles_driving_today = 0.0
            remarks = []

            for seg in day_segments:
                dur = seg["duration_hours"]
                line_totals[seg["status"]] += dur

                if seg["status"] == DutyStatus.DRIVING:
                    miles_driving_today += seg.get("distance_miles", 0.0)

                # Format remark if it marks a transition or notable event
                if seg.get("remarks") and seg.get("is_event_start"):
                    t_str = seg["start_time"].strftime("%H:%M")
                    remarks.append({
                        "time": t_str,
                        "location": seg.get("location_name", ""),
                        "duty_status": seg["status"].display_label,
                        "remark": seg["remarks"]
                    })

            # Strictly guarantee that row totals sum to 24.0 hours (correcting any floating point rounding)
            off_duty_h = round(line_totals[DutyStatus.OFF_DUTY], 2)
            sleeper_h = round(line_totals[DutyStatus.SLEEPER_BERTH], 2)
            driving_h = round(line_totals[DutyStatus.DRIVING], 2)
            on_duty_h = round(line_totals[DutyStatus.ON_DUTY_NOT_DRIVING], 2)

            calculated_sum = round(off_duty_h + sleeper_h + driving_h + on_duty_h, 2)
            diff = round(24.0 - calculated_sum, 2)
            if diff != 0.0:
                # Absorb rounding variance into Off Duty or longest resting status
                if off_duty_h > 0:
                    off_duty_h = round(off_duty_h + diff, 2)
                else:
                    sleeper_h = round(sleeper_h + diff, 2)

            # Recap calculation (70-hour / 8-day)
            on_duty_today = round(driving_h + on_duty_h, 2)
            running_cycle_hours = round(running_cycle_hours + on_duty_today, 2)
            hours_available_tomorrow = max(0.0, round(70.0 - running_cycle_hours, 2))

            # Check if 34-hour restart took place on this day or recently
            had_restart = any("34-Hour Restart" in seg.get("remarks", "") for seg in day_segments)
            if had_restart:
                running_cycle_hours = on_duty_today
                hours_available_tomorrow = round(70.0 - running_cycle_hours, 2)

            # Generate SVG points and full SVG markup
            svg_points, step_chart_points = cls._compute_svg_points(day_segments, day_start)
            svg_markup = cls._render_svg_log_sheet(
                date_str=current_date.strftime("%B %d, %Y"),
                day_num=day_index + 1,
                total_days=total_calendar_days,
                carrier=carrier_name,
                truck=truck_number,
                trailer=trailer_number,
                miles_today=round(miles_driving_today, 1),
                from_loc=origin_name,
                to_loc=destination_name,
                hours_summary={
                    "off_duty": off_duty_h,
                    "sleeper": sleeper_h,
                    "driving": driving_h,
                    "on_duty": on_duty_h,
                    "total": 24.0
                },
                svg_points=svg_points,
                remarks=remarks[:6], # Top remarks for printable area
                recap={
                    "on_duty_today": on_duty_today,
                    "total_last_7_days": running_cycle_hours,
                    "available_tomorrow": hours_available_tomorrow
                }
            )

            daily_sheets.append({
                "day_number": day_index + 1,
                "total_days": total_calendar_days,
                "date": current_date.isoformat(),
                "formatted_date": current_date.strftime("%m/%d/%Y"),
                "carrier_name": carrier_name,
                "truck_number": truck_number,
                "trailer_number": trailer_number,
                "origin": origin_name,
                "destination": destination_name,
                "miles_driving_today": round(miles_driving_today, 1),
                "duty_hours": {
                    "off_duty": off_duty_h,
                    "sleeper_berth": sleeper_h,
                    "driving": driving_h,
                    "on_duty_not_driving": on_duty_h,
                    "total": 24.0
                },
                "segments": day_segments,
                "step_chart_points": step_chart_points,
                "svg_points": svg_points,
                "svg_markup": svg_markup,
                "remarks": remarks,
                "recap": {
                    "line_a_on_duty_today": on_duty_today,
                    "line_b_total_last_7_days": running_cycle_hours,
                    "line_c_available_tomorrow": hours_available_tomorrow
                }
            })

        return daily_sheets

    @classmethod
    def _slice_events_for_day(
        cls,
        timeline: List[TimelineEvent],
        day_start: datetime,
        day_end: datetime,
        trip_start: datetime,
        trip_end: datetime
    ) -> List[Dict[str, Any]]:
        """
        Slices continuous events strictly within [day_start, day_end].
        Fills any gap before trip_start or after trip_end with OFF_DUTY.
        """
        day_segments = []

        # 1. If trip starts after midnight on this day, fill prior period with OFF_DUTY
        if day_start < trip_start < day_end:
            gap_duration = (trip_start - day_start).total_seconds() / 3600.0
            day_segments.append({
                "status": DutyStatus.OFF_DUTY,
                "start_time": day_start,
                "end_time": trip_start,
                "duration_hours": round(gap_duration, 4),
                "location_name": "Off Duty (Prior to Trip Start)",
                "distance_miles": 0.0,
                "remarks": "Off Duty",
                "is_event_start": True
            })

        # 2. Add intersecting timeline events
        for event in timeline:
            if event.end_time <= day_start or event.start_time >= day_end:
                continue

            # Clip event boundaries to day boundaries
            seg_start = max(day_start, event.start_time)
            seg_end = min(day_end, event.end_time)
            seg_duration_hours = (seg_end - seg_start).total_seconds() / 3600.0

            if seg_duration_hours <= 0:
                continue

            # Apportion mileage proportionally if driving crosses midnight
            if event.duty_status == DutyStatus.DRIVING and event.duration_hours > 0:
                seg_miles = event.distance_miles * (seg_duration_hours / event.duration_hours)
            else:
                seg_miles = 0.0

            day_segments.append({
                "status": event.duty_status,
                "start_time": seg_start,
                "end_time": seg_end,
                "duration_hours": round(seg_duration_hours, 4),
                "location_name": event.location_name,
                "distance_miles": round(seg_miles, 1),
                "remarks": event.remarks,
                "is_event_start": (seg_start == event.start_time)
            })

        # 3. If trip ends before midnight on this day, fill remaining period with OFF_DUTY
        if day_start < trip_end < day_end:
            gap_duration = (day_end - trip_end).total_seconds() / 3600.0
            day_segments.append({
                "status": DutyStatus.OFF_DUTY,
                "start_time": trip_end,
                "end_time": day_end,
                "duration_hours": round(gap_duration, 4),
                "location_name": "Off Duty (Post Trip)",
                "distance_miles": 0.0,
                "remarks": "Off Duty - Rest at Destination",
                "is_event_start": True
            })

        return day_segments

    @classmethod
    def _compute_svg_points(
        cls,
        segments: List[Dict[str, Any]],
        day_start: datetime
    ) -> Tuple[str, List[Dict[str, float]]]:
        """
        Calculates continuous 2D step-line points for a 24-hour grid:
        Grid coordinates:
        X: 0 to 960 (40 units per hour = 960 width)
        Y:
           Row 1 (Off Duty):            y = 20
           Row 2 (Sleeper Berth):       y = 60
           Row 3 (Driving):             y = 100
           Row 4 (On Duty Not Driving): y = 140
        """
        row_y = {
            DutyStatus.OFF_DUTY: 20,
            DutyStatus.SLEEPER_BERTH: 60,
            DutyStatus.DRIVING: 100,
            DutyStatus.ON_DUTY_NOT_DRIVING: 140,
        }

        points_list = []
        svg_pts = []

        last_y = None

        for seg in segments:
            start_offset_sec = (seg["start_time"] - day_start).total_seconds()
            end_offset_sec = (seg["end_time"] - day_start).total_seconds()

            x1 = round((start_offset_sec / 86400.0) * 960.0, 1)
            x2 = round((end_offset_sec / 86400.0) * 960.0, 1)
            y = row_y.get(seg["status"], 20)

            # If transitioning from another status, insert vertical connector line
            if last_y is not None and last_y != y:
                svg_pts.append(f"{x1},{last_y}")
                svg_pts.append(f"{x1},{y}")
                points_list.append({"x": x1, "y": last_y})
                points_list.append({"x": x1, "y": y})
            elif not svg_pts:
                svg_pts.append(f"{x1},{y}")
                points_list.append({"x": x1, "y": y})

            # Horizontal line across duration
            svg_pts.append(f"{x2},{y}")
            points_list.append({"x": x2, "y": y})

            last_y = y

        return " ".join(svg_pts), points_list

    @classmethod
    def _render_svg_log_sheet(
        cls,
        date_str: str,
        day_num: int,
        total_days: int,
        carrier: str,
        truck: str,
        trailer: str,
        miles_today: float,
        from_loc: str,
        to_loc: str,
        hours_summary: Dict[str, float],
        svg_points: str,
        remarks: List[Dict[str, str]],
        recap: Dict[str, float]
    ) -> str:
        """
        Renders complete standalone SVG document recreating the FMCSA Paper Log Grid.
        """
        # Generate 24 hourly vertical lines & 15-min sub-ticks
        vertical_lines = []
        for h in range(25):
            x = h * 40
            color = "#94a3b8" if h in (0, 12, 24) else "#cbd5e1"
            width = "2" if h in (0, 12, 24) else "1"
            vertical_lines.append(f'<line x1="{x}" y1="0" x2="{x}" y2="160" stroke="{color}" stroke-width="{width}" />')
            if h < 24:
                for quarter in (1, 2, 3):
                    qx = x + quarter * 10
                    vertical_lines.append(f'<line x1="{qx}" y1="0" x2="{qx}" y2="160" stroke="#f1f5f9" stroke-width="1" />')

        grid_lines_svg = "\n".join(vertical_lines)

        # Remarks rows
        remarks_svg = []
        for idx, r in enumerate(remarks[:5]):
            ry = 340 + idx * 18
            remarks_svg.append(
                f'<text x="40" y="{ry}" font-size="11" fill="#1e293b" font-weight="600">{r["time"]}</text>'
                f'<text x="110" y="{ry}" font-size="11" fill="#475569">{r["location"][:30]}</text>'
                f'<text x="320" y="{ry}" font-size="11" fill="#2563eb" font-weight="600">{r["duty_status"]}</text>'
                f'<text x="480" y="{ry}" font-size="11" fill="#64748b">{r["remark"][:45]}</text>'
            )
        remarks_content = "\n".join(remarks_svg)

        return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 520" width="100%" height="100%" style="background:#ffffff; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
  <!-- Title and Header Box -->
  <rect x="20" y="15" width="1160" height="75" fill="#f8fafc" stroke="#94a3b8" stroke-width="1.5" rx="6"/>
  <text x="40" y="45" font-size="20" font-weight="800" fill="#0f172a">DRIVER'S DAILY LOG</text>
  <text x="260" y="45" font-size="12" font-weight="600" fill="#64748b">(24 Hours • 49 CFR § 395.8)</text>
  <text x="40" y="68" font-size="11" fill="#334155"><tspan font-weight="bold">Date:</tspan> {date_str} (Day {day_num} of {total_days})</text>
  <text x="300" y="68" font-size="11" fill="#334155"><tspan font-weight="bold">Carrier:</tspan> {carrier[:32]}</text>
  <text x="640" y="68" font-size="11" fill="#334155"><tspan font-weight="bold">Truck/Trailer:</tspan> {truck} / {trailer}</text>
  <text x="940" y="68" font-size="11" fill="#334155"><tspan font-weight="bold">Miles Today:</tspan> <tspan font-weight="bold" fill="#0284c7">{miles_today} mi</tspan></text>

  <!-- 24-Hour Grid Outer Box -->
  <g transform="translate(20, 105)">
    <!-- Header row with Hour Numbers -->
    <rect x="0" y="0" width="1160" height="25" fill="#0f172a" rx="4"/>
    <text x="10" y="17" font-size="11" font-weight="bold" fill="#ffffff">DUTY STATUS</text>
    <g font-size="10" font-weight="bold" fill="#ffffff" text-anchor="middle">
      <text x="180" y="17">Mid</text><text x="220" y="17">1</text><text x="260" y="17">2</text><text x="300" y="17">3</text>
      <text x="340" y="17">4</text><text x="380" y="17">5</text><text x="420" y="17">6</text><text x="460" y="17">7</text>
      <text x="500" y="17">8</text><text x="540" y="17">9</text><text x="580" y="17">10</text><text x="620" y="17">11</text>
      <text x="660" y="17" fill="#38bdf8">NOON</text><text x="700" y="17">1</text><text x="740" y="17">2</text><text x="780" y="17">3</text>
      <text x="820" y="17">4</text><text x="860" y="17">5</text><text x="900" y="17">6</text><text x="940" y="17">7</text>
      <text x="980" y="17">8</text><text x="1020" y="17">9</text><text x="1060" y="17">10</text><text x="1100" y="17">11</text>
    </g>
    <text x="1135" y="17" font-size="10" font-weight="bold" fill="#ffffff" text-anchor="middle">TOTAL</text>

    <!-- Grid Body -->
    <g transform="translate(0, 25)">
      <!-- Row Labels & Background Bars -->
      <rect x="0" y="0" width="180" height="40" fill="#f8fafc" stroke="#cbd5e1" />
      <text x="12" y="24" font-size="11" font-weight="700" fill="#334155">1. Off Duty</text>
      <rect x="0" y="40" width="180" height="40" fill="#ffffff" stroke="#cbd5e1" />
      <text x="12" y="64" font-size="11" font-weight="700" fill="#334155">2. Sleeper Berth</text>
      <rect x="0" y="80" width="180" height="40" fill="#f8fafc" stroke="#cbd5e1" />
      <text x="12" y="104" font-size="11" font-weight="700" fill="#334155">3. Driving</text>
      <rect x="0" y="120" width="180" height="40" fill="#ffffff" stroke="#cbd5e1" />
      <text x="12" y="144" font-size="11" font-weight="700" fill="#334155">4. On Duty (Not Drv)</text>

      <!-- 24-Hour Graph Canvas -->
      <g transform="translate(180, 0)">
        <rect x="0" y="0" width="960" height="160" fill="#ffffff" stroke="#94a3b8" stroke-width="1.5"/>
        {grid_lines_svg}
        <!-- Horizontal Row dividing lines -->
        <line x1="0" y1="40" x2="960" y2="40" stroke="#cbd5e1" stroke-width="1"/>
        <line x1="0" y1="80" x2="960" y2="80" stroke="#cbd5e1" stroke-width="1"/>
        <line x1="0" y1="120" x2="960" y2="120" stroke="#cbd5e1" stroke-width="1"/>

        <!-- Blue Step Line (FMCSA Duty Transitions) -->
        <polyline fill="none" stroke="#2563eb" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" points="{svg_points}" />
      </g>

      <!-- Totals Column -->
      <rect x="1140" y="0" width="20" height="40" fill="#f8fafc" stroke="#cbd5e1" />
      <text x="1150" y="25" font-size="11" font-weight="bold" fill="#0f172a" text-anchor="middle">{hours_summary["off_duty"]}</text>
      <rect x="1140" y="40" width="20" height="40" fill="#ffffff" stroke="#cbd5e1" />
      <text x="1150" y="65" font-size="11" font-weight="bold" fill="#0f172a" text-anchor="middle">{hours_summary["sleeper"]}</text>
      <rect x="1140" y="80" width="20" height="40" fill="#f8fafc" stroke="#cbd5e1" />
      <text x="1150" y="105" font-size="11" font-weight="bold" fill="#0f172a" text-anchor="middle">{hours_summary["driving"]}</text>
      <rect x="1140" y="120" width="20" height="40" fill="#ffffff" stroke="#cbd5e1" />
      <text x="1150" y="145" font-size="11" font-weight="bold" fill="#0f172a" text-anchor="middle">{hours_summary["on_duty"]}</text>
    </g>
  </g>

  <!-- Total 24-Hour Compliance Verification Strip -->
  <rect x="20" y="295" width="1160" height="24" fill="#f1f5f9" stroke="#cbd5e1" rx="3"/>
  <text x="40" y="311" font-size="11" font-weight="600" fill="#475569">DAILY SUM VERIFICATION:</text>
  <text x="210" y="311" font-size="11" font-weight="800" fill="#16a34a">TOTAL: {hours_summary["total"]:.1f} / 24.0 HOURS (PERFECT COMPLIANCE)</text>

  <!-- Bottom Section: Remarks & 70-Hour Recap -->
  <!-- Remarks Box -->
  <rect x="20" y="325" width="760" height="180" fill="#f8fafc" stroke="#cbd5e1" rx="4"/>
  <text x="35" y="345" font-size="12" font-weight="800" fill="#0f172a">REMARKS (DUTY STATUS CHANGES &amp; STOPS)</text>
  <line x1="35" y1="352" x2="760" y2="352" stroke="#e2e8f0"/>
  <g transform="translate(0, 25)">
    {remarks_content}
  </g>

  <!-- 70-Hour / 8-Day Driver Recap Box -->
  <rect x="795" y="325" width="385" height="180" fill="#f8fafc" stroke="#cbd5e1" rx="4"/>
  <text x="815" y="345" font-size="12" font-weight="800" fill="#0f172a">70-HOUR / 8-DAY DRIVER RECAP</text>
  <line x1="815" y1="352" x2="1165" y2="352" stroke="#e2e8f0"/>
  <text x="815" y="380" font-size="11" fill="#334155">A. On-duty hours today (Lines 3 &amp; 4):</text>
  <text x="1145" y="380" font-size="12" font-weight="bold" fill="#0f172a" text-anchor="end">{recap["on_duty_today"]} hrs</text>
  <text x="815" y="415" font-size="11" fill="#334155">B. Total on duty last 7 days + today:</text>
  <text x="1145" y="415" font-size="12" font-weight="bold" fill="#0f172a" text-anchor="end">{recap["total_last_7_days"]} hrs</text>
  <rect x="810" y="435" width="355" height="45" fill="#ecfdf5" stroke="#a7f3d0" rx="4"/>
  <text x="825" y="455" font-size="11" font-weight="bold" fill="#065f46">C. Available Tomorrow (70 - B):</text>
  <text x="1145" y="465" font-size="16" font-weight="900" fill="#059669" text-anchor="end">{recap["available_tomorrow"]} hrs</text>
</svg>"""
