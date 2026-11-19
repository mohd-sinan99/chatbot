"""
Travel Advisory, Safety & Weather Tool (📘 L2: Tool 4 of 4)
Provides destination weather conditions, live forecast (Open-Meteo), packing recommendations,
safety advisories, and local travel rules (PRD Section 6.7).
"""

from typing import Dict, Any, Optional
from agent.tools.base import BaseTool
from agent.tools.weather_service import WeatherService


class TravelAdvisoryTool(BaseTool):
    """Tool to provide safety advisories, live weather insights, permits, and packing guidelines."""

    ADVISORIES: Dict[str, Dict[str, Any]] = {
        "wayanad": {
            "climate_summary": (
                "Mild hill-station climate. Monsoons (June-September) bring heavy rainfall and lush scenery. "
                "Winter (October-February) is pleasant (15°C - 26°C), ideal for sightseeing and trekking."
            ),
            "best_time_to_visit": "October to May",
            "packing_essentials": [
                "Comfortable walking / trekking shoes with good grip",
                "Light woollens or jacket for chilly mornings/evenings",
                "Raincoat or umbrella (essential during monsoon/post-monsoon)",
                "Leech socks and insect repellent for nature trails",
                "Reusable water bottle (plastic water bottles discouraged)"
            ],
            "safety_and_rules": [
                "Night Travel Ban: NH-766 through Bandipur/Muthanga Tiger Reserve is closed to regular traffic between 9:00 PM and 6:00 AM.",
                "Plastic-Free Zone: Wayanad strictly enforces curbs on single-use plastics and disposable bottles at tourist spots.",
                "Forest Permits: Sights like Chembra Peak and trekking trails require passes issued by the Kerala Forest Department; daily visitor quotas are capped.",
                "Monsoon Safety: Avoid venturing close to swollen streams, waterfalls, or steep slippery boulders after heavy rainfall."
            ],
            "official_portal": "https://dtpcwayanad.com"
        },
        "coorg": {
            "climate_summary": "Pleasant climate throughout the year (15°C - 28°C). Heavy monsoon downpours from June to August.",
            "best_time_to_visit": "October to March",
            "packing_essentials": [
                "Sweaters / jackets for cool evenings",
                "Hiking shoes for plantation walks",
                "Umbrella during monsoon months"
            ],
            "safety_and_rules": [
                "Driving: Exercise caution on winding ghat roads with sharp hairpin turns.",
                "Respect local Kodava culture and plantation private boundaries."
            ],
            "official_portal": "https://karnatakatourism.org"
        },
        "munnar": {
            "climate_summary": "Cool highland climate year-round (10°C - 22°C). Nights can dip below 10°C in winter.",
            "best_time_to_visit": "September to April",
            "packing_essentials": [
                "Warm fleece or jacket for evenings and early morning tea garden visits",
                "Good walking shoes with traction"
            ],
            "safety_and_rules": [
                "Fog advisory: Mountain roads can encounter thick mist and reduced visibility in the afternoon.",
                "Eravikulam National Park is closed to visitors during the Nilgiri Tahr calving season (February - March)."
            ],
            "official_portal": "https://keralatourism.org"
        }
    }

    @property
    def name(self) -> str:
        return "get_travel_advisory_and_weather"

    @property
    def description(self) -> str:
        return (
            "Retrieve live real-time weather conditions, seasonal patterns, packing essentials, "
            "regional safety alerts, and local regulations (e.g. night travel bans, forest permits) for a destination."
        )

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "destination": {
                    "type": "string",
                    "description": "Destination name (e.g. 'Wayanad', 'Coorg', 'Munnar')"
                },
                "season_or_month": {
                    "type": "string",
                    "description": "Specific travel month or season (optional)"
                }
            },
            "required": ["destination"]
        }

    def execute(self, destination: str, season_or_month: Optional[str] = None) -> Dict[str, Any]:
        normalized = destination.strip().lower()
        matched = None
        for key in self.ADVISORIES:
            if key in normalized or normalized in key:
                matched = self.ADVISORIES[key]
                break

        # Query live weather forecast (Open-Meteo)
        live_weather = WeatherService.get_live_forecast(destination)

        if matched:
            data = dict(matched)
            if season_or_month:
                data["queried_season"] = season_or_month
            data["destination"] = destination.title()
            data["live_weather"] = live_weather
            return data
        else:
            return {
                "destination": destination.title(),
                "climate_summary": "Standard regional seasonal climate. Moderate temperatures during spring and autumn.",
                "best_time_to_visit": "Post-monsoon and winter months (October - March)",
                "packing_essentials": [
                    "Comfortable walking shoes",
                    "Season-appropriate clothing and weather gear",
                    "Personal medication, power bank, and identification cards"
                ],
                "safety_and_rules": [
                    "Check local weather forecasts before setting out on outdoor trails.",
                    "Verify opening hours and ticket counters before visiting major cultural sites.",
                    "Keep emergency local contact numbers and valid ID proofs handy."
                ],
                "official_portal": "https://incredibleindia.org",
                "live_weather": live_weather
            }
