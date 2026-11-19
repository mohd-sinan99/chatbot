"""
Transport Guidance Tool (📘 L2: Tool 3 of 4)
Compares transit options (bus, train, cab, flight) with duration, estimated fares, and booking links.
"""

from typing import Dict, Any, List, Optional
from agent.tools.base import BaseTool


class TransportOptionsTool(BaseTool):
    """Tool to discover and compare transport options between origin and destination."""

    # Built-in transit data for common regional routes
    TRANSIT_ROUTES: Dict[str, List[Dict[str, Any]]] = {
        "bangalore_to_wayanad": [
            {
                "mode": "Overnight KSRTC / Private Bus",
                "duration": "6 - 7 hours (approx. 280 km)",
                "fare_range_inr": "₹450 - ₹1,100 per person (Non-AC vs AC Sleeper)",
                "frequency": "Multiple daily and overnight departures from Majestic/Satellite Bus Stand",
                "provider": "KSRTC (Kerala) / KSRTC (Karnataka) / RedBus",
                "booking_link": "https://online.keralartc.com",
                "notes": "Night travel via Bandipur is subject to night traffic ban (9 PM - 6 AM for certain routes; regular buses use diverted/permitted routes)."
            },
            {
                "mode": "Self-Drive / Private Taxi",
                "duration": "5.5 - 6.5 hours",
                "fare_range_inr": "₹3,500 - ₹5,500 (one-way cab) or fuel cost ~₹2,500",
                "route_via": "Bangalore -> Mysore -> Gundlupet -> Sultan Bathery / Kalpetta",
                "provider": "Local taxi operators / Self-drive rentals",
                "booking_link": "https://www.makemytrip.com/cabs",
                "notes": "Scenic drive through forests. Forest checkposts require vehicle registration check."
            },
            {
                "mode": "Train + Local Bus/Cab",
                "duration": "3 hours (Train to Mysore) + 3 hours (Bus/Cab to Wayanad)",
                "fare_range_inr": "₹150 - ₹600 (Train) + ₹150 (KSRTC bus)",
                "frequency": "Multiple daily trains between Bangalore and Mysore",
                "provider": "IRCTC",
                "booking_link": "https://www.irctc.co.in",
                "notes": "Nearest major railway station is Kozhikode (Calicut) or Mysore. Mysore route is preferred from Bangalore."
            }
        ],
        "bangalore_to_coorg": [
            {
                "mode": "KSRTC Rajahamsa / Airavat Bus",
                "duration": "5.5 - 6.5 hours (approx. 250 km)",
                "fare_range_inr": "₹400 - ₹850 per person",
                "provider": "KSRTC Karnataka",
                "booking_link": "https://www.ksrtc.in",
                "notes": "Frequent services to Madikeri and Kushalnagar."
            },
            {
                "mode": "Private Car / Taxi",
                "duration": "4.5 - 5.5 hours",
                "fare_range_inr": "₹3,000 - ₹4,800 cab",
                "provider": "Local Cabs",
                "booking_link": "https://www.makemytrip.com/cabs",
                "notes": "Smooth drive via Bangalore-Mysore Expressway."
            }
        ],
        "bangalore_to_munnar": [
            {
                "mode": "Overnight Bus (AC Sleeper)",
                "duration": "10 - 11 hours (approx. 480 km)",
                "fare_range_inr": "₹900 - ₹1,800 per person",
                "provider": "Kerala RTC / Private Operators",
                "booking_link": "https://www.redbus.in",
                "notes": "Best to take an overnight sleeper bus arriving early morning."
            },
            {
                "mode": "Train to Aluva/Ernakulam + Bus to Munnar",
                "duration": "9 hours (Train) + 3.5 hours (Hill Bus)",
                "fare_range_inr": "₹400 - ₹1,200 total",
                "provider": "IRCTC / KSRTC",
                "booking_link": "https://www.irctc.co.in",
                "notes": "Scenic winding ghat road up to Munnar."
            }
        ]
    }

    @property
    def name(self) -> str:
        return "find_transport_options"

    @property
    def description(self) -> str:
        return (
            "Find and compare transport routes, transit modes (bus, train, cab), travel times, "
            "and fare estimates between starting origin and destination."
        )

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "origin": {
                    "type": "string",
                    "description": "Starting city (e.g. 'Bangalore', 'Kozhikode', 'Mysore')"
                },
                "destination": {
                    "type": "string",
                    "description": "Destination city (e.g. 'Wayanad', 'Coorg', 'Munnar')"
                },
                "preferred_mode": {
                    "type": "string",
                    "enum": ["bus", "train", "cab", "all"],
                    "description": "Filter by preferred mode of transport (default: 'all')",
                    "default": "all"
                }
            },
            "required": ["origin", "destination"]
        }

    def execute(self, origin: str, destination: str, preferred_mode: str = "all") -> Dict[str, Any]:
        route_key = f"{origin.strip().lower()}_to_{destination.strip().lower()}"
        options = self.TRANSIT_ROUTES.get(route_key)

        if not options:
            # Fallback estimation for arbitrary routes
            options = [
                {
                    "mode": "Intercity Bus / Public Coach",
                    "duration": "Estimated 5 - 8 hours",
                    "fare_range_inr": "₹400 - ₹1,000 per person",
                    "provider": "State Transport Corporation / RedBus",
                    "booking_link": "https://www.redbus.in",
                    "notes": "Check schedules on official state transport portal."
                },
                {
                    "mode": "Private Cab / Rental Vehicle",
                    "duration": "Estimated 4 - 6 hours",
                    "fare_range_inr": "₹12 - ₹18 per km + toll charges",
                    "provider": "Local Cab Providers",
                    "booking_link": "https://www.makemytrip.com/cabs",
                    "notes": "Convenient for group travel and customized halts."
                }
            ]

        if preferred_mode != "all":
            filtered = [
                opt for opt in options 
                if preferred_mode.lower() in opt["mode"].lower()
            ]
            if filtered:
                options = filtered

        return {
            "origin": origin.title(),
            "destination": destination.title(),
            "options": options,
            "disclaimer": (
                "Timetables and fares are estimates subject to dynamic pricing, seasonal demand, and seat availability. "
                "Bookings must be confirmed directly with official transport providers."
            )
        }

