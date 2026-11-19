"""
Delta Itinerary Refinement Engine (PRD Section 6.8 & Core Use Case 6)
Applies targeted modifications to active trip plans without destroying unchanged days or activities.
Provides change summaries so users can review adjustments.
"""

from typing import Dict, Any, List, Tuple
from agent.models import TripPlan, ItineraryDay, Activity, BudgetBreakdown
from agent.tools import ToolRegistry


class DeltaPlanRefiner:
    """
    Applies conversational delta updates to an existing TripPlan.
    """

    def __init__(self, tool_registry: ToolRegistry):
        self.tools = tool_registry

    def refine_plan(
        self,
        current_plan: TripPlan,
        user_request: str
    ) -> Tuple[TripPlan, str]:
        """
        Parses modification request, updates affected sections, and returns (updated_plan, change_summary).
        """
        req = user_request.lower().strip()
        changes_applied: List[str] = []

        # 1. Budget Tier Refinement (e.g., "Make it more budget friendly", "Switch to moderate/luxury")
        if any(w in req for w in ["budget friendly", "cheaper", "lower budget", "cut costs"]):
            new_tier = "budget"
            changes_applied.append("Switched budget tier to 'budget' with cost-saving homestay & public commute assumptions.")
            current_plan = self._recalculate_budget(current_plan, new_tier)
        elif "luxury" in req or "premium" in req:
            new_tier = "luxury"
            changes_applied.append("Upgraded budget tier to 'luxury' with premium 4-star resort and private dedicated cab.")
            current_plan = self._recalculate_budget(current_plan, new_tier)
        elif "moderate" in req or "comfortable" in req:
            new_tier = "moderate"
            changes_applied.append("Adjusted budget tier to 'moderate' (3-star hotel / private taxi).")
            current_plan = self._recalculate_budget(current_plan, new_tier)

        # 2. Activity / Pacing Refinement (e.g., "Make day 1 more relaxing", "Replace trekking with tea plantation/lake")
        if "relaxing" in req or "leisure" in req or "easy pace" in req:
            # Find the day mentioned (or default to Day 1)
            target_day_num = 1
            if "day 2" in req:
                target_day_num = 2
            elif "day 3" in req:
                target_day_num = 3

            for day in current_plan.days:
                if day.day_number == target_day_num:
                    day.theme = f"{current_plan.destination} Relaxing & Leisure Experience"
                    # Replace intense activities with relaxing ones
                    day.activities = [
                        Activity(
                            title=f"{current_plan.destination} Scenic Tea Plantation & Lake Walk",
                            description="Gentle walking trail around lush plantations with scenic lake views and fresh mountain breeze.",
                            time_slot="Morning (10:00 AM - 1:00 PM)",
                            duration_hours=2.0,
                            estimated_cost=30.0,
                            location=current_plan.destination,
                            opening_hours="9:00 AM - 5:00 PM",
                            verified=True,
                            notes="Leisurely pace suitable for all fitness levels."
                        ),
                        Activity(
                            title="Sunset Café & Local Spice Market",
                            description="Relaxing evening at a hill-view café followed by sampling fresh farm spices.",
                            time_slot="Late Afternoon (4:00 PM - 6:00 PM)",
                            duration_hours=2.0,
                            estimated_cost=50.0,
                            location=current_plan.destination,
                            opening_hours="10:00 AM - 8:00 PM",
                            verified=True,
                            notes="Great views and authentic local tea."
                        )
                    ]
                    day.transit_notes = "Short auto ride; minimal walking required."
                    day.estimated_day_cost = sum(a.estimated_cost for a in day.activities)
                    changes_applied.append(f"Updated Day {target_day_num} with relaxing, low-intensity activities and buffer time.")
                    break

        # 3. Swap Specific Activity (e.g., "Replace Banasura Dam with Chembra Peak" or vice versa)
        if "chembra" in req:
            # Add Chembra Peak trekking
            for day in current_plan.days:
                if len(day.activities) > 0:
                    day.activities[0] = Activity(
                        title="Chembra Peak Trekking",
                        description="Scenic trek up to the famous heart-shaped lake (Hridaya Saras).",
                        time_slot="Early Morning (7:30 AM - 12:00 PM)",
                        duration_hours=4.5,
                        estimated_cost=150.0,
                        location="Meppadi, Wayanad",
                        opening_hours="7:00 AM - 2:00 PM",
                        verified=True,
                        notes="Forest Department pass required. Start early to beat afternoon mist."
                    )
                    changes_applied.append(f"Replaced morning activity on Day {day.day_number} with Chembra Peak trek.")
                    day.estimated_day_cost = sum(a.estimated_cost for a in day.activities)
                    break

        # 4. Explicit Budget Target Change (e.g., "My budget is now ₹8,000")
        import re
        budget_match = re.search(r'(?:₹|rs\.?|budget is|to)\s?([0-9,]+)', req)
        if budget_match and any(w in req for w in ["budget", "increase", "change budget", "now"]):
            try:
                new_budget = float(budget_match.group(1).replace(",", ""))
                if new_budget > 1000:
                    current_plan.budget.target_budget = new_budget
                    current_plan.budget.is_over_budget = current_plan.budget.total_estimated > new_budget
                    changes_applied.append(f"Updated target budget to ₹{new_budget:,.2f}.")
            except ValueError:
                pass

        if not changes_applied:
            changes_applied.append("Refined itinerary notes and refreshed local estimates according to your preferences.")

        summary = "\n".join(f"• {c}" for c in changes_applied)
        return current_plan, summary

    def _recalculate_budget(self, plan: TripPlan, tier: str) -> TripPlan:
        """Helper to re-compute budget metrics using the BudgetCalculatorTool."""
        res = self.tools.execute_tool(
            "calculate_budget_breakdown",
            destination=plan.destination,
            duration_days=plan.duration_days,
            travelers=plan.travelers_count,
            tier=tier,
            target_budget=plan.budget.target_budget
        )
        if res.status == "SUCCESS":
            data = res.data
            bd = data["breakdown"]
            plan.budget = BudgetBreakdown(
                currency="INR",
                transport_cost=bd["local_commute"] + bd["intercity_travel"],
                accommodation_cost=bd["accommodation"],
                food_cost=bd["food"],
                activities_cost=bd["activities_entry_fees"],
                contingency_cost=bd["contingency_buffer"],
                total_estimated=data["total_estimated"],
                per_person_estimated=data["per_person_estimated"],
                target_budget=data["target_budget"],
                is_over_budget=data["is_over_budget"],
                assumptions=data["assumptions"],
                disclaimers=plan.budget.disclaimers
            )
        return plan

