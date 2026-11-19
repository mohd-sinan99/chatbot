"""
Configuration and constants for Smart Travel Planner AI Agent.
"""

import os
from typing import Dict, Any

# Environment & Model Config
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
DEFAULT_MODEL = os.getenv("AGENT_MODEL", "gemini-1.5-flash")

# Safety & Execution Limits (📘 L7: Safety)
DEFAULT_MAX_STEPS = int(os.getenv("MAX_STEPS", "10"))
REQUIRE_HUMAN_APPROVAL_ON_OVERRUN = True
OVERRUN_PERCENTAGE_THRESHOLD = 0.05  # Trigger human approval if > 5% over budget

# Storage Paths (📘 L4: Memory)
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
MEMORY_FILE_PATH = os.path.join(DATA_DIR, "memory.json")

# Default Assumptions for Travel Estimates (PRD Section 6.3 & 10)
DEFAULT_COST_ASSUMPTIONS: Dict[str, Any] = {
    "currency": "INR",
    "accommodation_per_night": {
        "budget": 1200.0,
        "moderate": 2800.0,
        "luxury": 6500.0,
    },
    "food_per_person_per_day": {
        "budget": 450.0,
        "moderate": 900.0,
        "luxury": 2000.0,
    },
    "local_commute_per_day": {
        "budget": 300.0,      # public transit / shared auto
        "moderate": 800.0,    # private cab / auto
        "luxury": 1800.0,     # premium dedicated taxi
    },
    "contingency_percentage": 0.08,  # 8% buffer for unexpected expenses
}

