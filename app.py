"""
Streamlit Web Application for Smart Travel Planner AI Agent
Provides an interactive, modern user interface for trip planning, destination comparison,
live budget breakdown, weather advisories, and multi-format itinerary exports.
"""

import os
import sys
from datetime import date
import streamlit as st

# Ensure project root is on path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from agent.conversation import ConversationalAgent
from agent.safety import ExecutionLogger
from agent.exporter import ItineraryExporter
from agent.calendar_export import CalendarExporter
from agent.comparator import DestinationComparator
from agent.budget_optimizer import BudgetOptimizer

# Page Configuration
st.set_page_config(
    page_title="Smart Travel Planner AI",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .badge-card {
        background: #F3F4F6;
        border-radius: 8px;
        padding: 10px 14px;
        margin-bottom: 10px;
        border-left: 4px solid #3B82F6;
    }
    .metric-box {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 12px;
        text-align: center;
    }
    .disclaimer-banner {
        background-color: #FEF3C7;
        border-left: 4px solid #F59E0B;
        color: #92400E;
        padding: 12px;
        border-radius: 6px;
        font-size: 0.88rem;
        margin-top: 15px;
    }
</style>
""", unsafe_allow_html=True)


# Initialize Session State
if "agent" not in st.session_state:
    st.session_state.agent = ConversationalAgent(logger=ExecutionLogger(verbose=False))
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "👋 **Hello! I am your Smart Travel Planner AI Agent.**\n\n"
                "Tell me where you want to go or try one of the quick prompts below:\n"
                "• *'Plan a 2-day trip to Wayanad for 2 people with ₹5,000 budget, vegetarian food'*\n"
                "• *'Suggest weekend destinations from Bangalore'*\n"
                "• *'Compare Wayanad and Coorg'*"
            )
        }
    ]
if "active_trip" not in st.session_state:
    st.session_state.active_trip = None


# Sidebar
with st.sidebar:
    st.image("https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=500&auto=format&fit=crop&q=60", use_container_width=True)
    st.title("✈️ Travel Assistant")
    st.caption("AI-Powered Itineraries • Real-Time Weather • Zero Cost Bias")

    st.markdown("---")
    st.subheader("💡 Quick Prompts")

    if st.button("🌲 Wayanad 2-Day (₹5,000)", use_container_width=True):
        st.session_state.pending_input = "Plan a 2-day trip to Wayanad for 2 people with ₹5000 budget, vegetarian food"

    if st.button("☕ Coorg 3-Day Explorer", use_container_width=True):
        st.session_state.pending_input = "Plan a 3-day trip to Coorg for 2 people with ₹6000 budget"

    if st.button("🔍 Explore Kerala & Karnataka", use_container_width=True):
        st.session_state.pending_input = "Show me popular destinations starting from Bangalore"

    if st.button("⚖️ Compare Wayanad vs Coorg", use_container_width=True):
        st.session_state.pending_input = "compare wayanad and coorg"

    st.markdown("---")
    st.subheader("⚙️ Session Controls")
    if st.button("🔄 Reset Conversation", use_container_width=True):
        st.session_state.agent.memory.set_active_trip_id(None)
        st.session_state.agent.pending_params = {}
        st.session_state.agent.awaiting_clarification_field = None
        st.session_state.messages = [
            {"role": "assistant", "content": "✨ Session reset. Where would you like to travel next?"}
        ]
        st.session_state.active_trip = None
        st.rerun()

    st.markdown("---")
    st.caption("Built with Google Antigravity L1–L8 Standards • Streamlit UI")


# Header
st.markdown('<div class="main-header">Smart Travel Planner AI Agent</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Personalized itineraries with budget estimation, regional pacing, live weather advisories, and instant exports.</div>', unsafe_allow_html=True)


# Main Layout (Dual-Column: Chat Left (5), Dashboard Right (7))
col_chat, col_dash = st.columns([5, 7], gap="large")

# -------------------------------------------------------------
# LEFT COLUMN: Conversational Agent Interface
# -------------------------------------------------------------
with col_chat:
    st.subheader("💬 Chat with Agent")

    # Render Chat History
    chat_container = st.container(height=520)
    with chat_container:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # Chat Input
    user_prompt = st.chat_input("Type your travel requirements...")

    # Check if a quick button was pressed
    if "pending_input" in st.session_state and st.session_state.pending_input:
        user_prompt = st.session_state.pending_input
        del st.session_state.pending_input

    if user_prompt:
        # Display user message
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(user_prompt)

        # Process through Agent
        with chat_container:
            with st.chat_message("assistant"):
                with st.spinner("Agent thinking, checking tools & planning..."):
                    # Check if comparator intent directly
                    lower_p = user_prompt.lower()
                    if "compare" in lower_p and ("and" in lower_p or "vs" in lower_p):
                        words = lower_p.replace("compare", "").replace("vs", "and").split("and")
                        dest_a = words[0].strip().title() if len(words) > 0 else "Wayanad"
                        dest_b = words[1].strip().title() if len(words) > 1 else "Coorg"
                        comp_res = DestinationComparator.compare(dest_a, dest_b, target_budget=5000.0)
                        reply = DestinationComparator.format_report(comp_res)
                        st.markdown(reply)
                        st.session_state.messages.append({"role": "assistant", "content": reply})
                    else:
                        resp = st.session_state.agent.process_message(user_prompt)

                        if resp.get("type") == "TRIP_GENERATED":
                            plan = resp.get("trip_plan")
                            st.session_state.active_trip = plan
                            target_budget_str = f"₹{plan.budget.target_budget:,.0f}" if getattr(plan.budget, "target_budget", None) is not None else "Not specified"
                            reply = (
                                f"✨ **Itinerary generated for {plan.destination}!**\n\n"
                                f"• **Duration:** {plan.duration_days} Days ({plan.travelers_count} Travelers)\n"
                                f"• **Estimated Cost:** ₹{plan.budget.total_estimated:,.0f} (Target: {target_budget_str})\n\n"
                                "👉 *Review the full day-by-day plan, budget breakdown, and export options on the right.*"
                            )
                            st.markdown(reply)
                            st.session_state.messages.append({"role": "assistant", "content": reply})
                            st.rerun()

                        elif resp.get("type") == "CLARIFICATION_REQUIRED":
                            reply = f"❓ **Clarification Needed:**\n\n{resp.get('question')}"
                            st.markdown(reply)
                            st.session_state.messages.append({"role": "assistant", "content": reply})

                        elif resp.get("type") == "PLAN_UPDATED":
                            st.session_state.active_trip = resp.get("trip_plan")
                            reply = f"✏️ **Itinerary Updated:**\n\n{resp.get('summary')}"
                            st.markdown(reply)
                            st.session_state.messages.append({"role": "assistant", "content": reply})
                            st.rerun()

                        elif resp.get("type") == "DESTINATION_RECOMMENDATIONS":
                            reply = resp.get("content")
                            st.markdown(reply)
                            st.session_state.messages.append({"role": "assistant", "content": reply})

                        elif resp.get("type") == "BUDGET_COMPARISON":
                            reply = resp.get("content")
                            st.markdown(reply)
                            st.session_state.messages.append({"role": "assistant", "content": reply})

                        elif resp.get("type") == "TRIP_EXPORTED":
                            reply = resp.get("content")
                            st.markdown(reply)
                            st.session_state.messages.append({"role": "assistant", "content": reply})

                        else:
                            reply = resp.get("content", "I am ready to plan your trip! Where would you like to travel?")
                            st.markdown(reply)
                            st.session_state.messages.append({"role": "assistant", "content": reply})


# -------------------------------------------------------------
# RIGHT COLUMN: Live Itinerary & Budget Dashboard
# -------------------------------------------------------------
with col_dash:
    st.subheader("🗺️ Live Trip Dashboard")

    trip = st.session_state.active_trip or st.session_state.agent.memory.get_active_trip()

    if not trip:
        st.info("No active trip planned yet. Ask the agent on the left to plan a trip or click a quick prompt to generate an itinerary.")
        
        # Display sample features
        st.markdown("### ✨ Key Features Available")
        f1, f2 = st.columns(2)
        with f1:
            st.markdown("""
            - 🧭 **Regional Pacing:** Eliminates transit fatigue by grouping sights by geographic zones.
            - 🥗 **Dietary Filtering:** Verified authentic lunch stops matching dietary preferences (Veg/Non-Veg).
            - 🌤️ **Live Open-Meteo Weather:** Real-time weather advisories embedded into packing tips.
            """)
        with f2:
            st.markdown("""
            - 💰 **Budget Optimizer:** Compares Eco-Saver, Comfort, and Deluxe alternatives.
            - 📅 **iCalendar (.ics) Export:** Add full day schedules to Google or Apple Calendar.
            - 📄 **Multi-Format Export:** Instant Markdown, JSON, and Print-Ready HTML.
            """)
    else:
        # Trip Header
        st.markdown(f"### 📍 {trip.destination} ({trip.duration_days} Days / {trip.travelers_count} Travelers)")

        # Export Buttons Row
        e1, e2, e3, e4 = st.columns(4)
        exports = ItineraryExporter.export_all(trip, output_dir=os.path.join(ROOT_DIR, "exports"))
        ics_path = CalendarExporter.export(trip, start_date=date.today(), output_dir=os.path.join(ROOT_DIR, "exports"))

        with e1:
            with open(exports["html"], "r", encoding="utf-8") as f:
                st.download_button("🌐 HTML View", f.read(), file_name=f"{trip.destination}_itinerary.html", mime="text/html", use_container_width=True)
        with e2:
            with open(exports["markdown"], "r", encoding="utf-8") as f:
                st.download_button("📄 Markdown", f.read(), file_name=f"{trip.destination}_itinerary.md", mime="text/markdown", use_container_width=True)
        with e3:
            with open(exports["json"], "r", encoding="utf-8") as f:
                st.download_button("💾 JSON Data", f.read(), file_name=f"{trip.destination}_itinerary.json", mime="application/json", use_container_width=True)
        with e4:
            with open(ics_path, "r", encoding="utf-8") as f:
                st.download_button("📅 Add to Calendar", f.read(), file_name=f"{trip.destination}_calendar.ics", mime="text/calendar", use_container_width=True)

        st.markdown("---")

        # Budget Overview Metric Tiles
        b = trip.budget
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Total Estimated", f"₹{b.total_estimated:,.0f}")
        with m2:
            target_disp = f"₹{b.target_budget:,.0f}" if getattr(b, "target_budget", None) is not None else "N/A"
            st.metric("Target Budget", target_disp)
        with m3:
            st.metric("Per Person", f"₹{b.per_person_estimated:,.0f}")
        with m4:
            status_label = "✅ Under Budget" if not b.is_over_budget else "⚠️ Over Budget"
            st.metric("Budget Status", status_label)

        # Budget Category Breakdown
        with st.expander("📊 Itemized Cost Breakdown", expanded=True):
            bc1, bc2, bc3, bc4, bc5 = st.columns(5)
            bc1.metric("Stay", f"₹{b.accommodation_cost:,.0f}")
            bc2.metric("Food", f"₹{b.food_cost:,.0f}")
            bc3.metric("Transit", f"₹{b.transport_cost:,.0f}")
            bc4.metric("Activities", f"₹{b.activities_cost:,.0f}")
            bc5.metric("Buffer (8%)", f"₹{b.contingency_cost:,.0f}")

        # Day-by-Day Schedule Tabs
        st.markdown("#### 🗓️ Day-by-Day Itinerary")
        day_tabs = st.tabs([f"Day {d.day_number}" for d in trip.days])
        for idx, day in enumerate(trip.days):
            with day_tabs[idx]:
                st.markdown(f"**Theme:** {day.theme}")
                if hasattr(day, "zone") and day.zone:
                    st.caption(f"📍 Geographic Zone: {day.zone}")

                for act in day.activities:
                    act_name = getattr(act, "title", None) or getattr(act, "name", "Activity")
                    cost = getattr(act, "estimated_cost", None) or getattr(act, "entry_fee", 0.0)
                    slot = getattr(act, "time_slot", "Scheduled")
                    hours = getattr(act, "duration_hours", 2.0)
                    desc = getattr(act, "description", "")
                    notes = getattr(act, "notes", "")

                    st.markdown(f"""
                    <div class="badge-card">
                        <strong>⏱️ {slot} ({hours} hrs) — {act_name}</strong> &nbsp;•&nbsp; <em>Fee: ₹{cost:.0f}</em><br/>
                        <span style="font-size: 0.9rem; color: #374151;">{desc}</span>
                        {f'<br/><small style="color: #6B7280;">📌 {notes}</small>' if notes else ''}
                    </div>
                    """, unsafe_allow_html=True)

                if hasattr(day, "lunch_recommendation") and day.lunch_recommendation:
                    st.info(f"🥗 **Lunch Recommendation:** {day.lunch_recommendation}")

                if hasattr(day, "transit_notes") and day.transit_notes:
                    st.caption(f"🚌 Transit Advice: {day.transit_notes}")

        # Travel Tips & Weather
        with st.expander("🛡️ Travel Tips, Weather & Safety Advisories", expanded=False):
            for tip in trip.travel_tips:
                st.markdown(f"• {tip}")
            for adv in trip.safety_advisories:
                st.markdown(f"• {adv}")

        # PRD Mandatory Disclaimer Banner
        st.markdown(f"""
        <div class="disclaimer-banner">
            ⚠️ <strong>Notice:</strong> {trip.booking_disclaimer}
        </div>
        """, unsafe_allow_html=True)

