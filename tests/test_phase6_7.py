"""
Phase 6 & 7 Test Suite — Calendar Export, LLM Adapter, Comparator & Packaging
Tests RFC 5545 iCalendar generation, Gemini LLM fallback/adapter, Destination Comparator,
and Docker/CI packaging validity.
"""

import os
import sys
import unittest
from datetime import date

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent.models import TripPlan, ItineraryDay, Activity, BudgetBreakdown
from agent.calendar_export import CalendarExporter
from agent.llm import LLMAdapter, get_llm
from agent.comparator import DestinationComparator


class TestPhase6and7Features(unittest.TestCase):
    """Automated tests for Phase 6 enhancements and Phase 7 deployment integrity."""

    def setUp(self):
        self.sample_trip = TripPlan(
            trip_id="test_phase6_trip",
            destination="Wayanad",
            origin="Bangalore",
            duration_days=2,
            travelers_count=2,
            budget=BudgetBreakdown(
                accommodation_cost=1200.0,
                food_cost=900.0,
                transport_cost=600.0,
                activities_cost=300.0,
                contingency_cost=240.0,
                total_estimated=3240.0,
                target_budget=5000.0
            ),
            days=[
                ItineraryDay(
                    day_number=1,
                    date_or_label="Day 1",
                    theme="Nature & Adventure",
                    activities=[
                        Activity(
                            title="Banasura Sagar Dam",
                            description="Largest earthen dam in India.",
                            time_slot="Morning",
                            duration_hours=2.5,
                            estimated_cost=50.0,
                            location="Padinjarathara",
                            notes="Boating available."
                        )
                    ],
                    transit_notes="Local cab or auto"
                ),
                ItineraryDay(
                    day_number=2,
                    date_or_label="Day 2",
                    theme="Heritage & History",
                    activities=[
                        Activity(
                            title="Edakkal Caves",
                            description="Prehistoric petroglyphs.",
                            time_slot="Morning",
                            duration_hours=3.0,
                            estimated_cost=40.0,
                            location="Sulthan Bathery"
                        )
                    ],
                    transit_notes="Local bus to Ambalavayal"
                )
            ],
            travel_tips=["Wear good walking shoes.", "Night ban active on NH-766."]
        )

    def test_calendar_exporter_creates_valid_ics(self):
        """Verify CalendarExporter outputs valid RFC 5545 iCalendar (.ics) format."""
        out_dir = os.path.join(os.path.dirname(__file__), "..", "exports")
        ics_path = CalendarExporter.export(self.sample_trip, start_date=date(2026, 12, 1), output_dir=out_dir)

        self.assertTrue(os.path.exists(ics_path), "ICS file should exist on disk")
        with open(ics_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("BEGIN:VCALENDAR", content)
        self.assertIn("VERSION:2.0", content)
        self.assertIn("BEGIN:VEVENT", content)
        self.assertIn("Banasura Sagar Dam", content)
        self.assertIn("Edakkal Caves", content)
        self.assertIn("END:VCALENDAR", content)

    def test_llm_adapter_rule_based_fallback(self):
        """Verify LLMAdapter works reliably without an API key using rule-based fallback."""
        llm = LLMAdapter(api_key="")
        resp = llm.generate("Summarise Wayanad for travellers")
        self.assertFalse(resp.via_api)
        self.assertIn("Wayanad", resp.text)
        self.assertIn("Kerala", resp.text)

    def test_llm_adapter_budget_advice(self):
        """Verify LLM fallback answers budget travel queries."""
        llm = LLMAdapter(api_key="")
        resp = llm.generate("What is the estimated budget guidance?")
        self.assertIn("Economy", resp.text)
        self.assertIn("Comfort", resp.text)

    def test_destination_comparator_two_destinations(self):
        """Verify DestinationComparator computes scores and generates comparison table."""
        res = DestinationComparator.compare(
            dest_a="Wayanad",
            dest_b="Coorg",
            target_budget=5000.0,
            travelers=2
        )

        self.assertIn("winner", res)
        self.assertIn("comparison_table", res)
        self.assertIn("recommendation", res)
        self.assertIn("Wayanad", res["comparison_table"])
        self.assertIn("Coorg", res["comparison_table"])
        self.assertGreater(res["dest_a"]["score"]["total"], 0)
        self.assertGreater(res["dest_b"]["score"]["total"], 0)

    def test_dockerfile_and_ci_present(self):
        """Verify Phase 7 deployment files exist."""
        root = os.path.join(os.path.dirname(__file__), "..")
        self.assertTrue(os.path.exists(os.path.join(root, "Dockerfile")), "Dockerfile missing")
        self.assertTrue(os.path.exists(os.path.join(root, "docker-compose.yml")), "docker-compose.yml missing")
        self.assertTrue(os.path.exists(os.path.join(root, ".dockerignore")), ".dockerignore missing")
        self.assertTrue(os.path.exists(os.path.join(root, ".github", "workflows", "ci.yml")), "CI workflow missing")


if __name__ == "__main__":
    unittest.main(verbosity=2)
