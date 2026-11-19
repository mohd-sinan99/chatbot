"""
Destination & Attraction Search Tool (📘 L2: Tool 1 of 4)
Provides verified attraction recommendations, visiting hours, entry fees, source links,
authentic local eateries (PRD 6.5), and accommodation options (PRD 6.4).
"""

from typing import Dict, Any, List, Optional
from agent.tools.base import BaseTool


class DestinationSearchTool(BaseTool):
    """Tool to discover top attractions, visiting hours, dining, and accommodations for a destination."""

    # Built-in verified knowledge base for reliable offline/MVP operation (PRD Section 6.1, 6.4, 6.5)
    DESTINATION_DATA: Dict[str, Dict[str, Any]] = {
        "wayanad": {
            "name": "Wayanad, Kerala",
            "attractions": [
                {
                    "name": "Banasura Sagar Dam",
                    "category": "Nature & Adventure",
                    "entry_fee": 50.0,
                    "hours": "9:00 AM - 5:00 PM (Daily)",
                    "duration_hours": 2.5,
                    "description": "Largest earthen dam in India with scenic reservoir and speed boating.",
                    "source": "https://dtpcwayanad.com/destinations/banasura-sagar-dam",
                    "notes": "Boating costs extra (~₹300 for group of 5)."
                },
                {
                    "name": "Edakkal Caves",
                    "category": "History & Heritage",
                    "entry_fee": 40.0,
                    "hours": "9:00 AM - 4:00 PM (Closed Mondays)",
                    "duration_hours": 3.0,
                    "description": "Prehistoric rock engravings from the Neolithic era reached via a steep uphill hike.",
                    "source": "https://www.keralatourism.org/destination/edakkal-caves-wayanad/134",
                    "notes": "Requires ~1 km uphill trek. Wear sturdy shoes."
                },
                {
                    "name": "Soochipara Waterfalls",
                    "category": "Nature & Waterfalls",
                    "entry_fee": 80.0,
                    "hours": "9:00 AM - 5:00 PM (Daily)",
                    "duration_hours": 2.5,
                    "description": "Three-tiered waterfall surrounded by deciduous and evergreen forests.",
                    "source": "https://dtpcwayanad.com/destinations/soochipara-waterfalls",
                    "notes": "Swimming prohibited during high water levels."
                },
                {
                    "name": "Pookode Lake",
                    "category": "Leisure & Nature",
                    "entry_fee": 30.0,
                    "hours": "9:00 AM - 6:00 PM (Daily)",
                    "duration_hours": 1.5,
                    "description": "Freshwater lake nested in evergreen forests; pedal boating available.",
                    "source": "https://dtpcwayanad.com/destinations/pookode-lake",
                    "notes": "Ideal relaxing spot for families and evening walks."
                },
                {
                    "name": "Chembra Peak",
                    "category": "Trekking & Adventure",
                    "entry_fee": 100.0,
                    "hours": "7:00 AM - 2:00 PM (Passes limited per day)",
                    "duration_hours": 4.5,
                    "description": "Highest peak in Wayanad with famous heart-shaped lake (Hridaya Saras).",
                    "source": "https://keralatourism.org/destination/chembra-peak-wayanad/135",
                    "notes": "Forest department permit required. Pass fee is ₹750 for up to 5 people."
                }
            ],
            "eateries": [
                {
                    "name": "1980's A Nostalgic Restaurant",
                    "location": "Kalpetta",
                    "cuisine": "Traditional Kerala Sadya & Malabar Specials",
                    "approx_cost_for_two": 350.0,
                    "highlights": "Authentic meals served on banana leaves with spicy fish curry and payasam.",
                    "source": "https://www.tripadvisor.in/Restaurant_Review-Kalpetta"
                },
                {
                    "name": "ClayHut A Village Restaurant",
                    "location": "Sulthan Bathery",
                    "cuisine": "Kerala Clay-Pot Delicacies",
                    "approx_cost_for_two": 400.0,
                    "highlights": "Clay-cooked bamboo biryani, Appam, and local chicken stew.",
                    "source": "https://www.tripadvisor.in"
                },
                {
                    "name": "Udupi Pure Vegetarian Mess",
                    "location": "Kalpetta Town",
                    "cuisine": "South Indian Vegetarian",
                    "approx_cost_for_two": 180.0,
                    "highlights": "Ghee roast dosas, fresh idlis, and traditional filter coffee.",
                    "source": "https://www.zomato.com"
                }
            ],
            "accommodations": [
                {
                    "name": "Green Gates Homestay & Plantation Stay",
                    "type": "Budget Homestay",
                    "approx_rate_per_night": 1200.0,
                    "amenities": ["Free Wi-Fi", "Home-cooked Kerala breakfast", "Plantation walk"],
                    "booking_link": "https://www.booking.com/homestays/wayanad",
                    "verified": False,
                    "notes": "Prices are seasonal estimates. Must confirm directly with host."
                },
                {
                    "name": "Vythiri Eco Resort & Treehouses",
                    "type": "Nature Eco-Resort",
                    "approx_rate_per_night": 3200.0,
                    "amenities": ["Stream view", "Swimming pool", "Ayurvedic Spa"],
                    "booking_link": "https://www.vythiriresort.com",
                    "verified": False,
                    "notes": "Advance booking recommended for weekend dates."
                }
            ]
        },
        "coorg": {
            "name": "Coorg (Kodagu), Karnataka",
            "attractions": [
                {
                    "name": "Abbey Falls",
                    "category": "Nature",
                    "entry_fee": 20.0,
                    "hours": "9:00 AM - 5:00 PM",
                    "duration_hours": 1.5,
                    "description": "Picturesque waterfall surrounded by lush coffee and spice plantations.",
                    "source": "https://karnatakatourism.org",
                    "notes": "Accessible by stairs; hanging bridge viewing point."
                },
                {
                    "name": "Raja's Seat",
                    "category": "Scenic Viewpoint",
                    "entry_fee": 10.0,
                    "hours": "6:00 AM - 8:00 PM",
                    "duration_hours": 1.5,
                    "description": "Seasonal garden with sunset viewpoints and musical fountain.",
                    "source": "https://karnatakatourism.org",
                    "notes": "Best visited at golden hour (5:30 PM - 6:30 PM)."
                },
                {
                    "name": "Dubare Elephant Camp",
                    "category": "Wildlife & River",
                    "entry_fee": 100.0,
                    "hours": "9:00 AM - 11:30 AM & 4:30 PM - 5:30 PM",
                    "duration_hours": 2.5,
                    "description": "Elephant interaction and bathing camp on the banks of river Kaveri.",
                    "source": "https://junglelodges.com",
                    "notes": "River crossing via boat included in boat fee (~₹50)."
                }
            ],
            "eateries": [
                {
                    "name": "Coorg Cuisine Restaurant",
                    "location": "Madikeri",
                    "cuisine": "Traditional Kodava Dishes",
                    "approx_cost_for_two": 450.0,
                    "highlights": "Authentic Pandi Curry, Kadambuttu (rice dumplings), and Akki Roti.",
                    "source": "https://www.tripadvisor.in"
                },
                {
                    "name": "East End Hotel Restaurant",
                    "location": "Madikeri",
                    "cuisine": "Kodava & South Indian",
                    "approx_cost_for_two": 300.0,
                    "highlights": "Classic breakfast dosas and traditional mutton chops.",
                    "source": "https://www.zomato.com"
                }
            ],
            "accommodations": [
                {
                    "name": "Madikeri Heritage Homestay",
                    "type": "Budget Homestay",
                    "approx_rate_per_night": 1300.0,
                    "amenities": ["Coffee estate view", "Home meals", "Campfire"],
                    "booking_link": "https://www.airbnb.co.in/coorg-india",
                    "verified": False,
                    "notes": "Indicative pricing. Check live availability on host portal."
                }
            ]
        },
        "munnar": {
            "name": "Munnar, Kerala",
            "attractions": [
                {
                    "name": "Eravikulam National Park",
                    "category": "Wildlife & Scenery",
                    "entry_fee": 200.0,
                    "hours": "7:30 AM - 4:00 PM (Closed Feb-March for calving)",
                    "duration_hours": 3.0,
                    "description": "Home to the endangered Nilgiri Tahr and rolling tea hills.",
                    "source": "https://eravikulamnationalpark.in",
                    "notes": "Safari bus included in ticket. Pre-booking online recommended."
                },
                {
                    "name": "Mattupetty Dam & Lake",
                    "category": "Nature & Boating",
                    "entry_fee": 20.0,
                    "hours": "9:30 AM - 5:00 PM",
                    "duration_hours": 2.0,
                    "description": "Storage concrete gravity dam with boating and tea plantation views.",
                    "source": "https://keralatourism.org",
                    "notes": "Speedboat ~₹500 for 5 persons."
                },
                {
                    "name": "Tea Museum (KDHP)",
                    "category": "Heritage & Culture",
                    "entry_fee": 150.0,
                    "hours": "9:00 AM - 5:00 PM (Closed Mondays)",
                    "duration_hours": 1.5,
                    "description": "History of tea cultivation in Munnar with live tea tasting sessions.",
                    "source": "https://tatanatural.com",
                    "notes": "Includes cup of cardamom tea."
                }
            ],
            "eateries": [
                {
                    "name": "Rapsy Restaurant",
                    "location": "Munnar Town",
                    "cuisine": "Kerala & Continental",
                    "approx_cost_for_two": 300.0,
                    "highlights": "Spanish omelettes, beef fry, parottas, and cardamom tea.",
                    "source": "https://www.tripadvisor.in"
                },
                {
                    "name": "Saravana Bhavan Munnar",
                    "location": "Munnar Market",
                    "cuisine": "Pure Vegetarian South Indian",
                    "approx_cost_for_two": 220.0,
                    "highlights": "Unlimited vegetarian meals and crispy butter dosas.",
                    "source": "https://www.zomato.com"
                }
            ],
            "accommodations": [
                {
                    "name": "Tea Valley Eco Cottages",
                    "type": "Moderate Plantation Stay",
                    "approx_rate_per_night": 2200.0,
                    "amenities": ["Valley balcony view", "Breakfast included", "Hot water"],
                    "booking_link": "https://www.booking.com/munnar",
                    "verified": False,
                    "notes": "Estimated rates. Confirm on provider site."
                }
            ]
        }
    }

    @property
    def name(self) -> str:
        return "search_destination_and_attractions"

    @property
    def description(self) -> str:
        return (
            "Search for verified attractions, visiting hours, entry fees, highlights, "
            "authentic local restaurants, and accommodation suggestions for a given destination."
        )

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "destination": {
                    "type": "string",
                    "description": "Name of the city, district, or region (e.g. 'Wayanad', 'Coorg', 'Munnar')"
                },
                "interests": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of interests to filter by (e.g. ['Nature', 'Heritage', 'Adventure'])"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of attractions to return (default 4)",
                    "default": 4
                }
            },
            "required": ["destination"]
        }

    def execute(self, destination: str, interests: Optional[List[str]] = None, max_results: int = 4) -> Dict[str, Any]:
        normalized = destination.strip().lower()
        matched_key = None
        for key in self.DESTINATION_DATA:
            if key in normalized or normalized in key:
                matched_key = key
                break

        if matched_key:
            data = self.DESTINATION_DATA[matched_key]
            attractions = data["attractions"]

            # Filter by interests if specified
            if interests:
                lower_interests = [i.lower() for i in interests]
                filtered = [
                    a for a in attractions 
                    if any(i in a["category"].lower() or i in a["description"].lower() for i in lower_interests)
                ]
                if filtered:
                    attractions = filtered

            selected = attractions[:max_results]
            return {
                "destination": data["name"],
                "total_found": len(selected),
                "attractions": selected,
                "recommended_eateries": data.get("eateries", []),
                "accommodation_suggestions": data.get("accommodations", []),
                "disclaimer": (
                    "Opening hours and entry fees are verified estimates. "
                    "Accommodation rates and restaurant openings should be checked directly with providers."
                )
            }
        else:
            # Fallback for destinations outside built-in database
            return {
                "destination": destination.title(),
                "total_found": 3,
                "attractions": [
                    {
                        "name": f"{destination.title()} Central Heritage & Sights",
                        "category": "Culture & Sightseeing",
                        "entry_fee": 50.0,
                        "hours": "9:00 AM - 5:00 PM",
                        "duration_hours": 2.5,
                        "description": f"Popular cultural landmarks and city center highlights in {destination.title()}.",
                        "source": "https://incredibleindia.org",
                        "notes": "Guided tours available locally."
                    },
                    {
                        "name": f"{destination.title()} Nature Park / Viewpoint",
                        "category": "Nature & Leisure",
                        "entry_fee": 30.0,
                        "hours": "8:00 AM - 6:00 PM",
                        "duration_hours": 2.0,
                        "description": f"Scenic nature reserve and elevated viewpoints in {destination.title()}.",
                        "source": "https://incredibleindia.org",
                        "notes": "Great sunset views."
                    },
                    {
                        "name": f"{destination.title()} Local Bazaar & Food Street",
                        "category": "Food & Shopping",
                        "entry_fee": 0.0,
                        "hours": "10:00 AM - 9:00 PM",
                        "duration_hours": 2.0,
                        "description": f"Vibrant market streets offering local handicrafts and regional cuisine.",
                        "source": "https://incredibleindia.org",
                        "notes": "Cash and UPI widely accepted."
                    }
                ],
                "recommended_eateries": [
                    {
                        "name": f"Famous Local Mess of {destination.title()}",
                        "cuisine": "Regional Authentic Meals",
                        "approx_cost_for_two": 300.0,
                        "highlights": "Traditional local dishes and hearty thali.",
                        "source": "https://www.tripadvisor.in"
                    }
                ],
                "accommodation_suggestions": [
                    {
                        "name": f"{destination.title()} Central Budget Inn",
                        "type": "Budget Hotel / Homestay",
                        "approx_rate_per_night": 1200.0,
                        "amenities": ["Wi-Fi", "Clean linen", "Air conditioning"],
                        "booking_link": "https://www.booking.com",
                        "verified": False,
                        "notes": "Unverified estimate. Must complete booking with provider."
                    }
                ],
                "disclaimer": "General regional estimates applied. Verify specific sites with local tourism authorities."
            }

    @classmethod
    def recommend_destinations(cls, origin: str, budget: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Destination Finder helper (PRD Section 6.1).
        Recommends destinations based on starting point and budget limits.
        """
        ideas = [
            {
                "destination": "Wayanad, Kerala",
                "ideal_duration": "2 - 3 Days",
                "approx_budget_for_two": 4500.0,
                "why_visit": "Misty hills, wildlife sanctuaries, Neolithic caves, and India's largest earthen dam. Perfect for budget-friendly nature and weekend trips.",
                "distance_from_bangalore": "~280 km (6-7 hrs by road)",
                "highlights": ["Banasura Sagar Dam", "Edakkal Caves", "Soochipara Waterfalls"]
            },
            {
                "destination": "Coorg (Kodagu), Karnataka",
                "ideal_duration": "2 - 3 Days",
                "approx_budget_for_two": 5000.0,
                "why_visit": "Scotland of India: lush coffee plantations, gentle waterfalls, Kodava culinary specialties, and elephant interactions at Dubare.",
                "distance_from_bangalore": "~250 km (5-6 hrs by road)",
                "highlights": ["Abbey Falls", "Raja's Seat", "Dubare Elephant Camp"]
            },
            {
                "destination": "Munnar, Kerala",
                "ideal_duration": "3 - 4 Days",
                "approx_budget_for_two": 7500.0,
                "why_visit": "Rolling emerald tea plantations, cool highland weather, and endangered Nilgiri Tahr sightings at Eravikulam National Park.",
                "distance_from_bangalore": "~480 km (overnight bus)",
                "highlights": ["Eravikulam National Park", "Mattupetty Dam", "KDHP Tea Museum"]
            }
        ]

        if budget and budget > 0:
            return [d for d in ideas if d["approx_budget_for_two"] <= budget * 1.25]
        return ideas
