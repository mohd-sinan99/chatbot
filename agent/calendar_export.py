"""
iCalendar Export Engine (Phase 6 — PRD Future Enhancements: Calendar Integration)
Generates RFC 5545-compliant .ics files from TripPlan objects so travellers can
import their itinerary directly into Google Calendar, Apple Calendar, or Outlook.

Stdlib only — no external dependencies (icalendar package NOT required).
"""

import os
import re
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from agent.models import TripPlan


class CalendarExporter:
    """
    Converts a TripPlan into a standards-compliant iCalendar (.ics) file.

    Each ItineraryDay becomes a VEVENT spanning that calendar date.
    Individual attraction slots are created as shorter VEVENTs within the day.
    """

    # Default start time for the first activity of each day
    DAY_START_HOUR = 9      # 09:00 AM
    SLOT_DURATION_MINS = 90  # Default 1.5 hrs per activity slot

    @classmethod
    def export(
        cls,
        trip: TripPlan,
        start_date: Optional[date] = None,
        output_dir: str = "exports",
    ) -> str:
        """
        Generate a .ics file for `trip`.

        Args:
            trip: The TripPlan to export.
            start_date: First day of the trip (defaults to today).
            output_dir: Directory to write the .ics file.

        Returns:
            Absolute path of the generated .ics file.
        """
        if start_date is None:
            start_date = date.today()

        os.makedirs(output_dir, exist_ok=True)

        lines = cls._build_calendar(trip, start_date)
        ics_content = "\r\n".join(lines) + "\r\n"

        safe_name = re.sub(r"[^\w\-]", "_", trip.destination.lower())
        filename = f"{safe_name}_{trip.duration_days}d_itinerary.ics"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(ics_content)

        return os.path.abspath(filepath)

    # ------------------------------------------------------------------
    # Private builders
    # ------------------------------------------------------------------

    @classmethod
    def _build_calendar(cls, trip: TripPlan, start_date: date) -> list:
        now_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        cal_name = f"{trip.destination} Trip — {trip.duration_days} Days"

        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Smart Travel Planner AI Agent//Phase6//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            f"X-WR-CALNAME:{cls._escape(cal_name)}",
            "X-WR-TIMEZONE:Asia/Kolkata",
        ]

        for day in trip.days:
            day_offset = day.day_number - 1
            cal_date = start_date + timedelta(days=day_offset)

            # --- Full-day summary event ---
            lines += cls._full_day_event(
                uid=str(uuid.uuid4()),
                summary=f"Day {day.day_number}: {trip.destination} Itinerary",
                description=cls._day_description(day),
                cal_date=cal_date,
                dtstamp=now_stamp,
            )

            # --- Per-activity slot events ---
            current_hour = cls.DAY_START_HOUR
            current_min = 0

            for activity in day.activities:
                duration_hrs = getattr(activity, "duration_hours", None) or 1.5
                slot_mins = int(duration_hrs * 60)

                dt_start = datetime(
                    cal_date.year, cal_date.month, cal_date.day,
                    current_hour, current_min
                )
                dt_end = dt_start + timedelta(minutes=slot_mins)

                # Advance clock (add 15-min gap between activities)
                total_advance = slot_mins + 15
                current_min += total_advance % 60
                current_hour += total_advance // 60
                if current_min >= 60:
                    current_hour += current_min // 60
                    current_min = current_min % 60

                notes = getattr(activity, "notes", "") or ""
                desc = f"{activity.description}. {notes}".strip().rstrip(".")

                act_name = getattr(activity, "title", None) or getattr(activity, "name", "Activity")
                lines += cls._timed_event(
                    uid=str(uuid.uuid4()),
                    summary=f"[D{day.day_number}] {act_name}",
                    description=desc,
                    location=trip.destination,
                    dt_start=dt_start,
                    dt_end=dt_end,
                    dtstamp=now_stamp,
                    url=getattr(activity, "source_url", "") or getattr(activity, "source", ""),
                )

        # --- Budget reminder event (last day) ---
        last_date = start_date + timedelta(days=trip.duration_days - 1)
        lines += cls._budget_event(trip, last_date, now_stamp)

        lines.append("END:VCALENDAR")
        return lines

    @classmethod
    def _full_day_event(
        cls,
        uid: str,
        summary: str,
        description: str,
        cal_date: date,
        dtstamp: str,
    ) -> list:
        return [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{dtstamp}",
            f"DTSTART;VALUE=DATE:{cal_date.strftime('%Y%m%d')}",
            f"DTEND;VALUE=DATE:{(cal_date + timedelta(days=1)).strftime('%Y%m%d')}",
            f"SUMMARY:{cls._escape(summary)}",
            f"DESCRIPTION:{cls._escape(description)}",
            "TRANSP:TRANSPARENT",
            "END:VEVENT",
        ]

    @classmethod
    def _timed_event(
        cls,
        uid: str,
        summary: str,
        description: str,
        location: str,
        dt_start: datetime,
        dt_end: datetime,
        dtstamp: str,
        url: str = "",
    ) -> list:
        lines = [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{dtstamp}",
            f"DTSTART;TZID=Asia/Kolkata:{dt_start.strftime('%Y%m%dT%H%M%S')}",
            f"DTEND;TZID=Asia/Kolkata:{dt_end.strftime('%Y%m%dT%H%M%S')}",
            f"SUMMARY:{cls._escape(summary)}",
            f"DESCRIPTION:{cls._escape(description)}",
            f"LOCATION:{cls._escape(location)}",
        ]
        if url:
            lines.append(f"URL:{url}")
        lines.append("END:VEVENT")
        return lines

    @classmethod
    def _budget_event(cls, trip: TripPlan, last_date: date, dtstamp: str) -> list:
        total = getattr(trip.budget, "total_estimated", 0)
        summary = f"[Budget] {trip.destination} — Est. ₹{total:,.0f}"
        desc = (
            f"Estimated trip budget: ₹{total:,.0f} for {trip.travelers_count} traveller(s). "
            "All costs are estimates — confirm with providers before booking."
        )
        return cls._full_day_event(
            uid=str(uuid.uuid4()),
            summary=summary,
            description=desc,
            cal_date=last_date,
            dtstamp=dtstamp,
        )

    @staticmethod
    def _day_description(day) -> str:
        parts = [f"Theme: {day.theme}" if hasattr(day, "theme") and day.theme else ""]
        if hasattr(day, "zone") and day.zone:
            parts.append(f"Zone: {day.zone}")
        for act in day.activities:
            act_name = getattr(act, "title", None) or getattr(act, "name", "Activity")
            cost = getattr(act, "estimated_cost", None) or getattr(act, "entry_fee", 0.0)
            fee = f"₹{cost:.0f}" if cost else "Free"
            parts.append(f"• {act_name} ({fee})")
        if hasattr(day, "lunch_recommendation") and day.lunch_recommendation:
            parts.append(f"Lunch: {day.lunch_recommendation}")
        return "\\n".join(p for p in parts if p)

    @staticmethod
    def _escape(text: str) -> str:
        """Escape special iCalendar characters per RFC 5545 §3.3.11."""
        if not text:
            return ""
        text = text.replace("\\", "\\\\")
        text = text.replace(";", "\\;")
        text = text.replace(",", "\\,")
        text = text.replace("\n", "\\n")
        return text

