"""
Multi-Turn Conversational Session Manager (PRD Section 7, 8, 11)
Coordinates intent classification, clarification flow, plan generation, and delta refinements.
"""

from typing import Dict, Any, Optional, Tuple, List
from agent.models import TripPlan, UserPreferences
from agent.memory import TripMemoryStore
from agent.router import IntentRouter, UserIntent
from agent.refiner import DeltaPlanRefiner
from agent.core_loop import TravelAgentLoop
from agent.tools import ToolRegistry
from agent.tools.destination_tool import DestinationSearchTool
from agent.safety import ExecutionLogger, SafetyGuardrails
from agent.exporter import ItineraryExporter
from agent.budget_optimizer import BudgetOptimizer


class ConversationalAgent:
    """
    Stateful multi-turn conversational agent for travel planning.
    Handles clarifications, exploratory recommendations, new itineraries, and delta updates.
    """

    def __init__(
        self,
        memory_store: Optional[TripMemoryStore] = None,
        tool_registry: Optional[ToolRegistry] = None,
        logger: Optional[ExecutionLogger] = None
    ):
        self.memory = memory_store or TripMemoryStore()
        self.tools = tool_registry or ToolRegistry()
        self.logger = logger or ExecutionLogger(verbose=True)
        self.refiner = DeltaPlanRefiner(tool_registry=self.tools)
        self.agent_loop = TravelAgentLoop(
            memory_store=self.memory,
            tool_registry=self.tools,
            logger=self.logger
        )

        # Working session state
        self.pending_params: Dict[str, Any] = {}
        self.awaiting_clarification_field: Optional[str] = None

    def process_message(
        self,
        user_message: str,
        user_id: str = "default_user"
    ) -> Dict[str, Any]:
        """
        Process incoming user message through intent classification, clarification, or planning.
        """
        user_prefs = self.memory.get_user_preferences(user_id)
        active_trip = self.memory.get_active_trip()

        # Step 1: Intent Classification (PRD Section 8)
        intent = IntentRouter.classify_intent(
            user_message=user_message,
            has_active_trip=(active_trip is not None),
            awaiting_clarification=(self.awaiting_clarification_field is not None)
        )

        # Step 2: Check for Export command (PRD Section 12)
        lower_msg = user_message.lower().strip()
        if ("export" in lower_msg or "download" in lower_msg) and active_trip:
            export_files = ItineraryExporter.export_all(active_trip)
            return {
                "type": "TRIP_EXPORTED",
                "files": export_files,
                "content": (
                    f"Trip itinerary for {active_trip.destination} exported successfully!\n"
                    f"• 📄 Markdown: {export_files['markdown']}\n"
                    f"• 🌐 Print-Ready HTML: {export_files['html']}\n"
                    f"• 💾 JSON: {export_files['json']}"
                )
            }

        # Step 3: Check for Budget Comparison command (PRD Section 6.3)
        if ("compare budget" in lower_msg or "budget tiers" in lower_msg or "budget packages" in lower_msg) and active_trip:
            analysis = BudgetOptimizer.generate_alternative_packages(
                duration_days=active_trip.duration_days,
                travelers=active_trip.travelers_count,
                target_budget=active_trip.budget.target_budget
            )
            return {
                "type": "BUDGET_COMPARISON",
                "content": BudgetOptimizer.format_comparison_table(analysis),
                "analysis": analysis
            }

        # Step 4: Route by intent

        # Route A: Clarification Answer (answering a previously asked question)
        if intent == UserIntent.CLARIFY_INFO and self.awaiting_clarification_field:
            return self._handle_clarification_answer(user_message, user_prefs, user_id)

        # Route B: Destination Exploration (PRD Section 6.1)
        elif intent == UserIntent.EXPLORE_DESTINATIONS:
            return self._handle_destination_exploration(user_message, user_prefs)

        # Route C: Plan Refinement / Delta Modification (PRD Section 6.8)
        elif intent == UserIntent.REFINE_PLAN and active_trip:
            return self._handle_plan_refinement(user_message, active_trip)

        # Route D: New Trip Planning
        elif intent == UserIntent.NEW_TRIP:
            return self._handle_new_trip(user_message, user_prefs, user_id)

        # Route E: General Query / Fallback
        else:
            return {
                "type": "MESSAGE",
                "content": (
                    "I am your Smart Travel Planner AI Agent! ✈️\n\n"
                    "You can tell me:\n"
                    "• 'Plan a two-day trip to Wayanad for 2 people with a ₹5,000 budget'\n"
                    "• 'Suggest weekend destinations from Bangalore'\n"
                    "• 'Modify Day 2 to be more relaxing' (if you have an active itinerary)"
                )
            }

    # --- Internal Handlers ---

    def _handle_new_trip(
        self,
        user_message: str,
        user_prefs: UserPreferences,
        user_id: str
    ) -> Dict[str, Any]:
        """Evaluate missing info and start planning or ask clarification (PRD Section 7, 11)."""
        extracted, question = IntentRouter.evaluate_missing_information(user_message, user_prefs)
        self.pending_params = extracted

        # Enforce 'one clear question at a time' rule (PRD Section 11)
        if question:
            # Record which field we are waiting for
            if "destination" not in extracted:
                self.awaiting_clarification_field = "destination"
            elif "duration_days" not in extracted:
                self.awaiting_clarification_field = "duration_days"

            return {
                "type": "CLARIFICATION_REQUIRED",
                "question": question,
                "partial_params": self.pending_params
            }

        # All essential inputs present -> Proceed with ReAct Loop
        self.awaiting_clarification_field = None
        result = self.agent_loop.plan_trip(
            user_prompt=user_message,
            user_id=user_id,
            parsed_params=self.pending_params
        )
        return {
            "type": "TRIP_GENERATED",
            "result": result,
            "trip_plan": result["trip_plan"]
        }

    def _handle_clarification_answer(
        self,
        user_message: str,
        user_prefs: UserPreferences,
        user_id: str
    ) -> Dict[str, Any]:
        """Incorporate the user's answer into pending parameters."""
        field = self.awaiting_clarification_field
        ans = user_message.strip()

        if field == "destination":
            self.pending_params["destination"] = ans.title()
        elif field == "duration_days":
            # Extract number
            import re
            m = re.search(r'\d+', ans)
            self.pending_params["duration_days"] = int(m.group(0)) if m else 2

        self.awaiting_clarification_field = None

        # Re-check if any other essential info is missing
        dummy_prompt = f"Trip to {self.pending_params.get('destination', '')} for {self.pending_params.get('duration_days', '')} days"
        _, question = IntentRouter.evaluate_missing_information(dummy_prompt, user_prefs)

        if question:
            if "duration_days" not in self.pending_params:
                self.awaiting_clarification_field = "duration_days"
            return {
                "type": "CLARIFICATION_REQUIRED",
                "question": question,
                "partial_params": self.pending_params
            }

        # Ready to generate trip plan
        result = self.agent_loop.plan_trip(
            user_prompt=f"Trip to {self.pending_params['destination']} for {self.pending_params['duration_days']} days",
            user_id=user_id,
            parsed_params=self.pending_params
        )
        return {
            "type": "TRIP_GENERATED",
            "result": result,
            "trip_plan": result["trip_plan"]
        }

    def _handle_destination_exploration(
        self,
        user_message: str,
        user_prefs: UserPreferences
    ) -> Dict[str, Any]:
        """Suggest destinations based on budget and starting point (PRD Section 6.1)."""
        origin = user_prefs.starting_location or "Bangalore"
        ideas = DestinationSearchTool.recommend_destinations(origin=origin)

        lines = [
            f"Here are top destination recommendations starting from {origin}:\n"
        ]
        for idx, idea in enumerate(ideas, 1):
            lines.append(f"**{idx}. {idea['destination']}** ({idea['ideal_duration']})")
            lines.append(f"• Why Visit: {idea['why_visit']}")
            lines.append(f"• Approx Cost for 2: ₹{idea['approx_budget_for_two']:,.0f}")
            lines.append(f"• Highlights: {', '.join(idea['highlights'])}")
            lines.append(f"• Distance: {idea['distance_from_bangalore']}\n")

        lines.append("Which of these destinations would you like to explore or plan an itinerary for?")
        return {
            "type": "DESTINATION_RECOMMENDATIONS",
            "content": "\n".join(lines),
            "destinations": ideas
        }

    def _handle_plan_refinement(
        self,
        user_message: str,
        active_trip: TripPlan
    ) -> Dict[str, Any]:
        """Apply targeted modifications to active trip plan (PRD Section 6.8)."""
        updated_plan, change_summary = self.refiner.refine_plan(active_trip, user_message)
        # Save back to persistent memory
        self.memory.save_trip_plan(updated_plan)

        return {
            "type": "PLAN_UPDATED",
            "summary": change_summary,
            "trip_plan": updated_plan
        }

