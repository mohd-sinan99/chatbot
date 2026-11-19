"""
Intent Classifier & Clarification Router (PRD Section 7, 8, 11)
Identifies user intent and detects missing required travel details.
Enforces the 'one clear question at a time' rule to prevent interrogation fatigue.
"""

import re
from enum import Enum
from typing import Dict, Any, Optional, List, Tuple
from agent.models import UserPreferences


class UserIntent(str, Enum):
    NEW_TRIP = "NEW_TRIP"
    CLARIFY_INFO = "CLARIFY_INFO"
    EXPLORE_DESTINATIONS = "EXPLORE_DESTINATIONS"
    REFINE_PLAN = "REFINE_PLAN"
    GENERAL_QUERY = "GENERAL_QUERY"


class IntentRouter:
    """
    Classifies user intent and verifies if mandatory parameters are present.
    """

    @staticmethod
    def classify_intent(
        user_message: str,
        has_active_trip: bool = False,
        awaiting_clarification: bool = False
    ) -> UserIntent:
        """Classify user intent based on message keywords and session state."""
        msg = user_message.lower().strip()

        # If we previously asked a clarification question, interpret this as answering it
        if awaiting_clarification:
            return UserIntent.CLARIFY_INFO

        # Revisions to active trip (PRD Section 6.8)
        refine_keywords = [
            "change", "modify", "update", "replace", "swap", "make it",
            "add a day", "remove", "more relaxing", "switch hotel",
            "increase budget", "reduce budget", "cheaper"
        ]
        if has_active_trip and any(k in msg for k in refine_keywords):
            return UserIntent.REFINE_PLAN

        # Destination discovery (PRD Section 6.1)
        explore_keywords = [
            "suggest destination", "where should i go", "destination ideas",
            "recommend places", "places to visit from", "weekend getaway ideas"
        ]
        if any(k in msg for k in explore_keywords) or (
            "where" in msg and ("go" in msg or "travel" in msg or "visit" in msg)
        ):
            return UserIntent.EXPLORE_DESTINATIONS

        # New trip planning (PRD Section 6.2)
        plan_keywords = ["plan", "itinerary", "trip to", "visit", "travel to", "going to"]
        if any(k in msg for k in plan_keywords):
            return UserIntent.NEW_TRIP

        # Fallback
        return UserIntent.NEW_TRIP if ("to" in msg or "days" in msg or "trip" in msg) else UserIntent.GENERAL_QUERY

    @staticmethod
    def evaluate_missing_information(
        user_prompt: str,
        user_prefs: UserPreferences
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        """
        Detects missing essential travel inputs (PRD Section 7).
        Follows Section 11 rule: 'Ask only one clear question at a time when essential information is missing'.
        Returns:
            (extracted_params: dict, next_clarification_question: Optional[str])
        """
        text = user_prompt.lower()
        extracted: Dict[str, Any] = {}

        # 1. Destination Check (Essential - Required)
        known_destinations = ["wayanad", "coorg", "munnar", "ooty", "mysore", "goa", "chikmagalur", "kodaikanal"]
        for dest in known_destinations:
            if dest in text:
                extracted["destination"] = dest.title()
                break

        # Check for destination via regex pattern "trip to X", "visit X"
        if "destination" not in extracted:
            match = re.search(r'(?:to|visit|in)\s+([a-zA-Z]+)(?:\s|$|,|\.)', text)
            if match and match.group(1).lower() not in ["a", "the", "my", "our", "two", "three", "bangalore"]:
                extracted["destination"] = match.group(1).title()

        # If destination is completely absent and not exploring, ask for it first
        if "destination" not in extracted:
            question = (
                "Where would you like to travel? "
                "(For example: Wayanad, Coorg, Munnar, or ask me for weekend recommendations!)"
            )
            return extracted, question

        # 2. Duration Check (Essential if travel dates are unknown)
        if any(w in text for w in ["2-day", "2 day", "two day", "two-day", "weekend"]):
            extracted["duration_days"] = 2
        elif any(w in text for w in ["3-day", "3 day", "three day", "three-day"]):
            extracted["duration_days"] = 3
        elif any(w in text for w in ["1-day", "1 day", "one day", "day trip"]):
            extracted["duration_days"] = 1
        elif any(w in text for w in ["4-day", "4 day", "four day"]):
            extracted["duration_days"] = 4

        # If duration missing, ask one clear question
        if "duration_days" not in extracted:
            question = f"How many days would you like to plan your trip to {extracted['destination']} for?"
            return extracted, question

        # 3. Travelers Check (Can fallback to user profile default)
        if "two people" in text or "2 people" in text or "couple" in text:
            extracted["travelers"] = 2
        elif "solo" in text or "1 person" in text:
            extracted["travelers"] = 1
        elif "family" in text or "4 people" in text:
            extracted["travelers"] = 4
        else:
            extracted["travelers"] = user_prefs.default_travelers

        # 4. Budget Check (Can estimate if missing, but helpful to extract)
        budget_match = re.search(r'(?:₹|rs\.?|inr)\s?([0-9,]+)', text)
        if budget_match:
            clean_num = budget_match.group(1).replace(",", "")
            extracted["budget"] = float(clean_num)

        # 5. Origin Check
        if "from bangalore" in text or "bangalore" in text:
            extracted["origin"] = "Bangalore"
        elif "from kozhikode" in text or "kozhikode" in text:
            extracted["origin"] = "Kozhikode"
        else:
            extracted["origin"] = user_prefs.starting_location or "Bangalore"

        # All essential information is present
        return extracted, None

