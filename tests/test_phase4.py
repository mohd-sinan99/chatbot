"""
Phase 4 Test Suite: Geographic Clustering, Pacing Engine,
Budget Optimizer with Alternative Tiers, and Multi-Format Exporters.
"""

import os
import shutil
import tempfile
import unittest

from agent.models import UserPreferences, TripPlan, ItineraryDay, Activity, BudgetBreakdown
from agent.memory import TripMemoryStore
from agent.tools import ToolRegistry
from agent.pacing import PacingEngine
from agent.budget_optimizer import BudgetOptimizer
from agent.exporter import ItineraryExporter
from agent.conversation import ConversationalAgent
from agent.safety import ExecutionLogger


class TestPhase4Features(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.memory_path = os.path.join(self.test_dir, "test_memory.json")
        self.export_dir = os.path.join(self.test_dir, "exports")
        self.memory = TripMemoryStore(storage_path=self.memory_path)
        self.tools = ToolRegistry()
        self.logger = ExecutionLogger(verbose=False)
        self.agent = ConversationalAgent(
            memory_store=self.memory,
            tool_registry=self.tools,
            logger=self.logger
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    # --- 1. Test Geographic Clustering & Pacing Engine (PRD Section 6.2 & 6.5) ---

    def test_attraction_zone_mapping(self):
        """Verify attractions are mapped to their correct regional geographic zone."""
        zone_dam = PacingEngine.get_attraction_zone("Wayanad", "Banasura Sagar Dam")
        self.assertEqual(zone_dam, "west_vythiri")

        zone_caves = PacingEngine.get_attraction_zone("Wayanad", "Edakkal Caves")
        self.assertEqual(zone_caves, "east_sulthan_bathery")

        zone_falls = PacingEngine.get_attraction_zone("Wayanad", "Soochipara Waterfalls")
        self.assertEqual(zone_falls, "south_meppadi")

    def test_schedule_paced_days_with_dietary_filter(self):
        """Verify scheduling clusters attractions, includes lunch notes, and applies dietary filters."""
        attractions = [
            {"name": "Banasura Sagar Dam", "description": "Large dam", "entry_fee": 50.0, "duration_hours": 2.5},
            {"name": "Pookode Lake", "description": "Freshwater lake", "entry_fee": 30.0, "duration_hours": 1.5},
            {"name": "Edakkal Caves", "description": "Neolithic caves", "entry_fee": 40.0, "duration_hours": 3.0},
        ]
        eateries = [
            {"name": "Malabar Non-Veg Special", "cuisine": "Non-Vegetarian", "location": "Kalpetta", "approx_cost_for_two": 400.0},
            {"name": "Udupi Vegetarian Mess", "cuisine": "Pure Vegetarian", "location": "Kalpetta", "approx_cost_for_two": 200.0},
        ]

        days = PacingEngine.schedule_paced_days(
            destination="Wayanad",
            attractions=attractions,
            duration_days=2,
            eateries=eateries,
            dietary_preference="Vegetarian"
        )

        self.assertEqual(len(days), 2)
        # Check that activities count is reasonable
        for day in days:
            self.assertTrue(1 <= len(day.activities) <= 3)

        # Check that vegetarian restaurant was selected in transit notes
        all_notes = " ".join(d.transit_notes for d in days)
        self.assertIn("Udupi Vegetarian Mess", all_notes)
        self.assertNotIn("Malabar Non-Veg Special", all_notes)

    # --- 2. Test Budget Optimizer & Alternative Tiers (PRD Section 6.3) ---

    def test_budget_optimizer_packages(self):
        """Verify BudgetOptimizer generates Eco-Saver, Comfort, and Deluxe packages."""
        analysis = BudgetOptimizer.generate_alternative_packages(
            duration_days=2,
            travelers=2,
            target_budget=5000.0
        )
        self.assertEqual(len(analysis["packages"]), 3)
        tiers = [p.tier_name for p in analysis["packages"]]
        self.assertTrue(any("Eco-Saver" in t for t in tiers))
        self.assertTrue(any("Comfort" in t for t in tiers))
        self.assertTrue(any("Deluxe" in t for t in tiers))

        eco_pkg = analysis["packages"][0]
        self.assertLess(eco_pkg.total_cost, 5000.0)
        self.assertIn("Under Budget", eco_pkg.status_vs_target)
        self.assertTrue(len(eco_pkg.trade_off_notes) > 0)

    def test_budget_optimizer_overrun_tradeoffs(self):
        """Verify BudgetOptimizer flags overruns on low budgets and suggests trade-offs."""
        # Tight budget of ₹2,000 for 2 days
        analysis = BudgetOptimizer.generate_alternative_packages(
            duration_days=2,
            travelers=2,
            target_budget=2000.0
        )
        deluxe_pkg = analysis["packages"][2]
        self.assertIn("Exceeds Budget", deluxe_pkg.status_vs_target)

        table_md = BudgetOptimizer.format_comparison_table(analysis)
        self.assertIn("Comparative Budget Tier Analysis", table_md)
        self.assertIn("Cost-Saving Recommendations", table_md)

    # --- 3. Test Itinerary Exporters (PRD Section 12) ---

    def test_itinerary_exporters(self):
        """Verify exporting plan to Markdown, JSON, and HTML files."""
        day = ItineraryDay(
            day_number=1,
            date_or_label="Day 1",
            theme="Scenic Lakes",
            activities=[
                Activity(
                    title="Banasura Sagar Dam",
                    description="Largest dam",
                    time_slot="Morning",
                    duration_hours=2.5,
                    estimated_cost=50.0,
                    location="Wayanad"
                )
            ],
            transit_notes="Auto transit"
        )
        budget = BudgetBreakdown(
            currency="INR",
            total_estimated=4500.0,
            per_person_estimated=2250.0,
            target_budget=5000.0,
            assumptions=["1 night homestay"]
        )
        plan = TripPlan(
            trip_id="test_exp_01",
            destination="Wayanad",
            origin="Bangalore",
            duration_days=1,
            travelers_count=2,
            days=[day],
            budget=budget,
            travel_tips=["Bring camera"],
            safety_advisories=["Follow forest rules"]
        )

        exported = ItineraryExporter.export_all(plan, output_dir=self.export_dir)

        # Check all 3 files exist and have content
        for fmt, path in exported.items():
            self.assertTrue(os.path.exists(path), f"File {path} not found")
            self.assertGreater(os.path.getsize(path), 100, f"File {path} is empty")

        # Verify HTML has styling and content
        with open(exported["html"], "r", encoding="utf-8") as f:
            html_text = f.read()
            self.assertIn("WAYANAD ITINERARY", html_text)
            self.assertIn("Banasura Sagar Dam", html_text)
            self.assertIn("No bookings are confirmed", html_text)

    # --- 4. Test Export and Budget Commands in Conversation Agent ---

    def test_conversational_export_and_budget_commands(self):
        """Test user typing 'export' and 'compare budget' in conversation."""
        # First generate a trip
        self.agent.process_message("Plan a 2-day trip to Wayanad with ₹5,000 budget")

        # Request export
        exp_res = self.agent.process_message("Export my itinerary")
        self.assertEqual(exp_res["type"], "TRIP_EXPORTED")
        self.assertIn("files", exp_res)
        self.assertTrue(os.path.exists(exp_res["files"]["html"]))

        # Request budget comparison
        b_res = self.agent.process_message("Compare budget packages")
        self.assertEqual(b_res["type"], "BUDGET_COMPARISON")
        self.assertIn("Comparative Budget Tier Analysis", b_res["content"])


if __name__ == "__main__":
    unittest.main()

