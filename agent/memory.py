"""
Persistent Memory Store (📘 L4: Memory between tasks)
Persists user travel preferences, past itineraries, and active session context to disk.
"""

import json
import os
from typing import Dict, Any, Optional, List
from agent.models import UserPreferences, TripPlan


class TripMemoryStore:
    """
    Manages long-term and working memory across sessions and tasks.
    Stores user preferences (diet, budget style, starting city),
    past itineraries, and the currently active trip plan.
    """

    def __init__(self, storage_path: str = "data/memory.json"):
        self.storage_path = storage_path
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        """Ensure storage directory and JSON file exist with default structure."""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        if not os.path.exists(self.storage_path):
            initial_data = {
                "users": {
                    "default_user": UserPreferences(user_id="default_user").to_dict()
                },
                "trips": {},
                "active_trip_id": None,
            }
            self._write_file(initial_data)

    def _read_file(self) -> Dict[str, Any]:
        """Read data from persistent JSON file with graceful fallback."""
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"users": {}, "trips": {}, "active_trip_id": None}

    def _write_file(self, data: Dict[str, Any]) -> None:
        """Write data atomically to persistent JSON file."""
        temp_path = f"{self.storage_path}.tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(temp_path, self.storage_path)

    # --- User Preferences (L4: Long-Term Memory) ---

    def get_user_preferences(self, user_id: str = "default_user") -> UserPreferences:
        """Retrieve user preferences or return default if not found."""
        data = self._read_file()
        user_dict = data.get("users", {}).get(user_id)
        if user_dict:
            return UserPreferences.from_dict(user_dict)
        return UserPreferences(user_id=user_id)

    def save_user_preferences(self, prefs: UserPreferences) -> None:
        """Persist updated user preferences."""
        data = self._read_file()
        if "users" not in data:
            data["users"] = {}
        data["users"][prefs.user_id] = prefs.to_dict()
        self._write_file(data)

    def record_destination_visit(self, user_id: str, destination: str) -> None:
        """Record a visited destination to memory so agent avoids repeating suggestions unnecessarily."""
        prefs = self.get_user_preferences(user_id)
        if destination not in prefs.past_destinations:
            prefs.past_destinations.append(destination)
            self.save_user_preferences(prefs)

    # --- Trip Plans (L4: Task-to-Task Knowledge) ---

    def save_trip_plan(self, plan: TripPlan) -> None:
        """Save a trip plan and mark it as active."""
        data = self._read_file()
        if "trips" not in data:
            data["trips"] = {}
        data["trips"][plan.trip_id] = plan.to_dict()
        data["active_trip_id"] = plan.trip_id
        self._write_file(data)

    def get_trip_plan(self, trip_id: str) -> Optional[TripPlan]:
        """Retrieve a specific trip plan by ID."""
        data = self._read_file()
        trip_dict = data.get("trips", {}).get(trip_id)
        if trip_dict:
            return TripPlan.from_dict(trip_dict)
        return None

    def list_all_trips(self) -> List[TripPlan]:
        """List all trips in memory."""
        data = self._read_file()
        trips = []
        for t_dict in data.get("trips", {}).values():
            trips.append(TripPlan.from_dict(t_dict))
        return trips

    # --- Working Session Memory (L4: Active Trip Resume) ---

    def get_active_trip(self) -> Optional[TripPlan]:
        """Get the currently active trip being drafted or refined."""
        data = self._read_file()
        active_id = data.get("active_trip_id")
        if active_id:
            return self.get_trip_plan(active_id)
        return None

    def set_active_trip_id(self, trip_id: Optional[str]) -> None:
        """Set or clear active trip ID."""
        data = self._read_file()
        data["active_trip_id"] = trip_id
        self._write_file(data)

    def clear_all(self) -> None:
        """Reset memory store (useful for testing)."""
        data = {
            "users": {
                "default_user": UserPreferences(user_id="default_user").to_dict()
            },
            "trips": {},
            "active_trip_id": None,
        }
        self._write_file(data)

