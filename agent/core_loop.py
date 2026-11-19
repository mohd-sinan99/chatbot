"""
Core ReAct Agent Loop (📘 L1, L3: Think → Act → Look)
Coordinates planning (L5), memory (L4), tool dispatching & error recovery (L2),
and safety guardrails with human approval and step limits (L7).
"""

import json
from typing import Dict, Any, Optional, List, Tuple
from agent.models import (
    TripPlan,
    ItineraryDay,
    Activity,
    BudgetBreakdown,
    UserPreferences,
)
from agent.memory import TripMemoryStore
from agent.planner import PlannerEngine, ExecutionPlan, StepStatus
from agent.tools import ToolRegistry, ToolResult
from agent.safety import SafetyGuardrails, ExecutionLogger
from agent.constraints import ConstraintEngine
from agent.react_parser import ReActParser, ReActStep
from agent.pacing import PacingEngine
from agent.budget_optimizer import BudgetOptimizer
from config import DEFAULT_MAX_STEPS


class TravelAgentLoop:
    """
    Main ReAct Agent for Smart Travel Planning.
    Executes the classic loop: Think -> Act -> Look, guided by a pre-computed plan.
    """

    def __init__(
        self,
        memory_store: Optional[TripMemoryStore] = None,
        tool_registry: Optional[ToolRegistry] = None,
        safety_guardrails: Optional[SafetyGuardrails] = None,
        logger: Optional[ExecutionLogger] = None,
        llm_backend: Optional[Any] = None,  # Supports FakeLLM or Real LLM (L8)
    ):
        self.memory = memory_store or TripMemoryStore()
        self.tools = tool_registry or ToolRegistry()
        self.safety = safety_guardrails or SafetyGuardrails(max_steps=DEFAULT_MAX_STEPS)
        self.logger = logger or ExecutionLogger(verbose=True)
        self.llm = llm_backend

    def plan_trip(
        self,
        user_prompt: str,
        user_id: str = "default_user",
        parsed_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes the full planning workflow for a user request:
        1. Memory retrieval (L4)
        2. Plan formulation (L5)
        3. ReAct loop: Think -> Act -> Look (L1, L3, L2)
        4. Safety checks & approvals (L7)
        5. Final synthesis & persistent memory update (L4)
        """
        self.logger.log_thought(0, f"Received trip request: '{user_prompt}' for user '{user_id}'")

        # Step 1: Load Memory & Profile (📘 L4)
        user_prefs = self.memory.get_user_preferences(user_id)
        self.logger.log_thought(
            0,
            f"Loaded user preferences: Starting location='{user_prefs.starting_location}', "
            f"Default travelers={user_prefs.default_travelers}, Style='{user_prefs.travel_style}', "
            f"Past visits={user_prefs.past_destinations}"
        )

        # Extract trip parameters (either from parsed_params, LLM, or fallback heuristic)
        trip_params = self._extract_parameters(user_prompt, user_prefs, parsed_params)
        destination = trip_params["destination"]
        duration_days = trip_params["duration_days"]
        travelers = trip_params["travelers"]
        budget = trip_params.get("budget")
        origin = trip_params.get("origin") or user_prefs.starting_location

        # Step 2: Formulate Plan Before Acting (📘 L5)
        plan: ExecutionPlan = PlannerEngine.create_trip_planning_plan(
            destination=destination,
            duration_days=duration_days,
            travelers=travelers,
            budget=budget,
            origin=origin
        )
        self.logger.log_plan(0, plan.to_markdown())

        # Execution scratchpad for the ReAct loop
        observations: Dict[str, Any] = {}
        current_step_num = 1
        agent_terminated = False
        final_itinerary: Optional[TripPlan] = None

        # Step 3: Core ReAct Loop: Think -> Act -> Look (📘 L1, L3)
        while not plan.is_complete() and not agent_terminated:
            # 3.1 Safety Check: Enforce Step Limit (📘 L7)
            if not self.safety.check_step_limit(current_step_num):
                self.logger.log_safety(
                    current_step_num,
                    f"Safety step limit reached ({self.safety.max_steps} steps). Halting loop to prevent runaway cycles."
                )
                break

            current_plan_step = plan.get_current_step()
            if not current_plan_step:
                break

            plan.mark_step_in_progress(current_plan_step.step_id)

            # 3.2 THINK (📘 L1, L3)
            # Decide action based on current plan step and prior observations
            thought_text, action_tool, action_args = self._think_and_decide_action(
                current_plan_step=current_plan_step,
                trip_params=trip_params,
                observations=observations,
                step_num=current_step_num
            )
            self.logger.log_thought(current_step_num, thought_text)

            # Check if this step is pure synthesis (no tool needed)
            if not action_tool:
                plan.mark_step_completed(current_plan_step.step_id, "Completed synthesis.")
                current_step_num += 1
                continue

            # 3.3 ACT (📘 L1, L3, L2)
            self.logger.log_action(current_step_num, action_tool, action_args)
            tool_result: ToolResult = self.tools.execute_tool(action_tool, **action_args)

            # 3.4 FIXING ERRORS (📘 L2: Error recovery)
            if tool_result.status == "ERROR":
                self.logger.log_look(current_step_num, tool_result.to_observation_string())
                # Self-correction attempt: adjust arguments and retry once
                corrected_args = self._handle_tool_error(action_tool, action_args, tool_result.error or "")
                self.logger.log_thought(
                    current_step_num,
                    f"Tool error detected: {tool_result.error}. Attempting self-correction with revised args: {corrected_args}"
                )
                tool_result = self.tools.execute_tool(action_tool, **corrected_args)

            # 3.5 LOOK (📘 L1, L3)
            observation_str = tool_result.to_observation_string()
            self.logger.log_look(current_step_num, observation_str)
            observations[action_tool] = tool_result.data

            # 3.6 SAFETY: ASKS YOU FIRST (📘 L7)
            # If budget calculation reveals an overrun, trigger human approval
            if action_tool == "calculate_budget_breakdown" and tool_result.status == "SUCCESS":
                budget_data = tool_result.data
                if budget_data.get("is_over_budget"):
                    self.logger.log_safety(
                        current_step_num,
                        f"Overrun alert: Estimated total ₹{budget_data['total_estimated']} exceeds user budget ₹{budget_data['target_budget']}"
                    )
                    approved = self.safety.request_human_approval(
                        reason="Budget Overrun Detected",
                        details=(
                            f"Estimated trip expenses (₹{budget_data['total_estimated']:,.0f}) exceed your target budget "
                            f"(₹{budget_data['target_budget']:,.0f}) by ₹{budget_data['overrun_amount']:,.0f}.\n"
                            f"Suggestions:\n" + "\n".join(f"- {s}" for s in budget_data.get("cost_saving_suggestions", []))
                        )
                    )
                    if not approved:
                        self.logger.log_safety(
                            current_step_num,
                            "User chose not to proceed with over-budget plan. Applying budget-saving tier."
                        )
                        # Switch to extreme budget tier
                        trip_params["tier"] = "budget"

            # Update plan progress (📘 L5)
            plan.mark_step_completed(
                current_plan_step.step_id,
                f"Obtained verified data for {action_tool}"
            )
            current_step_num += 1

        # Step 4: Synthesize Final Plan & Itinerary
        final_itinerary = self._synthesize_final_plan(trip_params, observations)

        # Step 5: Save to Persistent Memory (📘 L4)
        self.memory.save_trip_plan(final_itinerary)
        self.memory.record_destination_visit(user_id, destination)
        self.logger.log_final(
            current_step_num,
            f"Successfully finalized and persisted trip '{final_itinerary.trip_id}' to memory store."
        )

        return {
            "plan_goal": plan.goal,
            "status": "COMPLETED" if plan.is_complete() else "PARTIAL",
            "trip_plan": final_itinerary,
            "execution_plan_markdown": plan.to_markdown(),
            "audit_trail": self.logger.get_full_trace(),
        }

    # --- Reasoning & Decision Helpers ---

    def _think_and_decide_action(
        self,
        current_plan_step: Any,
        trip_params: Dict[str, Any],
        observations: Dict[str, Any],
        step_num: int
    ) -> Tuple[str, Optional[str], Dict[str, Any]]:
        """
        Think step of the loop (📘 L1, L3).
        Determines the thought statement, tool to call, and arguments.
        """
        expected_tool = current_plan_step.expected_tool

        if expected_tool == "search_destination_and_attractions":
            thought = (
                f"Step requires discovering verified attractions in {trip_params['destination']}. "
                f"I will call search_destination_and_attractions."
            )
            args = {
                "destination": trip_params["destination"],
                "interests": trip_params.get("interests", []),
                "max_results": max(4, trip_params["duration_days"] * 2)
            }
            return thought, expected_tool, args

        elif expected_tool == "calculate_budget_breakdown":
            thought = (
                f"Step requires calculating categorized expenses for {trip_params['duration_days']} days "
                f"and {trip_params['travelers']} travelers under budget {trip_params.get('budget')}."
            )
            args = {
                "destination": trip_params["destination"],
                "duration_days": trip_params["duration_days"],
                "travelers": trip_params["travelers"],
                "tier": trip_params.get("tier", "budget"),
                "target_budget": trip_params.get("budget"),
                "include_intercity_travel": trip_params.get("include_intercity", False)
            }
            return thought, expected_tool, args

        elif expected_tool == "find_transport_options":
            thought = (
                f"User requested origin '{trip_params.get('origin')}'. "
                f"Calling find_transport_options to compare transit routes to {trip_params['destination']}."
            )
            args = {
                "origin": trip_params.get("origin", "Bangalore"),
                "destination": trip_params["destination"],
                "preferred_mode": "all"
            }
            return thought, expected_tool, args

        elif expected_tool == "get_travel_advisory_and_weather":
            thought = (
                f"Checking safety advisories, weather, and packing lists for {trip_params['destination']}."
            )
            args = {
                "destination": trip_params["destination"],
                "season_or_month": trip_params.get("travel_date")
            }
            return thought, expected_tool, args

        else:
            thought = f"Synthesizing gathered data for step: {current_plan_step.title}."
            return thought, None, {}

    def _handle_tool_error(self, tool_name: str, args: Dict[str, Any], error: str) -> Dict[str, Any]:
        """
        Self-correction logic when a tool fails (📘 L2).
        Inspects error message and returns fixed arguments.
        """
        corrected = dict(args)
        if "Missing required parameter" in error:
            # Provide sensible fallback defaults for missing parameters
            if "destination" in error:
                corrected["destination"] = "Wayanad"
            if "duration_days" in error:
                corrected["duration_days"] = 2
            if "travelers" in error:
                corrected["travelers"] = 2
        if "must be at least 1" in error:
            if corrected.get("duration_days", 0) < 1:
                corrected["duration_days"] = 1
            if corrected.get("travelers", 0) < 1:
                corrected["travelers"] = 1
        return corrected

    def _extract_parameters(
        self,
        user_prompt: str,
        user_prefs: UserPreferences,
        parsed_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extract or infer trip parameters from prompt and user memory."""
        if parsed_params:
            params = dict(parsed_params)
        else:
            params = {}

        # Heuristic extraction for MVP testing
        text = user_prompt.lower()

        # Destination
        if "destination" not in params:
            if "wayanad" in text:
                params["destination"] = "Wayanad"
            elif "coorg" in text:
                params["destination"] = "Coorg"
            elif "munnar" in text:
                params["destination"] = "Munnar"
            else:
                params["destination"] = "Wayanad"  # Default test destination

        # Duration
        if "duration_days" not in params:
            if "two-day" in text or "2-day" in text or "2 day" in text or "two day" in text:
                params["duration_days"] = 2
            elif "three-day" in text or "3-day" in text or "3 day" in text or "three day" in text:
                params["duration_days"] = 3
            elif "weekend" in text:
                params["duration_days"] = 2
            else:
                params["duration_days"] = 2

        # Travelers
        if "travelers" not in params:
            if "two people" in text or "2 people" in text or "couple" in text:
                params["travelers"] = 2
            elif "solo" in text or "1 person" in text:
                params["travelers"] = 1
            elif "family" in text or "4 people" in text:
                params["travelers"] = 4
            else:
                params["travelers"] = user_prefs.default_travelers

        # Budget
        if "budget" not in params:
            # Look for ₹ or digits
            import re
            budget_match = re.search(r'(?:₹|rs\.?|inr)\s?([0-9,]+)', text)
            if budget_match:
                clean_num = budget_match.group(1).replace(",", "")
                params["budget"] = float(clean_num)
            elif "5000" in text or "5,000" in text:
                params["budget"] = 5000.0

        # Origin
        if "origin" not in params:
            if "from bangalore" in text or "bangalore" in text:
                params["origin"] = "Bangalore"
            else:
                params["origin"] = user_prefs.starting_location or "Bangalore"

        # Tier & Interests
        if "tier" not in params:
            params["tier"] = user_prefs.travel_style or "budget"
        if "interests" not in params:
            params["interests"] = user_prefs.interests

        # Day of week (for operational closure checks)
        if "start_day" not in params:
            for dow in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
                if dow in text:
                    params["start_day"] = dow
                    break

        return params

    def _synthesize_final_plan(
        self,
        params: Dict[str, Any],
        observations: Dict[str, Any]
    ) -> TripPlan:
        """
        Combines observations into a structured, realistic, day-by-day TripPlan.
        Enforces realistic pacing (morning/afternoon/evening) and PRD disclaimers.
        """
        destination = params["destination"]
        duration = params["duration_days"]
        travelers = params["travelers"]
        trip_id = f"trip_{destination.lower()}_{duration}d"

        # Attractions
        dest_data = observations.get("search_destination_and_attractions", {})
        attractions_list = dest_data.get("attractions", [])

        # Budget
        budget_data = observations.get("calculate_budget_breakdown", {})
        bd = budget_data.get("breakdown", {})
        assumptions_list = list(budget_data.get("assumptions", []))

        # Check alternative tier packages if target budget is defined (PRD Section 6.3)
        target_b = params.get("budget")
        if target_b and target_b > 0:
            analysis = BudgetOptimizer.generate_alternative_packages(
                duration_days=duration,
                travelers=travelers,
                target_budget=target_b
            )
            eco_pkg = analysis["packages"][0]
            if budget_data.get("is_over_budget", False):
                assumptions_list.append(
                    f"Cost-Saving Alternative: Eco-Saver package (Homestay + KSRTC) fits at ₹{eco_pkg.total_cost:,.0f}."
                )

        budget = BudgetBreakdown(
            currency="INR",
            transport_cost=bd.get("local_commute", 0.0) + bd.get("intercity_travel", 0.0),
            accommodation_cost=bd.get("accommodation", 0.0),
            food_cost=bd.get("food", 0.0),
            activities_cost=bd.get("activities_entry_fees", 0.0),
            contingency_cost=bd.get("contingency_buffer", 0.0),
            total_estimated=budget_data.get("total_estimated", 0.0),
            per_person_estimated=budget_data.get("per_person_estimated", 0.0),
            target_budget=params.get("budget"),
            is_over_budget=budget_data.get("is_over_budget", False),
            assumptions=assumptions_list,
            disclaimers=[
                "All price figures are estimates. Confirm live rates with hotels, cab operators, and ticket counters.",
                "No bookings are confirmed until paid directly to official providers."
            ]
        )

        # Distribute attractions across days with geographic clustering & dining buffers (PRD 6.2, 6.5)
        eateries_list = dest_data.get("recommended_eateries", [])
        dietary_pref = params.get("dietary_preference")
        days = PacingEngine.schedule_paced_days(
            destination=destination,
            attractions=attractions_list,
            duration_days=duration,
            eateries=eateries_list,
            dietary_preference=dietary_pref
        )

        # Apply constraint engine checks (PRD Section 6.2: Opening hours & closures)
        start_dow = params.get("start_day")
        adjusted_days, constraint_warnings = ConstraintEngine.validate_and_adjust_itinerary(
            days, start_day_of_week=start_dow
        )
        days = adjusted_days

        # Advisory & Safety
        advisory_data = observations.get("get_travel_advisory_and_weather", {})
        tips = list(advisory_data.get("packing_essentials", [
            "Comfortable footwear", "Camera", "Identification proof", "Power bank"
        ]))

        # Include live weather forecast if available (PRD Section 6.7)
        live_weather = advisory_data.get("live_weather")
        if live_weather:
            temp = live_weather.get("temperature_celsius")
            cond = live_weather.get("condition")
            dyn_adv = live_weather.get("dynamic_advisory")
            tips.insert(0, f"Live Weather Forecast: {temp}°C, {cond}. {dyn_adv}")

        safety = list(advisory_data.get("safety_and_rules", [
            "Verify attraction opening times locally.",
            "Avoid night travel through forest reserves."
        ]))

        # Append constraint notices if any
        for warn in constraint_warnings:
            safety.append(f"Operating Hours Alert: {warn}")

        return TripPlan(
            trip_id=trip_id,
            destination=destination,
            origin=params.get("origin"),
            duration_days=duration,
            travelers_count=travelers,
            days=days,
            budget=budget,
            travel_tips=tips,
            safety_advisories=safety,
            status="FINALIZED"
        )

