"""
Budget Calculator Tool (📘 L2: Tool 2 of 4)
Calculates category-wise trip cost estimates, checks against user budget, and suggests cost-saving alternatives.
"""

import math
from typing import Dict, Any, List, Optional
from agent.tools.base import BaseTool
from config import DEFAULT_COST_ASSUMPTIONS


class BudgetCalculatorTool(BaseTool):
    """Tool to calculate transparent, category-wise trip budgets with assumptions and overrun detection."""

    @property
    def name(self) -> str:
        return "calculate_budget_breakdown"

    @property
    def description(self) -> str:
        return (
            "Calculate itemized budget estimates for transport, accommodation, food, and activities. "
            "Evaluates whether the trip fits within the user's target budget and provides cost-saving suggestions."
        )

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "destination": {
                    "type": "string",
                    "description": "Trip destination (e.g. 'Wayanad')"
                },
                "duration_days": {
                    "type": "integer",
                    "description": "Total duration of trip in days",
                    "minimum": 1
                },
                "travelers": {
                    "type": "integer",
                    "description": "Number of travelers",
                    "minimum": 1
                },
                "tier": {
                    "type": "string",
                    "enum": ["budget", "moderate", "luxury"],
                    "description": "Travel budget tier (default: 'budget')",
                    "default": "budget"
                },
                "target_budget": {
                    "type": "number",
                    "description": "User's stated maximum budget in INR (optional)"
                },
                "include_intercity_travel": {
                    "type": "boolean",
                    "description": "Whether to include intercity transit to the destination (default: False)",
                    "default": False
                }
            },
            "required": ["destination", "duration_days", "travelers"]
        }

    def execute(
        self,
        destination: str,
        duration_days: int,
        travelers: int,
        tier: str = "budget",
        target_budget: Optional[float] = None,
        include_intercity_travel: bool = False
    ) -> Dict[str, Any]:
        # Validate inputs
        if duration_days < 1:
            raise ValueError("duration_days must be at least 1")
        if travelers < 1:
            raise ValueError("travelers must be at least 1")
        tier = tier.lower() if tier in ["budget", "moderate", "luxury"] else "budget"

        assumptions = DEFAULT_COST_ASSUMPTIONS
        nights = max(1, duration_days - 1)
        rooms_needed = math.ceil(travelers / 2)

        # 1. Accommodation
        nightly_rate = assumptions["accommodation_per_night"][tier]
        total_accommodation = nightly_rate * nights * rooms_needed

        # 2. Food
        daily_food_rate = assumptions["food_per_person_per_day"][tier]
        total_food = daily_food_rate * travelers * duration_days

        # 3. Local Commute
        daily_commute_rate = assumptions["local_commute_per_day"][tier]
        total_commute = daily_commute_rate * duration_days

        # 4. Intercity Travel (optional)
        intercity_cost = 0.0
        if include_intercity_travel:
            # Approximate standard bus/train rate per person
            intercity_rate = 600.0 if tier == "budget" else 1500.0
            intercity_cost = intercity_rate * travelers * 2  # Round trip

        # 5. Sightseeing & Activities (standard baseline)
        activities_rate_per_day = 150.0 if tier == "budget" else 400.0
        total_activities = activities_rate_per_day * travelers * duration_days

        # 6. Subtotal & Contingency
        subtotal = total_accommodation + total_food + total_commute + intercity_cost + total_activities
        contingency = subtotal * assumptions["contingency_percentage"]
        total_estimated = round(subtotal + contingency, 2)
        per_person = round(total_estimated / travelers, 2)

        # Check overrun against user's target budget
        is_over_budget = False
        overrun_amount = 0.0
        cost_saving_tips: List[str] = []

        if target_budget is not None and target_budget > 0:
            if total_estimated > target_budget:
                is_over_budget = True
                overrun_amount = round(total_estimated - target_budget, 2)
                cost_saving_tips = [
                    "Opt for homestays, hostels, or government guest houses instead of hotels.",
                    "Use local state transport (KSRTC/public bus) instead of private auto/taxi.",
                    "Focus on scenic viewpoints, waterfalls, and public lakes with low or no entry fees.",
                    "Dine at authentic local Kerala messes/eateries for wholesome food under ₹100-150 per meal."
                ]

        explanation_assumptions = [
            f"Accommodation: {nights} night(s) in {rooms_needed} room(s) @ ₹{nightly_rate:,.0f}/night ({tier} tier).",
            f"Food: ₹{daily_food_rate:,.0f}/day per person across {duration_days} days for {travelers} traveler(s).",
            f"Local Commute: ₹{daily_commute_rate:,.0f}/day for local transport.",
            f"Activities/Entry fees: ~₹{activities_rate_per_day:,.0f}/day per person.",
            f"Contingency: 8% buffer (₹{contingency:,.0f}) for emergency expenses."
        ]

        if include_intercity_travel:
            explanation_assumptions.append(f"Intercity Travel: Included round-trip estimate of ₹{intercity_cost:,.0f}.")
        else:
            explanation_assumptions.append("Intercity Travel: Excluded (assumes starting at destination).")

        return {
            "destination": destination,
            "currency": "INR",
            "tier": tier,
            "duration_days": duration_days,
            "travelers": travelers,
            "breakdown": {
                "accommodation": round(total_accommodation, 2),
                "food": round(total_food, 2),
                "local_commute": round(total_commute, 2),
                "intercity_travel": round(intercity_cost, 2),
                "activities_entry_fees": round(total_activities, 2),
                "contingency_buffer": round(contingency, 2),
            },
            "total_estimated": total_estimated,
            "per_person_estimated": per_person,
            "target_budget": target_budget,
            "is_over_budget": is_over_budget,
            "overrun_amount": overrun_amount,
            "assumptions": explanation_assumptions,
            "cost_saving_suggestions": cost_saving_tips,
            "disclaimer": "All figures are estimated approximations based on standard seasonal rates. Confirm live prices directly with service providers."
        }

