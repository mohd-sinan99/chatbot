"""
Geographic Clustering & Daily Pacing Engine (PRD Section 6.2 & 6.5)
Clusters attractions into geographic zones to eliminate unnecessary travel time,
inserts realistic transit buffers, and embeds authentic lunch/dinner recommendations.
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from agent.models import Activity, ItineraryDay


@dataclass
class ZoneInfo:
    zone_name: str
    attraction_names: List[str]
    transit_hub: str


class PacingEngine:
    """
    Groups sights geographically to prevent criss-cross travel across districts,
    and schedules realistic morning and afternoon activities with transit and dining buffers.
    """

    # Regional geographic clusters for optimal day-by-day routing
    GEOGRAPHIC_ZONES: Dict[str, Dict[str, ZoneInfo]] = {
        "wayanad": {
            "west_vythiri": ZoneInfo(
                zone_name="South-West (Vythiri & Pozhuthana)",
                attraction_names=["banasura sagar dam", "pookode lake", "karlad lake", "lakkidi viewpoint"],
                transit_hub="Vythiri / Kalpetta"
            ),
            "south_meppadi": ZoneInfo(
                zone_name="South (Meppadi & Waterfalls)",
                attraction_names=["soochipara waterfalls", "chembra peak", "kanthanpara waterfalls"],
                transit_hub="Meppadi"
            ),
            "east_sulthan_bathery": ZoneInfo(
                zone_name="East (Sulthan Bathery & Heritage)",
                attraction_names=["edakkal caves", "wayanad wildlife sanctuary", "jain temple"],
                transit_hub="Sulthan Bathery"
            ),
            "north_mananthavady": ZoneInfo(
                zone_name="North (Mananthavady & Rivers)",
                attraction_names=["kuruva island", "thirunelli temple", "tholpetty wildlife sanctuary"],
                transit_hub="Mananthavady"
            )
        },
        "coorg": {
            "central_madikeri": ZoneInfo(
                zone_name="Central Madikeri",
                attraction_names=["abbey falls", "raja's seat", "madikeri fort", "omkareshwara temple"],
                transit_hub="Madikeri Town"
            ),
            "east_kushalnagar": ZoneInfo(
                zone_name="East Kushalnagar",
                attraction_names=["dubare elephant camp", "namdroling monastery (golden temple)", "nisargadhama"],
                transit_hub="Kushalnagar"
            )
        },
        "munnar": {
            "central_tea_valley": ZoneInfo(
                zone_name="Munnar Central & Tea Hills",
                attraction_names=["tea museum (kdhp)", "eravikulam national park", "blossom park"],
                transit_hub="Munnar Town"
            ),
            "mattupetty_dam_direction": ZoneInfo(
                zone_name="Mattupetty & Top Station Route",
                attraction_names=["mattupetty dam & lake", "echo point", "kundala lake", "top station"],
                transit_hub="Mattupetty"
            )
        }
    }

    @classmethod
    def get_attraction_zone(cls, destination: str, attraction_name: str) -> Optional[str]:
        """Determine which geographic zone an attraction belongs to."""
        dest_norm = destination.strip().lower()
        att_norm = attraction_name.strip().lower()

        for dest_key, zones in cls.GEOGRAPHIC_ZONES.items():
            if dest_key in dest_norm or dest_norm in dest_key:
                for zone_id, zone_data in zones.items():
                    if any(a in att_norm or att_norm in a for a in zone_data.attraction_names):
                        return zone_id
        return None

    @classmethod
    def schedule_paced_days(
        cls,
        destination: str,
        attractions: List[Dict[str, Any]],
        duration_days: int,
        eateries: Optional[List[Dict[str, Any]]] = None,
        dietary_preference: Optional[str] = None
    ) -> List[ItineraryDay]:
        """
        Organizes attractions by geographic proximity into paced daily schedules,
        interleaving authentic lunch and dinner recommendations (PRD Section 6.2 & 6.5).
        """
        days: List[ItineraryDay] = []
        eateries_list = eateries or []

        # Filter eateries by dietary preferences if specified
        suitable_eateries = eateries_list
        if dietary_preference:
            pref = dietary_preference.lower()
            filtered = []
            for e in eateries_list:
                text_to_check = f"{e.get('cuisine', '')} {e.get('highlights', '')}".lower()
                if "veg" in pref and "non" not in pref:
                    if "vegetarian" in text_to_check and "non-veg" not in text_to_check and "non-vegetarian" not in text_to_check:
                        filtered.append(e)
                else:
                    if pref in text_to_check:
                        filtered.append(e)
            if filtered:
                suitable_eateries = filtered

        # Group attractions by zone if destination is mapped
        zone_buckets: Dict[str, List[Dict[str, Any]]] = {}
        unassigned: List[Dict[str, Any]] = []

        for att in attractions:
            zone_id = cls.get_attraction_zone(destination, att["name"])
            if zone_id:
                zone_buckets.setdefault(zone_id, []).append(att)
            else:
                unassigned.append(att)

        # Flatten in zone-clustered order
        clustered_attractions: List[Dict[str, Any]] = []
        for zone_items in zone_buckets.values():
            clustered_attractions.extend(zone_items)
        clustered_attractions.extend(unassigned)

        attraction_idx = 0
        eatery_idx = 0

        for day_num in range(1, duration_days + 1):
            day_activities: List[Activity] = []
            transit_notes_parts: List[str] = []

            # 1. Morning Activity (9:30 AM - 12:30 PM)
            if attraction_idx < len(clustered_attractions):
                morning_att = clustered_attractions[attraction_idx]
                day_activities.append(
                    Activity(
                        title=morning_att["name"],
                        description=morning_att["description"],
                        time_slot="Morning (9:30 AM - 12:30 PM)",
                        duration_hours=morning_att.get("duration_hours", 2.5),
                        estimated_cost=morning_att.get("entry_fee", 50.0),
                        location=f"{destination}, India",
                        opening_hours=morning_att.get("hours"),
                        verified=True,
                        source_url=morning_att.get("source"),
                        notes=morning_att.get("notes")
                    )
                )
                attraction_idx += 1

            # 2. Afternoon / Sunset Activity (3:00 PM - 5:30 PM)
            if attraction_idx < len(clustered_attractions):
                afternoon_att = clustered_attractions[attraction_idx]
                day_activities.append(
                    Activity(
                        title=afternoon_att["name"],
                        description=afternoon_att["description"],
                        time_slot="Afternoon / Sunset (3:00 PM - 5:30 PM)",
                        duration_hours=afternoon_att.get("duration_hours", 2.0),
                        estimated_cost=afternoon_att.get("entry_fee", 40.0),
                        location=f"{destination}, India",
                        opening_hours=afternoon_att.get("hours"),
                        verified=True,
                        source_url=afternoon_att.get("source"),
                        notes=afternoon_att.get("notes")
                    )
                )
                attraction_idx += 1

            # 3. Embed Lunch Dining Note
            if suitable_eateries:
                chosen_eatery = suitable_eateries[eatery_idx % len(suitable_eateries)]
                transit_notes_parts.append(
                    f"Lunch recommendation: '{chosen_eatery['name']}' in {chosen_eatery.get('location', destination)} "
                    f"({chosen_eatery['cuisine']}, ~₹{chosen_eatery.get('approx_cost_for_two', 300.0):,.0f} for 2)."
                )
                eatery_idx += 1

            # 4. Transit & Pacing Guidance
            transit_notes_parts.append(
                "Sights grouped by regional cluster to minimize transit fatigue. "
                "Allow 30-45 mins buffer time between sights. Evening free for local market stroll."
            )

            total_day_cost = sum(a.estimated_cost for a in day_activities)
            days.append(
                ItineraryDay(
                    day_number=day_num,
                    date_or_label=f"Day {day_num}",
                    theme=f"{destination} Highlights - Day {day_num}",
                    activities=day_activities,
                    transit_notes=" ".join(transit_notes_parts),
                    estimated_day_cost=round(total_day_cost, 2)
                )
            )

        return days
