"""
Destination Comparator (Phase 6 — PRD Section 6.1: Compare destination options)
Provides side-by-side comparison of two trip destinations across budget, activities,
travel time, weather suitability, and overall fit score.
"""

from typing import Dict, Any, List, Optional, Tuple
from agent.tools.destination_tool import DestinationSearchTool


class DestinationComparator:
    """
    Compare two destinations across multiple dimensions and produce a
    structured comparison report with a recommendation.
    """

    # Scoring weights (must sum to 1.0)
    WEIGHTS = {
        "budget_fit":     0.30,   # How well it fits ₹5,000 target
        "activity_count": 0.20,   # Breadth of attractions
        "travel_ease":    0.20,   # Distance from Bangalore
        "veg_friendliness": 0.15, # Vegetarian dining options
        "family_score":   0.15,   # Family/group suitability
    }

    # Rough distances from Bangalore in km (for scoring)
    DISTANCE_KM: Dict[str, float] = {
        "wayanad": 280.0,
        "coorg":   250.0,
        "munnar":  480.0,
        "alleppey": 600.0,
        "thekkady": 460.0,
        "ooty":     270.0,
        "goa":      570.0,
    }

    # Approximate budget for 2 pax (2 nights baseline)
    BUDGET_FOR_TWO: Dict[str, float] = {
        "wayanad": 4500.0,
        "coorg":   5000.0,
        "munnar":  7500.0,
        "alleppey": 6500.0,
        "thekkady": 5500.0,
        "ooty":    5000.0,
        "goa":     8000.0,
    }

    @classmethod
    def compare(
        cls,
        dest_a: str,
        dest_b: str,
        target_budget: float = 5000.0,
        travelers: int = 2,
        dietary_pref: str = "any",
    ) -> Dict[str, Any]:
        """
        Compare two destinations and return a structured report.

        Args:
            dest_a: First destination name (e.g. "Wayanad").
            dest_b: Second destination name (e.g. "Coorg").
            target_budget: User's total budget (₹).
            travelers: Number of travellers.
            dietary_pref: "vegetarian", "vegan", or "any".

        Returns:
            Dict with keys: 'dest_a', 'dest_b', 'scores', 'winner',
            'comparison_table', 'recommendation'.
        """
        key_a = dest_a.strip().lower().split()[0]
        key_b = dest_b.strip().lower().split()[0]

        data_a = cls._gather_data(key_a, dest_a, target_budget, travelers, dietary_pref)
        data_b = cls._gather_data(key_b, dest_b, target_budget, travelers, dietary_pref)

        score_a = cls._score(data_a, target_budget)
        score_b = cls._score(data_b, target_budget)

        winner = dest_a if score_a["total"] >= score_b["total"] else dest_b
        reason = cls._explain_winner(data_a, data_b, score_a, score_b, winner, target_budget)

        table = cls._build_table(dest_a, dest_b, data_a, data_b, score_a, score_b)

        return {
            "dest_a": {"name": dest_a, "data": data_a, "score": score_a},
            "dest_b": {"name": dest_b, "data": data_b, "score": score_b},
            "winner": winner,
            "recommendation": reason,
            "comparison_table": table,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @classmethod
    def _gather_data(
        cls,
        key: str,
        label: str,
        budget: float,
        travelers: int,
        dietary: str,
    ) -> Dict[str, Any]:
        """Pull destination data from DestinationSearchTool knowledge base."""
        tool_result = DestinationSearchTool().execute(destination=label)

        attractions = tool_result.get("attractions", [])
        eateries = tool_result.get("recommended_eateries", [])
        accoms = tool_result.get("accommodation_suggestions", [])

        # Veg-friendly eateries
        veg_eateries = [
            e for e in eateries
            if any(
                word in e.get("cuisine", "").lower()
                for word in ("vegetarian", "veg", "udupi", "saravana", "pure")
            )
        ]

        budget_for_two = cls.BUDGET_FOR_TWO.get(key, budget)
        distance = cls.DISTANCE_KM.get(key, 400.0)
        cheapest_stay = min(
            (a.get("approx_rate_per_night", 1500) for a in accoms),
            default=1500,
        )

        return {
            "key": key,
            "label": label,
            "attraction_count": len(attractions),
            "eatery_count": len(eateries),
            "veg_eatery_count": len(veg_eateries),
            "accommodation_count": len(accoms),
            "cheapest_stay_per_night": cheapest_stay,
            "budget_for_two": budget_for_two,
            "distance_km": distance,
            "attractions": attractions,
            "eateries": eateries,
        }

    @classmethod
    def _score(cls, data: Dict[str, Any], target_budget: float) -> Dict[str, float]:
        """Produce normalised 0–10 scores per dimension."""
        # Budget fit: 10 if on-budget, decays as over-budget %
        ratio = data["budget_for_two"] / max(target_budget, 1)
        budget_fit = max(0.0, 10.0 - (ratio - 1.0) * 10.0) if ratio > 1 else 10.0

        # Activity count: score out of 10 (5 attractions = max)
        act_score = min(10.0, data["attraction_count"] * 2.0)

        # Travel ease: 10 for ≤250 km, decays by 1 point per 50 km over
        excess_km = max(0.0, data["distance_km"] - 250.0)
        travel_score = max(0.0, 10.0 - (excess_km / 50.0))

        # Veg friendliness: 10 if any veg options, 5 if none
        veg_score = 10.0 if data["veg_eatery_count"] > 0 else 5.0

        # Family score heuristic: more attractions + cheap stays = better
        family_score = min(
            10.0,
            (data["attraction_count"] * 1.5) + max(0, (2000 - data["cheapest_stay_per_night"]) / 200)
        )

        raw = {
            "budget_fit": budget_fit,
            "activity_count": act_score,
            "travel_ease": travel_score,
            "veg_friendliness": veg_score,
            "family_score": family_score,
        }

        total = sum(raw[k] * cls.WEIGHTS[k] for k in cls.WEIGHTS)
        return {**raw, "total": round(total, 2)}

    @staticmethod
    def _explain_winner(
        data_a: Dict, data_b: Dict,
        score_a: Dict, score_b: Dict,
        winner: str,
        target_budget: float,
    ) -> str:
        """Generate a human-readable recommendation paragraph."""
        d = data_a if winner == data_a["label"] else data_b
        s = score_a if winner == data_a["label"] else score_b
        other_d = data_b if winner == data_a["label"] else data_a
        other_s = score_b if winner == data_a["label"] else score_a

        budget_note = ""
        if d["budget_for_two"] <= target_budget:
            budget_note = f"fits comfortably within your ₹{target_budget:,.0f} budget"
        else:
            over = d["budget_for_two"] - target_budget
            budget_note = f"runs ~₹{over:,.0f} over your ₹{target_budget:,.0f} budget"

        margin = abs(s["total"] - other_s["total"])
        strength = "clearly better" if margin > 1.5 else "slightly better"

        return (
            f"**{winner}** is the {strength} choice overall (score: {s['total']:.1f}/10 vs "
            f"{other_s['total']:.1f}/10). It {budget_note}, offers "
            f"{d['attraction_count']} attractions, and is approximately "
            f"{d['distance_km']:.0f} km from Bangalore. "
            f"{'Vegetarian dining options are available.' if d['veg_eatery_count'] > 0 else 'Vegetarian options may be limited — verify locally.'} "
            f"All prices are estimates; confirm with providers before booking."
        )

    @staticmethod
    def _build_table(
        dest_a: str, dest_b: str,
        data_a: Dict, data_b: Dict,
        score_a: Dict, score_b: Dict,
    ) -> str:
        """Build a markdown comparison table."""
        def fmt_budget(d):
            return f"₹{d['budget_for_two']:,.0f} for 2"

        def fmt_dist(d):
            return f"~{d['distance_km']:.0f} km"

        def fmt_veg(d):
            return "✅ Yes" if d["veg_eatery_count"] > 0 else "⚠️  Limited"

        rows = [
            ("Category", dest_a, dest_b),
            ("Estimated Budget (2 pax)", fmt_budget(data_a), fmt_budget(data_b)),
            ("Attractions", str(data_a["attraction_count"]), str(data_b["attraction_count"])),
            ("Distance from Bangalore", fmt_dist(data_a), fmt_dist(data_b)),
            ("Vegetarian Dining", fmt_veg(data_a), fmt_veg(data_b)),
            ("Cheapest Stay/Night", f"₹{data_a['cheapest_stay_per_night']:,.0f}", f"₹{data_b['cheapest_stay_per_night']:,.0f}"),
            ("🏆 Overall Score (/ 10)", f"{score_a['total']:.1f}", f"{score_b['total']:.1f}"),
        ]

        col_widths = [max(len(r[i]) for r in rows) for i in range(3)]
        sep = "| " + " | ".join("-" * w for w in col_widths) + " |"

        lines = []
        for i, row in enumerate(rows):
            line = "| " + " | ".join(str(row[j]).ljust(col_widths[j]) for j in range(3)) + " |"
            lines.append(line)
            if i == 0:  # header separator
                lines.append(sep)

        return "\n".join(lines)

    @classmethod
    def format_report(cls, result: Dict[str, Any]) -> str:
        """Format the comparison result as a readable markdown string."""
        lines = [
            f"## 🗺️  Destination Comparison: {result['dest_a']['name']} vs {result['dest_b']['name']}\n",
            result["comparison_table"],
            "",
            f"### 🎯 Recommendation\n{result['recommendation']}",
            "",
            "> ⚠️  All prices, distances, and scores are estimates. Verify with official sources before booking.",
        ]
        return "\n".join(lines)

