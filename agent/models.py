"""
Core domain models and data schemas for Smart Travel Planner AI Agent.
Includes schemas for trips, activities, day plans, budget breakdowns, and user preferences.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any


@dataclass
class UserPreferences:
    """Stored preferences for a user to personalize trip planning across sessions."""
    user_id: str = "default_user"
    starting_location: Optional[str] = None
    default_travelers: int = 2
    preferred_currency: str = "INR"
    dietary_preferences: List[str] = field(default_factory=list)
    interests: List[str] = field(default_factory=list)
    travel_style: str = "budget"  # budget, moderate, luxury
    past_destinations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserPreferences":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Activity:
    """An individual activity or sight in an itinerary."""
    title: str
    description: str
    time_slot: str  # e.g., "Morning", "Afternoon", "Evening"
    duration_hours: float
    estimated_cost: float
    location: str
    opening_hours: Optional[str] = None
    verified: bool = False
    source_url: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Activity":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ItineraryDay:
    """Day-by-day plan containing ordered activities and transit notes."""
    day_number: int
    date_or_label: str  # e.g., "Day 1" or "2026-11-12"
    theme: str  # e.g., "Heritage & Caves Exploration"
    activities: List[Activity] = field(default_factory=list)
    transit_notes: str = ""
    estimated_day_cost: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["activities"] = [a.to_dict() if isinstance(a, Activity) else a for a in self.activities]
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ItineraryDay":
        acts = [Activity.from_dict(a) if isinstance(a, dict) else a for a in data.get("activities", [])]
        data_copy = {k: v for k, v in data.items() if k in cls.__dataclass_fields__ and k != "activities"}
        return cls(activities=acts, **data_copy)


@dataclass
class BudgetBreakdown:
    """Itemized budget estimation with explicit assumptions and confidence level."""
    currency: str = "INR"
    transport_cost: float = 0.0
    accommodation_cost: float = 0.0
    food_cost: float = 0.0
    activities_cost: float = 0.0
    contingency_cost: float = 0.0
    total_estimated: float = 0.0
    per_person_estimated: float = 0.0
    target_budget: Optional[float] = None
    is_over_budget: bool = False
    assumptions: List[str] = field(default_factory=list)
    disclaimers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BudgetBreakdown":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class TripPlan:
    """Complete finalized trip plan, containing itinerary days, budget, tips, and disclaimers."""
    trip_id: str
    destination: str
    origin: Optional[str]
    duration_days: int
    travelers_count: int
    days: List[ItineraryDay] = field(default_factory=list)
    budget: BudgetBreakdown = field(default_factory=BudgetBreakdown)
    travel_tips: List[str] = field(default_factory=list)
    safety_advisories: List[str] = field(default_factory=list)
    booking_disclaimer: str = (
        "Notice: All prices and schedules are estimates. "
        "No bookings are confirmed until completed directly with official service providers."
    )
    status: str = "DRAFT"  # DRAFT, FINALIZED, ARCHIVED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trip_id": self.trip_id,
            "destination": self.destination,
            "origin": self.origin,
            "duration_days": self.duration_days,
            "travelers_count": self.travelers_count,
            "days": [d.to_dict() for d in self.days],
            "budget": self.budget.to_dict() if isinstance(self.budget, BudgetBreakdown) else self.budget,
            "travel_tips": self.travel_tips,
            "safety_advisories": self.safety_advisories,
            "booking_disclaimer": self.booking_disclaimer,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TripPlan":
        days = [ItineraryDay.from_dict(d) if isinstance(d, dict) else d for d in data.get("days", [])]
        budget_data = data.get("budget", {})
        budget = BudgetBreakdown.from_dict(budget_data) if isinstance(budget_data, dict) else budget_data
        data_copy = {
            k: v for k, v in data.items() 
            if k in cls.__dataclass_fields__ and k not in ("days", "budget")
        }
        return cls(days=days, budget=budget, **data_copy)

