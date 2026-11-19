"""
Deterministic Test Suite with Fake/Mock Simulation (📘 L8: Fake LLM First)
Validates:
- ReAct Loop (Think -> Act -> Look 📘 L1, L3)
- Tool Schemas & Execution (📘 L2)
- Tool Error Catching & Recovery (📘 L2)
- Persistent Memory across Tasks (📘 L4)
- Pre-Execution Plan Tracking (📘 L5)
- Safety: Asks You First, Step Limit, Audit Logging (📘 L7)
- PRD Acceptance Criteria & Disclaimers
"""

import os
import shutil
import tempfile
import unittest

from agent.models import UserPreferences, TripPlan, BudgetBreakdown
from agent.memory import TripMemoryStore
from agent.tools import ToolRegistry, ToolResult
from agent.planner import PlannerEngine, StepStatus
from agent.safety import SafetyGuardrails, ExecutionLogger
from agent.core_loop import TravelAgentLoop


class FakeLLMBackend:
    """
    Mock LLM backend that returns scripted reasoning and tool decisions (📘 L8).
    Allows running entire agent loop deterministically without external API calls or keys.
    """

    def __init__(self, scripted_responses=None):
        self.scripted_responses = scripted_responses or []
        self.call_history = []

    def generate(self, prompt: str) -> str:
        self.call_history.append(prompt)
        if self.scripted_responses:
            return self.scripted_responses.pop(0)
        return "THOUGHT: Proceed with next step.\nACTION: None"


