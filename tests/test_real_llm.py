"""
Live Integration Tests with Real LLM (📘 L8: Real LLM Second)
Connects to Google Gemini API when GEMINI_API_KEY is configured in the environment.
Gracefully skips if the API key is not present.
"""

import os
import unittest
from agent.memory import TripMemoryStore
from agent.tools import ToolRegistry
from agent.safety import SafetyGuardrails, ExecutionLogger
from agent.core_loop import TravelAgentLoop


class TestRealLLMIntegration(unittest.TestCase):
    """Tier 2: Real LLM integration test suite (📘 L8)."""

    def setUp(self):
        self.api_key = os.getenv("GEMINI_API_KEY")

    def test_live_llm_end_to_end(self):
        """End-to-end integration test with live LLM (skipped if no API key)."""
        if not self.api_key:
            self.skipTest("GEMINI_API_KEY environment variable not set. Skipping live LLM test.")

        # Test live connection
        memory = TripMemoryStore()
        logger = ExecutionLogger(verbose=True)
        safety = SafetyGuardrails(max_steps=10)

        agent = TravelAgentLoop(
            memory_store=memory,
            safety_guardrails=safety,
            logger=logger
        )

        result = agent.plan_trip(
            user_prompt="Plan a 2-day trip to Wayanad with a budget of ₹5,000 for 2 people"
        )

        self.assertEqual(result["status"], "COMPLETED")
        self.assertIsNotNone(result["trip_plan"])
        self.assertEqual(result["trip_plan"].destination, "Wayanad")


if __name__ == "__main__":
    unittest.main()

