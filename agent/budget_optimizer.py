"""
Budget Optimization & Alternative Package Generator (PRD Section 6.3)
Generates 3 comparative budget tiers (Eco-Saver, Comfort, Deluxe),
computes exact overrun deltas, and suggests trade-offs to fit user budget constraints.
"""

import math
from dataclasses import dataclass
from typing import Dict, Any, List, Optional


@dataclass
class BudgetTierPackage:
    tier_name: str
    description: str
    stay_rate_night: float
    food_rate_day: float
    commute_rate_day: float
    activity_rate_day: float
    total_cost: float
    per_person_cost: float
    status_vs_target: str
    delta_amount: float
    trade_off_notes: List[str]


class BudgetOptimizer:
    """
    Evaluates trip budgets against user limits and generates alternative tier packages (PRD Section 6.3).
    """

    TIER_SPECS = {
        "eco_saver": {
            "name": "Eco-Saver (Budget Homestay & Public Transit)",
            "description": "Clean budget homestay or guest house, public KSRTC buses / shared auto, authentic Kerala messes.",
            "stay_per_night": 1000.0,
            "food_per_person_day": 350.0,
            "commute_per_day": 250.0,
            "activity_per_person_day": 120.0,
        },
        "comfort": {
            "name": "Comfort (3-Star Hotel & Private Auto)",
            "description": "Comfortable 3-star hotel/cottage, dedicated auto or taxi for day trips, mid-range family dining.",
            "stay_per_night": 2200.0,
            "food_per_person_day": 700.0,
            "commute_per_day": 750.0,
            "activity_per_person_day": 250.0,
        },
        "deluxe": {
            "name": "Deluxe (Resort Stay & Chauffeur Cab)",
            "description": "Hill-view eco resort or treehouse, private AC cab throughout, specialty multi-cuisine restaurants.",
            "stay_per_night": 5500.0,
            "food_per_person_day": 1500.0,
            "commute_per_day": 1800.0,
            "activity_per_person_day": 500.0,
        }
    }

    @classmethod
    def generate_alternative_packages(
        cls,
        duration_days: int,
        travelers: int,
        target_budget: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calculates itemized costs for all 3 tiers and returns comparative delta analysis.
        """
        nights = max(1, duration_days - 1)
        rooms = math.ceil(travelers / 2)
        contingency_rate = 0.08  # 8% emergency buffer

        packages: List[BudgetTierPackage] = []
        recommended_tier = "eco_saver"

        for key, spec in cls.TIER_SPECS.items():
            stay_total = spec["stay_per_night"] * nights * rooms
            food_total = spec["food_per_person_day"] * travelers * duration_days
            commute_total = spec["commute_per_day"] * duration_days
            activity_total = spec["activity_per_person_day"] * travelers * duration_days

            subtotal = stay_total + food_total + commute_total + activity_total
            contingency = subtotal * contingency_rate
            total = round(subtotal + contingency, 2)
            per_person = round(total / travelers, 2)

            delta = 0.0
            status = "N/A"
            trade_offs = []

            if target_budget and target_budget > 0:
                if total <= target_budget:
                    delta = round(target_budget - total, 2)
                    status = f"✅ Under Budget (Savings: ₹{delta:,.0f})"
                    recommended_tier = key
                else:
                    delta = round(total - target_budget, 2)
                    status = f"⚠️ Exceeds Budget by ₹{delta:,.0f}"

            if key == "eco_saver":
                trade_offs = [
                    "Saves ~₹1,200/night on stay by choosing certified plantation homestays.",
                    "Saves ~₹500/day on local transport by utilizing state transport buses.",
                    "Food focuses on wholesome local vegetarian/Malabar messes."
                ]
            elif key == "comfort":
                trade_offs = [
                    "Balanced comfort with private room amenities and attached balcony.",
                    "Private local auto/cab eliminates transit wait times."
                ]
            else:
                trade_offs = [
                    "Luxury eco-resort with swimming pool, spa, and plantation treks.",
                    "Dedicated chauffeur vehicle ensures complete route flexibility."
                ]

            packages.append(
                BudgetTierPackage(
                    tier_name=spec["name"],
                    description=spec["description"],
                    stay_rate_night=spec["stay_per_night"],
                    food_rate_day=spec["food_per_person_day"],
                    commute_rate_day=spec["commute_per_day"],
                    activity_rate_day=spec["activity_per_person_day"],
                    total_cost=total,
                    per_person_cost=per_person,
                    status_vs_target=status,
                    delta_amount=delta,
                    trade_off_notes=trade_offs
                )
            )

        return {
            "duration_days": duration_days,
            "travelers": travelers,
            "target_budget": target_budget,
            "packages": packages,
            "recommended_tier": recommended_tier
        }

    @classmethod
    def format_comparison_table(cls, analysis: Dict[str, Any]) -> str:
        """Render a formatted comparison table for display in chat or exports."""
        lines = []
        lines.append("### Comparative Budget Tier Analysis (PRD Section 6.3)")
        if analysis.get("target_budget"):
            lines.append(f"**Target Budget:** ₹{analysis['target_budget']:,.2f} for {analysis['travelers']} traveler(s)")
        lines.append("")
        lines.append("| Tier Package | Total Cost | Per Person | Budget Status |")
        lines.append("| :--- | :--- | :--- | :--- |")

        for pkg in analysis["packages"]:
            lines.append(f"| **{pkg.tier_name.split('(')[0].strip()}** | ₹{pkg.total_cost:,.2f} | ₹{pkg.per_person_cost:,.2f} | {pkg.status_vs_target} |")

        lines.append("\n**Cost-Saving Recommendations:**")
        eco_pkg = analysis["packages"][0]
        for note in eco_pkg.trade_off_notes:
            lines.append(f"- {note}")

        return "\n".join(lines)

