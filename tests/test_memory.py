"""
Unit tests for Persistent Memory Store (📘 L4: Memory between tasks)
Tests user preferences persistence, trip plan serialization, and active session resumption.
"""

import os
import shutil
import tempfile
import unittest

from agent.models import UserPreferences, TripPlan, BudgetBreakdown, ItineraryDay, Activity
from agent.memory import TripMemoryStore


class TestTripMemoryStore(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.storage_path = os.path.join(self.test_dir, "test_memory.json")
        self.store = TripMemoryStore(storage_path=self.storage_path)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_default_user_preferences(self):
        """Test retrieving default preferences for a new user."""
        prefs = self.store.get_user_preferences("user_123")
        self.assertEqual(prefs.user_id, "user_123")
        self.assertEqual(prefs.travel_style, "budget")
        self.assertEqual(prefs.preferred_currency, "INR")

    def test_save_and_update_preferences(self):
        """Test persisting and updating preferences across tasks (L4)."""
        prefs = UserPreferences(
            user_id="alice",
            starting_location="Bangalore",
            default_travelers=2,
            dietary_preferences=["Vegetarian"],
            interests=["Wildlife", "Coffee plantations"],
            travel_style="budget",
        )
        self.store.save_user_preferences(prefs)

        # Re-instantiate store from disk to verify true persistence
        new_store_instance = TripMemoryStore(storage_path=self.storage_path)
        loaded = new_store_instance.get_user_preferences("alice")

        self.assertEqual(loaded.user_id, "alice")
        self.assertEqual(loaded.starting_location, "Bangalore")
        self.assertIn("Coffee plantations", loaded.interests)

    def test_record_destination_visit(self):
        """Test tracking visited destinations to prevent repetitive suggestions."""
        self.store.record_destination_visit("alice", "Wayanad")
        self.store.record_destination_visit("alice", "Munnar")
        # Record duplicate, should not duplicate in list
        self.store.record_destination_visit("alice", "Wayanad")

        loaded = self.store.get_user_preferences("alice")
        self.assertEqual(loaded.past_destinations, ["Wayanad", "Munnar"])

    def test_save_and_retrieve_trip_plan(self):
        """Test saving and retrieving full trip plans with days and budget (L4)."""
        act1 = Activity(
            title="Banasura Sagar Dam",
            description="Visit the largest earthen dam in India.",
            time_slot="Morning",
            duration_hours=2.5,
            estimated_cost=200.0,
            location="Padinjarathara, Wayanad",
            verified=True,
            source_url="https://dtpcwayanad.com"
        )
        day1 = ItineraryDay(
            day_number=1,
            date_or_label="Day 1",
            theme="Scenic Lakes & Nature",
            activities=[act1],
            transit_notes="Local auto from Kalpetta",
            estimated_day_cost=700.0
        )
        budget = BudgetBreakdown(
            currency="INR",
            transport_cost=1000.0,
            accommodation_cost=1500.0,
            food_cost=900.0,
            activities_cost=400.0,
            total_estimated=4000.0,
            per_person_estimated=2000.0,
            target_budget=5000.0,
            is_over_budget=False,
            assumptions=["1 double room homestay", "Standard local meals"]
        )
        plan = TripPlan(
            trip_id="trip_wayanad_01",
            destination="Wayanad",
            origin="Bangalore",
            duration_days=2,
            travelers_count=2,
            days=[day1],
            budget=budget,
            travel_tips=["Carry umbrellas during monsoon", "Book cave tickets early"],
            safety_advisories=["Follow forest department warnings around ghats"]
        )

        self.store.save_trip_plan(plan)

        # Retrieve and verify
        retrieved = self.store.get_trip_plan("trip_wayanad_01")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.destination, "Wayanad")
        self.assertEqual(len(retrieved.days), 1)
        self.assertEqual(retrieved.days[0].activities[0].title, "Banasura Sagar Dam")
        self.assertEqual(retrieved.budget.total_estimated, 4000.0)

    def test_active_trip_resume(self):
        """Test retrieving the active trip across tasks."""
        plan = TripPlan(
            trip_id="trip_active_02",
            destination="Coorg",
            origin="Bangalore",
            duration_days=3,
            travelers_count=4,
        )
        self.store.save_trip_plan(plan)

        active = self.store.get_active_trip()
        self.assertIsNotNone(active)
        self.assertEqual(active.trip_id, "trip_active_02")
        self.assertEqual(active.destination, "Coorg")


if __name__ == "__main__":
    unittest.main()

