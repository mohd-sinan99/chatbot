"""
Phase 2 Test Suite: Intent Routing, Single-Question Clarification,
Delta Itinerary Refinement, and Destination/Food Recommendations.
"""

import os
import shutil
import tempfile
import unittest

from agent.models import UserPreferences, TripPlan
from agent.memory import TripMemoryStore
from agent.router import IntentRouter, UserIntent
from agent.refiner import DeltaPlanRefiner
from agent.conversation import ConversationalAgent
from agent.tools import ToolRegistry
from agent.tools.destination_tool import DestinationSearchTool
from agent.safety import ExecutionLogger


class TestPhase2Features(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.memory_path = os.path.join(self.test_dir, "test_memory.json")
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

    # --- 1. Test Intent Classification (PRD Section 8) ---

    def test_intent_classification(self):
        """Test classifying diverse user travel intents."""
        self.assertEqual(
            IntentRouter.classify_intent("Plan a 2-day trip to Wayanad"),
            UserIntent.NEW_TRIP
        )
        self.assertEqual(
            IntentRouter.classify_intent("Suggest destination ideas from Bangalore"),
            UserIntent.EXPLORE_DESTINATIONS
        )
        self.assertEqual(
            IntentRouter.classify_intent("Make day 2 more relaxing", has_active_trip=True),
            UserIntent.REFINE_PLAN
        )
        self.assertEqual(
            IntentRouter.classify_intent("Hello, what can you do?"),
            UserIntent.GENERAL_QUERY
        )

    # --- 2. Test Single-Question Clarification (PRD Section 7 & 11) ---

    def test_single_question_clarification_flow(self):
        """
        Verify agent asks only one clear question at a time when essential details are missing.
        Step 1: User says 'Plan a trip for 2 people' (Missing destination)
        Step 2: Agent asks for destination.
        Step 3: User answers 'Wayanad' (Missing duration)
        Step 4: Agent asks for duration.
        Step 5: User answers '2 days' -> Agent generates trip!
        """
        # Step 1: Missing destination
        res1 = self.agent.process_message("Plan a trip for two people")
        self.assertEqual(res1["type"], "CLARIFICATION_REQUIRED")
        self.assertIn("Where would you like to travel", res1["question"])

        # Step 2: Answer destination
        res2 = self.agent.process_message("Wayanad")
        self.assertEqual(res2["type"], "CLARIFICATION_REQUIRED")
        self.assertIn("How many days", res2["question"])

        # Step 3: Answer duration
        res3 = self.agent.process_message("2 days")
        self.assertEqual(res3["type"], "TRIP_GENERATED")
        plan = res3["trip_plan"]
        self.assertEqual(plan.destination, "Wayanad")
        self.assertEqual(plan.duration_days, 2)

    # --- 3. Test Delta Itinerary Refinement (PRD Section 6.8 & Core Use Case 6) ---

    def test_delta_plan_refinement(self):
        """
        Verify that user can modify parts of an active trip (e.g. Day 1 relaxing)
        without resetting Day 2 or unchanged fields.
        """
        # 1. Generate initial trip
        gen_res = self.agent.process_message("Plan a two-day trip to Wayanad for two people with ₹5,000 budget")
        self.assertEqual(gen_res["type"], "TRIP_GENERATED")
        initial_plan: TripPlan = gen_res["trip_plan"]
        original_day2_title = initial_plan.days[1].activities[0].title

        # 2. Request delta modification
        mod_res = self.agent.process_message("Make day 1 more relaxing with lake walk")
        self.assertEqual(mod_res["type"], "PLAN_UPDATED")
        updated_plan: TripPlan = mod_res["trip_plan"]

        # Day 1 should be updated
        self.assertIn("Relaxing", updated_plan.days[0].theme)
        self.assertIn("Lake Walk", updated_plan.days[0].activities[0].title)

        # Day 2 must remain completely intact!
        self.assertEqual(updated_plan.days[1].activities[0].title, original_day2_title)

        # Change summary must explain what changed
        self.assertIn("Day 1", mod_res["summary"])

    # --- 4. Test Accommodation & Food Suggestions (PRD Section 6.4 & 6.5) ---

    def test_food_and_accommodation_data(self):
        """Verify destination tool provides authentic eateries and accommodations with disclaimers."""
        res = self.tools.execute_tool("search_destination_and_attractions", destination="Wayanad")
        self.assertEqual(res.status, "SUCCESS")
        data = res.data

        # Food (PRD Section 6.5)
        eateries = data.get("recommended_eateries", [])
        self.assertTrue(len(eateries) >= 2)
        names = [e["name"] for e in eateries]
        self.assertTrue(any("1980" in n or "Udupi" in n for n in names))

        # Accommodations (PRD Section 6.4)
        acc = data.get("accommodation_suggestions", [])
        self.assertTrue(len(acc) >= 1)
        self.assertIn("approx_rate_per_night", acc[0])
        self.assertIn("booking_link", acc[0])

    # --- 5. Test Destination Recommendations (PRD Section 6.1) ---

    def test_destination_exploration(self):
        """Verify destination finder recommends relevant places matching origin and budget."""
        res = self.agent.process_message("Suggest weekend getaway ideas from Bangalore")
        self.assertEqual(res["type"], "DESTINATION_RECOMMENDATIONS")
        self.assertIn("Wayanad", res["content"])
        self.assertIn("Coorg", res["content"])


if __name__ == "__main__":
    unittest.main()
