"""
Phase 3 Test Suite: Live Weather Retrieval, Constraint Engine,
Dynamic ReAct Parser, and Operational Hours Optimization.
"""

import os
import shutil
import tempfile
import unittest

from agent.models import UserPreferences, TripPlan, ItineraryDay, Activity
from agent.memory import TripMemoryStore
from agent.tools import ToolRegistry
from agent.tools.weather_service import WeatherService
from agent.constraints import ConstraintEngine
from agent.react_parser import ReActParser, ReActStep
from agent.core_loop import TravelAgentLoop
from agent.safety import ExecutionLogger


class TestPhase3Features(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.memory_path = os.path.join(self.test_dir, "test_memory.json")
        self.memory = TripMemoryStore(storage_path=self.memory_path)
        self.tools = ToolRegistry()
        self.logger = ExecutionLogger(verbose=False)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    # --- 1. Test Live Weather Service (PRD Section 6.7 & Phase 3) ---

    def test_weather_service_forecast(self):
        """Test WeatherService returns valid forecast structure (live or fallback)."""
        weather = WeatherService.get_live_forecast("Wayanad")
        self.assertIn("temperature_celsius", weather)
        self.assertIn("condition", weather)
        self.assertIn("dynamic_advisory", weather)
        self.assertIn("source", weather)
        self.assertIsInstance(weather["temperature_celsius"], (int, float))

    def test_travel_advisory_tool_includes_weather(self):
        """Test Tool 4 get_travel_advisory_and_weather merges live weather data."""
        res = self.tools.execute_tool("get_travel_advisory_and_weather", destination="Wayanad")
        self.assertEqual(res.status, "SUCCESS")
        data = res.data
        self.assertIn("live_weather", data)
        self.assertIn("climate_summary", data)
        self.assertIn("packing_essentials", data)
        self.assertIn("safety_and_rules", data)

    # --- 2. Test Constraint Engine (PRD Section 6.2 & 10) ---

    def test_constraint_closed_days(self):
        """Verify Edakkal Caves is flagged as closed on Mondays."""
        is_open_mon, reason_mon = ConstraintEngine.check_activity_availability("Edakkal Caves", day_of_week="Monday")
        self.assertFalse(is_open_mon)
        self.assertIn("closed on Monday", reason_mon)

        is_open_tue, reason_tue = ConstraintEngine.check_activity_availability("Edakkal Caves", day_of_week="Tuesday")
        self.assertTrue(is_open_tue)
        self.assertIsNone(reason_tue)

    def test_constraint_seasonal_closures(self):
        """Verify Eravikulam National Park is flagged as closed in February/March."""
        is_open_feb, reason_feb = ConstraintEngine.check_activity_availability(
            "Eravikulam National Park Safari", month=2
        )
        self.assertFalse(is_open_feb)
        self.assertIn("calving season", reason_feb)

        is_open_nov, reason_nov = ConstraintEngine.check_activity_availability(
            "Eravikulam National Park Safari", month=11
        )
        self.assertTrue(is_open_nov)

    def test_itinerary_auto_adjustment_for_closures(self):
        """
        Verify that if an activity is scheduled on a day it is closed,
        the constraint engine swaps it with an open activity from another day.
        """
        act_edakkal = Activity(
            title="Edakkal Caves",
            description="Prehistoric rock engravings.",
            time_slot="Morning",
            duration_hours=2.5,
            estimated_cost=40.0,
            location="Wayanad"
        )
        act_lake = Activity(
            title="Pookode Lake",
            description="Scenic freshwater lake.",
            time_slot="Morning",
            duration_hours=1.5,
            estimated_cost=30.0,
            location="Wayanad"
        )

        day1 = ItineraryDay(day_number=1, date_or_label="Day 1", theme="Day 1", activities=[act_edakkal])
        day2 = ItineraryDay(day_number=2, date_or_label="Day 2", theme="Day 2", activities=[act_lake])

        # If trip starts on Monday, Day 1 is Monday (Edakkal is closed!)
        adjusted_days, warnings = ConstraintEngine.validate_and_adjust_itinerary(
            [day1, day2], start_day_of_week="Monday"
        )

        # Edakkal Caves should be moved to Day 2 (Tuesday), Pookode Lake moved to Day 1
        self.assertEqual(adjusted_days[0].activities[0].title, "Pookode Lake")
        self.assertEqual(adjusted_days[1].activities[0].title, "Edakkal Caves")
        self.assertTrue(len(warnings) > 0)
        self.assertIn("Swapped", warnings[0])

    # --- 3. Test ReAct Parser (📘 L1, L3: Think -> Act -> Look) ---

    def test_react_parser_standard(self):
        """Test parsing Thought, Action, and Action Input."""
        text = (
            "Thought: I should search for attractions in Wayanad.\n"
            "Action: search_destination_and_attractions\n"
            "Action Input: {\"destination\": \"Wayanad\", \"max_results\": 4}"
        )
        step = ReActParser.parse(text)
        self.assertFalse(step.is_final)
        self.assertEqual(step.action, "search_destination_and_attractions")
        self.assertEqual(step.action_input["destination"], "Wayanad")
        self.assertEqual(step.action_input["max_results"], 4)
        self.assertIn("search for attractions", step.thought)

    def test_react_parser_final_answer(self):
        """Test parsing Final Answer."""
        text = (
            "Thought: I have finalized the budget and itinerary.\n"
            "Final Answer: Here is your 2-day Wayanad trip plan..."
        )
        step = ReActParser.parse(text)
        self.assertTrue(step.is_final)
        self.assertIn("2-day Wayanad trip plan", step.final_answer)

    # --- 4. End-to-End Integration with Phase 3 Live Features ---

    def test_end_to_end_phase3_trip_planning(self):
        """Verify full loop includes live weather advice and operating hours verification."""
        agent = TravelAgentLoop(memory_store=self.memory, logger=self.logger)
        result = agent.plan_trip(
            user_prompt="Plan a 2-day trip to Wayanad starting on Monday with ₹5,000 budget"
        )

        self.assertEqual(result["status"], "COMPLETED")
        plan: TripPlan = result["trip_plan"]

        # Check live weather is included in travel tips
        weather_tips = [t for t in plan.travel_tips if "Weather" in t]
        self.assertTrue(len(weather_tips) > 0)

        # Check booking disclaimer preserved
        self.assertIn("No bookings are confirmed", plan.booking_disclaimer)


if __name__ == "__main__":
    unittest.main()

