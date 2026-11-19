"""
Itinerary Export Engine (PRD Section 12 & Phase 4)
Generates clean export files in Markdown (.md), JSON (.json), and Print-Ready HTML (.html).
"""

import os
import json
from typing import Dict, Any, Optional
from agent.models import TripPlan


class ItineraryExporter:
    """Exports structured trip plans to Markdown, JSON, and styled HTML."""

    @classmethod
    def export_all(cls, plan: TripPlan, output_dir: str = "exports") -> Dict[str, str]:
        """Export plan to Markdown, JSON, and HTML in the specified directory."""
        os.makedirs(output_dir, exist_ok=True)
        base_name = f"{plan.destination.lower()}_{plan.duration_days}d_itinerary"

        md_path = os.path.join(output_dir, f"{base_name}.md")
        json_path = os.path.join(output_dir, f"{base_name}.json")
        html_path = os.path.join(output_dir, f"{base_name}.html")

        cls.export_markdown(plan, md_path)
        cls.export_json(plan, json_path)
        cls.export_html(plan, html_path)

        return {
            "markdown": md_path,
            "json": json_path,
            "html": html_path,
        }

    @classmethod
    def export_markdown(cls, plan: TripPlan, filepath: str) -> str:
        """Render itinerary as standard Markdown."""
        lines = []
        lines.append(f"# Trip Itinerary: {plan.destination.title()} ({plan.duration_days} Days)")
        if plan.origin:
            lines.append(f"**Origin:** {plan.origin} | **Travelers:** {plan.travelers_count}")
        lines.append("")

        # Schedule
        lines.append("## 📅 Day-by-Day Schedule")
        for day in plan.days:
            lines.append(f"### Day {day.day_number}: {day.theme}")
            for act in day.activities:
                lines.append(f"- **{act.time_slot}**: {act.title}")
                lines.append(f"  - *Details:* {act.description}")
                lines.append(f"  - *Cost:* ₹{act.estimated_cost:,.0f} | *Duration:* ~{act.duration_hours} hrs")
                if act.opening_hours:
                    lines.append(f"  - *Hours:* {act.opening_hours}")
                if act.source_url:
                    lines.append(f"  - *Source:* [{act.source_url}]({act.source_url})")
            if day.transit_notes:
                lines.append(f"  - *Transit Notes:* {day.transit_notes}")
            lines.append("")

        # Budget
        b = plan.budget
        lines.append("## 💰 Estimated Budget Breakdown")
        lines.append(f"| Category | Estimated Cost ({b.currency}) |")
        lines.append("| :--- | :--- |")
        lines.append(f"| Accommodation | ₹{b.accommodation_cost:,.2f} |")
        lines.append(f"| Food & Dining | ₹{b.food_cost:,.2f} |")
        lines.append(f"| Local Transit | ₹{b.transport_cost:,.2f} |")
        lines.append(f"| Sightseeing & Fees | ₹{b.activities_cost:,.2f} |")
        lines.append(f"| Contingency Buffer (8%) | ₹{b.contingency_cost:,.2f} |")
        lines.append(f"| **Total Estimated** | **₹{b.total_estimated:,.2f}** |")
        lines.append(f"| **Per Person** | **₹{b.per_person_estimated:,.2f}** |")
        if b.target_budget:
            lines.append(f"| **Target Budget** | **₹{b.target_budget:,.2f}** |")
        lines.append("")

        if b.assumptions:
            lines.append("### Key Budget Assumptions")
            for asm in b.assumptions:
                lines.append(f"- {asm}")
            lines.append("")

        # Tips
        lines.append("## 🛡️ Travel Tips & Safety")
        for tip in plan.travel_tips:
            lines.append(f"- {tip}")
        for safe in plan.safety_advisories:
            lines.append(f"- ⚠️ {safe}")
        lines.append("")

        # Disclaimer
        lines.append("## ⚠️ Notice & Disclaimer")
        lines.append(f"> {plan.booking_disclaimer}")

        content = "\n".join(lines)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return filepath

    @classmethod
    def export_json(cls, plan: TripPlan, filepath: str) -> str:
        """Export plan to formatted JSON."""
        data = plan.to_dict()
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return filepath

    @classmethod
    def export_html(cls, plan: TripPlan, filepath: str) -> str:
        """Generate a clean, responsive, print-ready HTML page."""
        b = plan.budget
        status_badge = (
            "<span style='color: #dc2626; background: #fee2e2; padding: 4px 8px; border-radius: 4px; font-weight: bold;'>⚠️ Over Budget</span>"
            if b.is_over_budget
            else "<span style='color: #16a34a; background: #dcfce7; padding: 4px 8px; border-radius: 4px; font-weight: bold;'>✅ Within Budget</span>"
        )

        days_html = []
        for day in plan.days:
            acts_html = []
            for act in day.activities:
                acts_html.append(f"""
                <div style="margin-bottom: 12px; padding: 10px; background: #f8fafc; border-left: 4px solid #3b82f6; border-radius: 4px;">
                    <div style="font-weight: bold; color: #1e293b;">{act.time_slot}: {act.title}</div>
                    <div style="font-size: 0.9em; color: #475569; margin: 4px 0;">{act.description}</div>
                    <div style="font-size: 0.85em; color: #64748b;">
                        Cost: <strong>₹{act.estimated_cost:,.0f}</strong> &bull; Duration: ~{act.duration_hours} hrs
                        {f'&bull; Hours: {act.opening_hours}' if act.opening_hours else ''}
                    </div>
                </div>
                """)
            days_html.append(f"""
            <div style="margin-bottom: 24px; padding: 16px; border: 1px solid #e2e8f0; border-radius: 8px;">
                <h3 style="margin-top: 0; color: #0f172a;">Day {day.day_number}: {day.theme}</h3>
                {''.join(acts_html)}
                {f'<p style="font-size: 0.85em; color: #64748b; font-style: italic;">🚗 {day.transit_notes}</p>' if day.transit_notes else ''}
            </div>
            """)

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Trip Itinerary - {plan.destination}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.5; color: #1e293b; max-width: 850px; margin: 40px auto; padding: 0 20px; }}
        h1 {{ color: #0f172a; margin-bottom: 4px; }}
        .header-meta {{ color: #64748b; margin-bottom: 24px; font-size: 0.95em; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #e2e8f0; }}
        th {{ background: #f1f5f9; }}
        .disclaimer-box {{ background: #fffbeb; border: 1px solid #fef3c7; border-left: 4px solid #f59e0b; padding: 12px; border-radius: 4px; margin-top: 24px; font-size: 0.9em; }}
        @media print {{ body {{ margin: 0; }} }}
    </style>
</head>
<body>
    <h1>✈️ {plan.destination.upper()} ITINERARY</h1>
    <div class="header-meta">
        <strong>Duration:</strong> {plan.duration_days} Days &bull; 
        <strong>Travelers:</strong> {plan.travelers_count} &bull; 
        <strong>Origin:</strong> {plan.origin or 'N/A'}
    </div>

    <h2>📅 Daily Schedule</h2>
    {''.join(days_html)}

    <h2>💰 Budget Breakdown</h2>
    <table>
        <tr><th>Category</th><th>Estimated Amount ({b.currency})</th></tr>
        <tr><td>Accommodation</td><td>₹{b.accommodation_cost:,.2f}</td></tr>
        <tr><td>Food & Dining</td><td>₹{b.food_cost:,.2f}</td></tr>
        <tr><td>Local Transit</td><td>₹{b.transport_cost:,.2f}</td></tr>
        <tr><td>Sightseeing & Entry Fees</td><td>₹{b.activities_cost:,.2f}</td></tr>
        <tr><td>Contingency Buffer (8%)</td><td>₹{b.contingency_cost:,.2f}</td></tr>
        <tr style="font-weight: bold; background: #f8fafc;"><td>Total Estimated</td><td>₹{b.total_estimated:,.2f} ({status_badge})</td></tr>
        <tr style="font-weight: bold;"><td>Per Person</td><td>₹{b.per_person_estimated:,.2f}</td></tr>
    </table>

    <h2>🛡️ Packing & Safety Advisories</h2>
    <ul>
        {''.join(f'<li>{t}</li>' for t in plan.travel_tips)}
        {''.join(f'<li>⚠️ {s}</li>' for s in plan.safety_advisories)}
    </ul>

    <div class="disclaimer-box">
        <strong>Important Notice:</strong> {plan.booking_disclaimer}
    </div>
</body>
</html>"""

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)
        return filepath

