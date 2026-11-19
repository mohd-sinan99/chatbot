"""
Interactive Multi-Turn CLI Runner for Smart Travel Planner AI Agent.
Demonstrates:
- Intent Routing & Single-Question Clarification (PRD 7, 8, 11)
- Destination Explorer & Food/Accommodation Finder (PRD 6.1, 6.4, 6.5)
- Delta Itinerary Refinement (PRD 6.8 & Core Use Case 6)
- ReAct Loop: Think -> Act -> Look (📘 L1, L3)
- 4 schema-validated tools with error recovery (📘 L2)
- Persistent Memory across Tasks (📘 L4)
- Pre-Execution Planning (📘 L5)
- Safety: Asks you first, Step limit, Audit log (📘 L7)
"""

import sys
import argparse
from typing import Optional
from agent.memory import TripMemoryStore
from agent.tools import ToolRegistry
from agent.safety import ExecutionLogger
from agent.conversation import ConversationalAgent
from agent.models import TripPlan


def format_trip_display(plan: TripPlan) -> str:
    """Format the finalized trip plan into a clean terminal display."""
    lines = []
    lines.append("=" * 72)
    lines.append(f"  ✈️  TRIP ITINERARY: {plan.destination.upper()} ({plan.duration_days} DAYS, {plan.travelers_count} TRAVELERS)")
    if plan.origin:
        lines.append(f"  📍 Origin: {plan.origin}")
    lines.append("=" * 72)

    # Day-by-Day Schedule
    lines.append("\n📅 DAY-BY-DAY SCHEDULE")
    lines.append("-" * 72)
    for day in plan.days:
        lines.append(f"\n[Day {day.day_number}: {day.theme}]")
        for act in day.activities:
            lines.append(f"  • {act.time_slot}: {act.title}")
            lines.append(f"    - Details: {act.description}")
            lines.append(f"    - Estimated Cost: ₹{act.estimated_cost:,.0f} | Duration: ~{act.duration_hours} hrs")
            if act.opening_hours:
                lines.append(f"    - Hours: {act.opening_hours}")
            if act.source_url:
                lines.append(f"    - Verified Source: {act.source_url}")
            if act.notes:
                lines.append(f"    - Note: {act.notes}")
        if day.transit_notes:
            lines.append(f"  🚗 Transit Note: {day.transit_notes}")

    # Budget Breakdown
    b = plan.budget
    lines.append("\n" + "=" * 72)
    lines.append("💰 ESTIMATED BUDGET BREAKDOWN (PRD Section 6.3)")
    lines.append("-" * 72)
    lines.append(f"  • Accommodation:   ₹{b.accommodation_cost:,.2f}")
    lines.append(f"  • Food & Dining:   ₹{b.food_cost:,.2f}")
    lines.append(f"  • Local Transit:   ₹{b.transport_cost:,.2f}")
    lines.append(f"  • Sightseeing/Fees:₹{b.activities_cost:,.2f}")
    lines.append(f"  • Contingency (8%):₹{b.contingency_cost:,.2f}")
    lines.append("  " + "-" * 36)
    lines.append(f"  TOTAL ESTIMATED:   ₹{b.total_estimated:,.2f} ({b.currency})")
    lines.append(f"  PER PERSON:        ₹{b.per_person_estimated:,.2f}")
    if b.target_budget:
        lines.append(f"  TARGET BUDGET:     ₹{b.target_budget:,.2f}")
        status = "⚠️ OVER BUDGET" if b.is_over_budget else "✅ WITHIN BUDGET"
        lines.append(f"  BUDGET STATUS:     {status}")

    if b.assumptions:
        lines.append("\n  Key Budget Assumptions:")
        for asm in b.assumptions:
            lines.append(f"    - {asm}")

    # Tips & Safety
    lines.append("\n" + "=" * 72)
    lines.append("🛡️  TRAVEL TIPS & SAFETY ADVISORIES")
    lines.append("-" * 72)
    lines.append("  Packing & Advice:")
    for tip in plan.travel_tips:
        lines.append(f"    - {tip}")
    lines.append("  Local Rules & Safety:")
    for safe in plan.safety_advisories:
        lines.append(f"    - {safe}")

    # Anti-Hallucination Disclaimer (PRD Requirement)
    lines.append("\n" + "=" * 72)
    lines.append("⚠️  IMPORTANT NOTICE & DISCLAIMER (PRD Section 11 & 16)")
    lines.append("-" * 72)
    lines.append(f"  {plan.booking_disclaimer}")
    lines.append("=" * 72 + "\n")

    return "\n".join(lines)


