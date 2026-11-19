"""
Operational Hours & Constraint Engine (PRD Section 6.2 & 10)
Validates itinerary activities against operating hours, closed-days (e.g. Mondays),
seasonal closures, and prevents crowded or impossible schedules.
"""

from typing import Dict, Any, List, Optional, Tuple
from agent.models import Activity, ItineraryDay


class ConstraintEngine:
    """
    Validates operating hours, closed days (e.g., Monday closures), and seasonal restrictions.
    """

    # Days when specific sights are known to be closed
    KNOWN_CLOSED_DAYS: Dict[str, List[str]] = {
        "edakkal caves": ["monday"],
        "tea museum (kdhp)": ["monday"],
        "eravikulam national park": [],  # Special season check
    }

    # Seasonal closures
    SEASONAL_CLOSURES: Dict[str, List[int]] = {
        "eravikulam national park": [2, 3],  # Closed Feb (2) & March (3) for calving
    }

    @classmethod
    def check_activity_availability(
        cls,
        activity_title: str,
        day_of_week: Optional[str] = None,
        month: Optional[int] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if an activity is open on a given day of the week or month.
        Returns: (is_available: bool, warning_or_reason: Optional[str])
        """
        norm_title = activity_title.strip().lower()

        # Check day-of-week closures
        if day_of_week:
            dow = day_of_week.strip().lower()
            for site, closed_days in cls.KNOWN_CLOSED_DAYS.items():
                if site in norm_title and dow in closed_days:
                    return False, f"'{activity_title}' is closed on {day_of_week.title()}s."

        # Check seasonal closures
        if month:
            for site, closed_months in cls.SEASONAL_CLOSURES.items():
                if site in norm_title and month in closed_months:
                    month_names = {2: "February", 3: "March"}
                    return False, f"'{activity_title}' is closed in {month_names.get(month, str(month))} for calving season."

        return True, None

    @classmethod
    def validate_and_adjust_itinerary(
        cls,
        days: List[ItineraryDay],
        start_day_of_week: Optional[str] = None
    ) -> Tuple[List[ItineraryDay], List[str]]:
        """
        Validates all activities across days.
        If an activity is scheduled on a day it is closed, swaps it to another day where possible.
        Returns: (adjusted_days: List[ItineraryDay], warnings_or_changes: List[str])
        """
        if not start_day_of_week:
            # If no start day is specified, no day-of-week collision can be asserted
            return days, []

        weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        try:
            start_idx = weekdays.index(start_day_of_week.strip().lower())
        except ValueError:
            return days, []

        changes: List[str] = []

        # Map each day number to its day of week
        for i, day in enumerate(days):
            current_dow = weekdays[(start_idx + i) % 7]
            for j, act in enumerate(day.activities):
                is_open, reason = cls.check_activity_availability(act.title, day_of_week=current_dow)
                if not is_open:
                    # Look for another day to swap with
                    swapped = False
                    for other_i, other_day in enumerate(days):
                        if other_i == i:
                            continue
                        other_dow = weekdays[(start_idx + other_i) % 7]
                        # Check if the activity is open on other_dow
                        other_open, _ = cls.check_activity_availability(act.title, day_of_week=other_dow)
                        if other_open and len(other_day.activities) > 0:
                            # Swap activities between days
                            target_act = other_day.activities[0]
                            target_open, _ = cls.check_activity_availability(target_act.title, day_of_week=current_dow)
                            if target_open:
                                day.activities[j] = target_act
                                other_day.activities[0] = act
                                changes.append(
                                    f"Detected closure: {reason} Swapped with '{target_act.title}' from Day {other_day.day_number}."
                                )
                                swapped = True
                                break
                    if not swapped:
                        changes.append(f"Notice: {reason} Verify alternative visiting schedule.")

        return days, changes

