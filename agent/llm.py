"""
LLM Adapter (Phase 6 — Real LLM Integration, L8 Tier-2)
Provides a unified interface to the Gemini API (google.generativeai) when
GEMINI_API_KEY is set, with a transparent rule-based fallback when it is not.

This keeps the entire codebase stdlib-compatible:
  - No external package is imported at module level.
  - The Gemini SDK is imported lazily inside GeminiLLMBackend only if the key
    is present and the user explicitly requests a live call.
"""

import os
import json
import re
import urllib.request
import urllib.error
from typing import Optional, Dict, Any


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

class LLMResponse:
    """Thin wrapper around a raw LLM text response."""

    def __init__(self, text: str, model: str, via_api: bool = False):
        self.text = text
        self.model = model
        self.via_api = via_api      # True when produced by a live API call

    def __repr__(self) -> str:
        src = "Gemini API" if self.via_api else "rule-based fallback"
        return f"<LLMResponse model={self.model!r} via={src} len={len(self.text)}>"


class LLMAdapter:
    """
    Unified LLM interface used throughout the agent.

    Priority:
      1. If GEMINI_API_KEY is set → call Gemini 1.5 Flash REST endpoint.
      2. Otherwise              → rule-based template fallback (no API).

    Usage::

        llm = LLMAdapter()
        resp = llm.generate("Summarise Wayanad in 2 sentences.")
        print(resp.text, resp.via_api)
    """

    _GEMINI_API_URL = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-1.5-flash:generateContent?key={api_key}"
    )
    MODEL_NAME = "gemini-1.5-flash"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")

    @property
    def has_api_key(self) -> bool:
        return bool(self.api_key)

    # ------------------------------------------------------------------
    # Core generate method
    # ------------------------------------------------------------------

    def generate(
        self,
        prompt: str,
        system_instruction: str = "",
        temperature: float = 0.4,
        max_output_tokens: int = 2048,
    ) -> LLMResponse:
        """
        Generate text for `prompt`.

        When GEMINI_API_KEY is set the call goes live; otherwise the
        rule-based fallback is returned so tests never need a key.
        """
        if self.has_api_key:
            try:
                return self._call_gemini_rest(
                    prompt=prompt,
                    system_instruction=system_instruction,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                )
            except Exception as exc:   # Network error, quota, etc.
                # Graceful degradation: fall through to rule-based
                fallback = self._rule_based_response(prompt)
                fallback.text = (
                    f"[Gemini API error: {exc}. Using rule-based fallback.]\n\n"
                    + fallback.text
                )
                return fallback
        else:
            return self._rule_based_response(prompt)

    # ------------------------------------------------------------------
    # Gemini REST backend (pure urllib — zero external dependencies)
    # ------------------------------------------------------------------

    def _call_gemini_rest(
        self,
        prompt: str,
        system_instruction: str = "",
        temperature: float = 0.4,
        max_output_tokens: int = 2048,
    ) -> LLMResponse:
        """Call the Gemini REST API using stdlib urllib."""
        url = self._GEMINI_API_URL.format(api_key=self.api_key)

        payload: Dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_output_tokens,
            },
        }
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )

        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode("utf-8"))

        # Extract text from response
        text = (
            body.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )
        return LLMResponse(text=text, model=self.MODEL_NAME, via_api=True)

    # ------------------------------------------------------------------
    # Rule-based fallback (no API key required)
    # ------------------------------------------------------------------

    def _rule_based_response(self, prompt: str) -> LLMResponse:
        """
        Deterministic keyword-driven response generator.
        Covers the most common travel planning query shapes so the
        agent remains fully functional without an API key.
        """
        p = prompt.lower()
        text = self._match_rule(p)
        return LLMResponse(text=text, model="rule-based", via_api=False)

    @staticmethod
    def _match_rule(prompt_lower: str) -> str:
        # Summarise destination
        if "summarise" in prompt_lower or "summarize" in prompt_lower:
            for dest in ("wayanad", "coorg", "munnar", "alleppey", "thekkady", "ooty", "goa"):
                if dest in prompt_lower:
                    summaries = {
                        "wayanad": (
                            "Wayanad is a lush green hill district in northern Kerala, famous for "
                            "its misty forests, Neolithic Edakkal Caves, Banasura Sagar Dam, and "
                            "rich tribal heritage. It offers a perfect weekend escape for nature "
                            "lovers and budget travellers from Bangalore or Calicut."
                        ),
                        "munnar": (
                            "Munnar is a scenic hill station in Kerala renowned for its rolling "
                            "tea estates, cool climate, and the Eravikulam National Park — home "
                            "of the endangered Nilgiri Tahr. Ideal for 3–4 day highland retreats."
                        ),
                        "coorg": (
                            "Coorg (Kodagu) is Karnataka's misty coffee-growing district, "
                            "nicknamed 'Scotland of India'. It offers waterfall hikes, elephant "
                            "interactions at Dubare, and distinctive Kodava cuisine."
                        ),
                        "alleppey": (
                            "Alleppey (Alappuzha) is Kerala's backwater capital, famous for its "
                            "houseboat cruises on palm-fringed canals, coir industries, and "
                            "vibrant snake-boat races. Best experienced for 2–3 days."
                        ),
                        "thekkady": (
                            "Thekkady is home to Periyar Tiger Reserve, one of India's finest "
                            "wildlife sanctuaries. Boat rides on Periyar Lake, spice plantation "
                            "tours, and bamboo rafting make it a premier eco-tourism hub."
                        ),
                        "ooty": (
                            "Ooty (Udhagamandalam) is the 'Queen of Hill Stations' in the "
                            "Nilgiris of Tamil Nadu. The UNESCO-listed Nilgiri Mountain Railway, "
                            "Ooty Lake, and botanical gardens make it a classic getaway."
                        ),
                        "goa": (
                            "Goa is India's smallest state and its beach capital, blending "
                            "Portuguese colonial heritage with palm-shaded beaches, vibrant "
                            "nightlife, fresh seafood, and laid-back coastal charm."
                        ),
                    }
                    return summaries.get(dest, f"A wonderful destination with rich culture and nature.")

        # Travel tips
        if "tip" in prompt_lower or "advice" in prompt_lower or "safety" in prompt_lower:
            return (
                "Key travel tips:\n"
                "• Book accommodation well in advance for peak-season dates.\n"
                "• Carry cash — ATMs can be sparse near forest areas.\n"
                "• Respect wildlife guidelines in sanctuaries and forest zones.\n"
                "• Confirm all entry fees and timings with local authorities on arrival.\n"
                "• Opt for eco-friendly practices: avoid single-use plastics."
            )

        # Budget question
        if "budget" in prompt_lower or "cost" in prompt_lower or "price" in prompt_lower:
            return (
                "Budget guidance:\n"
                "• Economy (₹2,500–4,000 for 2): Budget homestays, local eateries, shared transport.\n"
                "• Comfort (₹5,000–8,000 for 2): Mid-range resorts, private cabs, guided tours.\n"
                "• Premium (₹10,000+ for 2): Luxury eco-resorts, private itineraries, fine dining.\n"
                "All amounts are estimates; confirm current rates with providers before booking."
            )

        # Itinerary question
        if "itinerary" in prompt_lower or "plan" in prompt_lower or "schedule" in prompt_lower:
            return (
                "A well-paced itinerary should:\n"
                "1. Group nearby attractions to minimise transit time.\n"
                "2. Start heavy-walking activities in the morning (cooler temperatures).\n"
                "3. Reserve afternoons for scenic spots, markets, or leisure.\n"
                "4. Build in at least 1 hour of buffer time between activities.\n"
                "5. End each day near your accommodation to avoid late-night travel."
            )

        # Greeting / help
        if any(w in prompt_lower for w in ("hello", "hi", "help", "start", "what can")):
            return (
                "Hello! I'm your Smart Travel Planner. I can help you:\n"
                "• Plan multi-day itineraries to Kerala, Karnataka, Tamil Nadu, and Goa.\n"
                "• Compare destinations and budget packages.\n"
                "• Export your itinerary as Markdown, JSON, HTML, or iCalendar (.ics).\n"
                "Tell me where you'd like to go and your budget!"
            )

        # Default
        return (
            "I'm here to help plan your perfect trip! Tell me your destination, "
            "travel dates, group size, and budget and I'll put together a personalised itinerary."
        )


# ---------------------------------------------------------------------------
# Module-level convenience singleton
# ---------------------------------------------------------------------------

_default_adapter: Optional[LLMAdapter] = None


def get_llm() -> LLMAdapter:
    """Return (and cache) the default LLMAdapter instance."""
    global _default_adapter
    if _default_adapter is None:
        _default_adapter = LLMAdapter()
    return _default_adapter