def run_agent_cli(demo_mode: bool = False, query: Optional[str] = None):
    print("=" * 72)
    print("  🌍 SMART TRAVEL PLANNER AI AGENT")
    print("  Core Agent Architecture: L1-L8 | PRD Functional Requirements 6.1 - 6.8")
    print("=" * 72)

    memory = TripMemoryStore()
    user_id = "default_user"
    prefs = memory.get_user_preferences(user_id)

    print(f"\n[📘 L4: Memory Loaded] User: {user_id}")
    print(f"  • Home Location: {prefs.starting_location}")
    print(f"  • Travel Style:  {prefs.travel_style}")
    print(f"  • Past Visits:   {', '.join(prefs.past_destinations) if prefs.past_destinations else 'None'}")

    logger = ExecutionLogger(verbose=True)
    conv_agent = ConversationalAgent(memory_store=memory, logger=logger)

    # Demo or single query mode
    if demo_mode or query:
        prompt = query or "Plan a two-day trip to Wayanad for two people with a total budget of ₹5,000 from Bangalore"
        print(f"\n[User Query]: {prompt}\n")
        response = conv_agent.process_message(prompt, user_id=user_id)

        if response["type"] == "TRIP_GENERATED":
            print("\n" + format_trip_display(response["trip_plan"]))
        elif response["type"] == "DESTINATION_RECOMMENDATIONS":
            print(f"\n{response['content']}\n")
        elif response["type"] == "CLARIFICATION_REQUIRED":
            print(f"\n🤖 Clarification: {response['question']}\n")
        elif response["type"] == "PLAN_UPDATED":
            print(f"\n[Update Summary]:\n{response['summary']}\n")
            print(format_trip_display(response["trip_plan"]))
        return

    # Interactive multi-turn conversational loop
    print("\nAsk anything or plan a trip! (Type 'exit' to quit)")
    print("Try: 'Plan a 2-day trip to Wayanad', 'Suggest destinations', 'Make Day 1 more relaxing'\n")

    while True:
        try:
            user_msg = input("\nYou: ").strip()
            if not user_msg:
                continue
            if user_msg.lower() in ("exit", "quit", "q"):
                print("Happy travels! Goodbye! 👋")
                break

            response = conv_agent.process_message(user_msg, user_id=user_id)
            resp_type = response.get("type")

            if resp_type == "CLARIFICATION_REQUIRED":
                print(f"\n🤖 Agent: {response['question']}")

            elif resp_type == "TRIP_GENERATED":
                print("\n" + format_trip_display(response["trip_plan"]))

            elif resp_type == "PLAN_UPDATED":
                print(f"\n✅ Itinerary Updated:\n{response['summary']}")
                print("\n" + format_trip_display(response["trip_plan"]))

            elif resp_type == "DESTINATION_RECOMMENDATIONS":
                print(f"\n{response['content']}")

            elif resp_type == "TRIP_EXPORTED":
                print(f"\n📁 {response['content']}")

            elif resp_type == "BUDGET_COMPARISON":
                print(f"\n{response['content']}")

            else:
                print(f"\n🤖 Agent: {response.get('content', 'How can I help you plan your trip?')}")

        except (KeyboardInterrupt, EOFError):
            print("\nExiting. Safe travels!")
            break


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smart Travel Planner AI Agent CLI & Web Dashboard")
    parser.add_argument("--demo", action="store_true", help="Run benchmark demo mode")
    parser.add_argument("--query", type=str, default=None, help="Custom travel query")
    parser.add_argument("--web", action="store_true", help="Launch interactive dual-pane Web UI")
    parser.add_argument("--port", type=int, default=8000, help="Web server port (default 8000)")
    args = parser.parse_args()

    if args.web:
        from web_server import start_server
        start_server(port=args.port)
    else:
        run_agent_cli(demo_mode=args.demo, query=args.query)
