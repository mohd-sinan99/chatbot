"""
Live Weather Service (PRD Section 6.7 & Phase 3 Retrieval)
Integrates Open-Meteo free API for live real-time weather forecasts and seasonal advisories.
Includes graceful offline fallback if network is unavailable.
"""

import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, Tuple


class WeatherService:
    """Fetches real-time weather forecasts using Open-Meteo API with fallback."""

    COORDINATES: Dict[str, Tuple[float, float]] = {
        "wayanad": (11.6854, 76.1320),
        "coorg": (12.4244, 75.7382),
        "munnar": (10.0889, 77.0595),
        "ooty": (11.4102, 76.6950),
        "mysore": (12.2958, 76.6394),
        "goa": (15.2993, 74.1240),
        "bangalore": (12.9716, 77.5946),
    }

    WEATHER_CODES: Dict[int, str] = {
        0: "Clear sky ☀️",
        1: "Mainly clear 🌤️",
        2: "Partly cloudy ⛅",
        3: "Overcast ☁️",
        45: "Foggy 🌫️",
        48: "Depositing rime fog 🌫️",
        51: "Light drizzle 🌧️",
        53: "Moderate drizzle 🌧️",
        55: "Dense drizzle 🌧️",
        61: "Slight rain 🌦️",
        63: "Moderate rain 🌧️",
        65: "Heavy rain ⛈️",
        71: "Slight snow fall 🌨️",
        80: "Slight rain showers 🌦️",
        81: "Moderate rain showers 🌧️",
        82: "Violent rain showers ⛈️",
        95: "Thunderstorm ⚡",
    }

    @classmethod
    def get_live_forecast(cls, destination: str, timeout_sec: int = 4) -> Dict[str, Any]:
        """
        Fetch real-time weather data for a given destination.
        Returns live weather dict or sensible offline fallback.
        """
        norm = destination.strip().lower()
        coords = None
        for key, (lat, lon) in cls.COORDINATES.items():
            if key in norm or norm in key:
                coords = (lat, lon)
                break

        if not coords:
            # Default to South India hill station coords (Wayanad)
            coords = cls.COORDINATES["wayanad"]

        lat, lon = coords
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}&current_weather=true"
        )

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SmartTravelPlanner/1.0"})
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    current = data.get("current_weather", {})
                    code = current.get("weathercode", 0)
                    temp = current.get("temperature", 22.0)
                    wind = current.get("windspeed", 5.0)
                    condition = cls.WEATHER_CODES.get(code, "Pleasant")

                    # Generate dynamic advisory based on weather
                    advisory = "Favorable conditions for outdoor sightseeing."
                    if code in [51, 53, 55, 61, 63, 65, 80, 81, 82, 95]:
                        advisory = "Rain expected. Carry rain gear, sturdy footwear, and allow extra transit time on hill roads."
                    elif temp > 32:
                        advisory = "Warm temperatures. Stay hydrated, carry sunscreen and sun hats."
                    elif temp < 15:
                        advisory = "Chilly mornings and evenings. Carry warm fleece or jackets."

                    return {
                        "is_live": True,
                        "temperature_celsius": temp,
                        "windspeed_kmh": wind,
                        "condition": condition,
                        "weather_code": code,
                        "dynamic_advisory": advisory,
                        "source": "Open-Meteo Live API"
                    }
        except Exception:
            # Graceful offline fallback
            pass

        return {
            "is_live": False,
            "temperature_celsius": 22.5,
            "windspeed_kmh": 6.0,
            "condition": "Pleasant / Partly Cloudy ⛅",
            "weather_code": 2,
            "dynamic_advisory": "Standard seasonal hill station conditions. Light jacket recommended for evenings.",
            "source": "Standard Seasonal Historical Baseline (Offline Fallback)"
        }