class TestSmartTravelPlannerAgent(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.memory_path = os.path.join(self.test_dir, "test_memory.json")
        self.memory = TripMemoryStore(storage_path=self.memory_path)
        self.tools = ToolRegistry()
        self.logger = ExecutionLogger(verbose=False)  # Silent during unit tests
        self.fake_llm = FakeLLMBackend()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    # --- 1. Test 2–4 Tools Description & Execution (📘 L2) ---

    def test_tools_registered_and_described(self):
        """Verify exactly 4 core tools are registered with schemas (L2)."""
        tool_names = self.tools.list_tool_names()
        self.assertEqual(len(tool_names), 4)
        self.assertIn("search_destination_and_attractions", tool_names)
        self.assertIn("calculate_budget_breakdown", tool_names)
        self.assertIn("find_transport_options", tool_names)
        self.assertIn("get_travel_advisory_and_weather", tool_names)

        # Check schemas have required fields
        for name in tool_names:
            tool = self.tools.get_tool(name)
            self.assertIsNotNone(tool)
            self.assertTrue(len(tool.description) > 10)
            self.assertIn("type", tool.parameters_schema)

    def test_destination_tool_execution(self):
        """Test search_destination_and_attractions tool returns verified sights."""
        res = self.tools.execute_tool("search_destination_and_attractions", destination="Wayanad")
        self.assertEqual(res.status, "SUCCESS")
        self.assertIn("attractions", res.data)
        self.assertTrue(len(res.data["attractions"]) >= 2)
        # Check that Banasura or Edakkal is found
        titles = [a["name"] for a in res.data["attractions"]]
        self.assertTrue(any("Banasura" in t or "Edakkal" in t for t in titles))

    def test_budget_calculator_tool(self):
        """Test calculate_budget_breakdown computes math accurately."""
        res = self.tools.execute_tool(
            "calculate_budget_breakdown",
            destination="Wayanad",
            duration_days=2,
            travelers=2,
            tier="budget",
            target_budget=5000.0
        )
        self.assertEqual(res.status, "SUCCESS")
        data = res.data
        self.assertEqual(data["currency"], "INR")
        self.assertIn("breakdown", data)
        self.assertTrue(data["total_estimated"] > 0)
        self.assertEqual(data["target_budget"], 5000.0)
        self.assertIn("assumptions", data)

    # --- 2. Test Fixing Errors when a Tool Fails (📘 L2) ---

    def test_tool_error_handling_and_recovery(self):
        """Verify that invalid parameters return structured errors and do not crash (L2)."""
        # Missing required parameter 'destination'
        res = self.tools.execute_tool("search_destination_and_attractions")
        self.assertEqual(res.status, "ERROR")
        self.assertIn("Missing required parameter", res.error)

        # Invalid numeric parameter
        res_budget = self.tools.execute_tool(
            "calculate_budget_breakdown",
            destination="Wayanad",
            duration_days=-1,
            travelers=0
        )
        self.assertEqual(res_budget.status, "ERROR")
        self.assertIn("must be at least 1", res_budget.error)

    # --- 3. Test Pre-Execution Plan Before Acting (📘 L5) ---

    def test_planner_creates_structured_checklist(self):
        """Verify planner creates sequential steps before agent acts (L5)."""
        plan = PlannerEngine.create_trip_planning_plan(
            destination="Wayanad",
            duration_days=2,
            travelers=2,
            budget=5000.0,
            origin="Bangalore"
        )
        self.assertEqual(len(plan.steps), 5)
        self.assertEqual(plan.steps[0].expected_tool, "search_destination_and_attractions")
        self.assertFalse(plan.is_complete())

        # Test state progression
        plan.mark_step_completed(1, "Found attractions")
        self.assertEqual(plan.steps[0].status, StepStatus.COMPLETED)
        self.assertEqual(plan.get_current_step().step_id, 2)

    # --- 4. Test Memory Across Tasks (📘 L4) ---

    def test_memory_persistence_between_tasks(self):
        """Verify user preferences and past trips persist across multiple sessions (L4)."""
        # Task 1: Save preferences for user 'riya'
        prefs = UserPreferences(
            user_id="riya",
            starting_location="Kozhikode",
            default_travelers=3,
            dietary_preferences=["Halal", "Seafood"],
            travel_style="moderate"
        )
        self.memory.save_user_preferences(prefs)

        # Task 2: Create a new agent instance simulating a separate conversation session
        new_memory = TripMemoryStore(storage_path=self.memory_path)
        agent2 = TravelAgentLoop(memory_store=new_memory, logger=self.logger)

        loaded_prefs = new_memory.get_user_preferences("riya")
        self.assertEqual(loaded_prefs.starting_location, "Kozhikode")
        self.assertEqual(loaded_prefs.default_travelers, 3)
        self.assertEqual(loaded_prefs.travel_style, "moderate")

    # --- 5. Test Safety: Step Limit (📘 L7) ---

    def test_safety_step_limit_prevents_runaway(self):
        """Verify hard step ceiling halts execution if exceeded (L7)."""
        # Configure strict limit of 1 step
        strict_safety = SafetyGuardrails(max_steps=1)
        agent = TravelAgentLoop(
            memory_store=self.memory,
            safety_guardrails=strict_safety,
            logger=self.logger
        )

        result = agent.plan_trip("Plan a 2-day trip to Wayanad")
        # Should halt before completing all 4 steps
        self.assertEqual(result["status"], "PARTIAL")

    # --- 6. Test Safety: Asks You First / Human Approval (📘 L7) ---

    def test_safety_human_approval_on_budget_overrun(self):
        """Verify that budget overrun triggers human approval prompt (L7)."""
        approval_requested = []

        def mock_approval_callback(prompt: str) -> bool:
            approval_requested.append(prompt)
            return True  # User approves

        safety = SafetyGuardrails(max_steps=10, approval_callback=mock_approval_callback)
        agent = TravelAgentLoop(
            memory_store=self.memory,
            safety_guardrails=safety,
            logger=self.logger
        )

        # Tiny budget of ₹500 for 2 days 2 people (guaranteed overrun)
        parsed = {
            "destination": "Wayanad",
            "duration_days": 2,
            "travelers": 2,
            "budget": 500.0,
            "origin": "Bangalore"
        }
        result = agent.plan_trip("2-day trip with ₹500 budget", parsed_params=parsed)

        # Verify that approval hook was triggered
        self.assertTrue(len(approval_requested) > 0)
        self.assertIn("Budget Overrun Detected", approval_requested[0])

    # --- 7. Full End-to-End ReAct Loop (📘 L1, L3) & PRD Acceptance Criteria ---

    def test_full_react_loop_wayanad_benchmark(self):
        """
        PRD Section 9 & 16 Acceptance Benchmark:
        'Plan a two-day trip to Wayanad for two people with a total budget of ₹5,000.'
        """
        agent = TravelAgentLoop(
            memory_store=self.memory,
            logger=self.logger
        )

        result = agent.plan_trip(
            user_prompt="Plan a two-day trip to Wayanad for two people with a total budget of ₹5,000 from Bangalore",
            user_id="default_user"
        )

        self.assertEqual(result["status"], "COMPLETED")
        plan: TripPlan = result["trip_plan"]

        # Validate PRD Acceptance Criteria
        self.assertEqual(plan.destination, "Wayanad")
        self.assertEqual(plan.duration_days, 2)
        self.assertEqual(plan.travelers_count, 2)
        self.assertEqual(len(plan.days), 2)

        # Validate realistic day pacing (PRD Section 6.2 & 14)
        for day in plan.days:
            self.assertTrue(len(day.activities) >= 1)
            self.assertTrue(len(day.activities) <= 3)  # Not crowded

        # Validate budget breakdown (PRD Section 6.3)
        self.assertGreater(plan.budget.total_estimated, 0)
        self.assertGreater(plan.budget.accommodation_cost, 0)
        self.assertGreater(plan.budget.food_cost, 0)
        self.assertTrue(len(plan.budget.assumptions) >= 3)

        # Validate Anti-Hallucination & Booking Disclaimer (PRD Section 11 & 16)
        self.assertIn("No bookings are confirmed", plan.booking_disclaimer)
        self.assertIn("estimates", plan.booking_disclaimer.lower())

        # Validate Audit Log exists (📘 L7)
        audit_trail = result["audit_trail"]
        self.assertIn("[THOUGHT]", audit_trail)
        self.assertIn("[ACTION]", audit_trail)
        self.assertIn("[LOOK]", audit_trail)
        self.assertIn("[PLAN]", audit_trail)


if __name__ == "__main__":
    unittest.main()

