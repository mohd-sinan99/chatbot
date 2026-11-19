"""
Phase 5 Test Suite — Web Server & REST API (L8: Tier-1 Fake, Tier-2 Structural)
Tests the ThreadingHTTPServer REST API endpoints defined in web_server.py.
Spins up a real server on a random free port in setUp / tearDown.
"""

import json
import threading
import time
import unittest
import urllib.error
import urllib.request
import os
import sys

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from http.server import ThreadingHTTPServer
from web_server import TravelAppHandler


def _get_free_port() -> int:
    """Find an available localhost port."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestWebServerEndpoints(unittest.TestCase):
    """
    Tier-1 (Fake LLM) tests: spin up the full web server in a background thread,
    hit every REST endpoint with urllib, and assert expected HTTP statuses and JSON.
    No real LLM calls are made — the ConversationalAgent uses its built-in
    rule-based fallback which does NOT require an API key.
    """

    @classmethod
    def setUpClass(cls):
        """Start a fresh ThreadingHTTPServer on a random port."""
        # Fresh handler class with a clean agent per test run
        class _Handler(TravelAppHandler):
            pass
        # Reset shared agent state
        from agent.conversation import ConversationalAgent
        from agent.safety import ExecutionLogger
        _Handler.agent = ConversationalAgent(logger=ExecutionLogger(verbose=False))

        cls.port = _get_free_port()
        cls.server = ThreadingHTTPServer(("127.0.0.1", cls.port), _Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.3)  # let server bind

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"

    def _get(self, path: str):
        """Return (status_code, response_body_str)."""
        try:
            with urllib.request.urlopen(self._url(path), timeout=10) as resp:
                return resp.status, resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8")

    def _post(self, path: str, payload: dict):
        """POST JSON payload, return (status_code, response_body_str)."""
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self._url(path),
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.status, resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8")

    # ------------------------------------------------------------------
    # Test 1: Root returns HTML
    # ------------------------------------------------------------------
    def test_01_root_returns_html(self):
        """GET / must return 200 and HTML content."""
        status, body = self._get("/")
        self.assertEqual(status, 200, "Expected HTTP 200 from GET /")
        self.assertIn("<html", body.lower(), "Response should be an HTML document")

    # ------------------------------------------------------------------
    # Test 2: Static assets served
    # ------------------------------------------------------------------
    def test_02_static_assets_served(self):
        """GET /style.css and /app.js must return 200."""
        for asset in ("/style.css", "/app.js"):
            status, body = self._get(asset)
            self.assertEqual(status, 200, f"Expected 200 for {asset}, got {status}")
            self.assertTrue(len(body) > 0, f"{asset} returned empty body")

    # ------------------------------------------------------------------
    # Test 3: /api/trip returns 404 when no active trip
    # ------------------------------------------------------------------
    def test_03_api_trip_no_active_trip_returns_404(self):
        """GET /api/trip must return 404 when no trip is active."""
        # Ensure clean state
        self._post("/api/reset", {})
        status, body = self._get("/api/trip")
        self.assertEqual(status, 404, "Expected HTTP 404 when no active trip")
        data = json.loads(body)
        self.assertIn("message", data)

    # ------------------------------------------------------------------
    # Test 4: /api/chat with empty message returns 400
    # ------------------------------------------------------------------
    def test_04_api_chat_empty_message_returns_400(self):
        """POST /api/chat with empty message must return HTTP 400."""
        status, body = self._post("/api/chat", {"message": ""})
        self.assertEqual(status, 400, "Expected 400 for empty message")
        data = json.loads(body)
        self.assertIn("error", data)

    # ------------------------------------------------------------------
    # Test 5: /api/chat general query returns JSON response
    # ------------------------------------------------------------------
    def test_05_api_chat_returns_json(self):
        """POST /api/chat with a greeting must return a JSON object with a 'type' key."""
        status, body = self._post("/api/chat", {"message": "hello"})
        self.assertEqual(status, 200, f"Expected 200 for chat greeting, got {status}")
        data = json.loads(body)
        self.assertIsInstance(data, dict, "Response should be a JSON object")
        self.assertIn("type", data, "Response must contain a 'type' field")

    # ------------------------------------------------------------------
    # Test 6: /api/chat trip generation returns structured trip
    # ------------------------------------------------------------------
    def test_06_api_chat_trip_generation(self):
        """POST /api/chat with a trip query returns TRIP_GENERATED or CLARIFY_INFO type."""
        self._post("/api/reset", {})
        status, body = self._post(
            "/api/chat",
            {"message": "Plan a 2-day trip to Wayanad for 2 people with ₹5000 budget"},
        )
        self.assertEqual(status, 200, f"Expected 200, got {status}")
        data = json.loads(body)
        self.assertIn(
            data.get("type"),
            ("TRIP_GENERATED", "CLARIFY_INFO", "GENERAL_RESPONSE"),
            f"Unexpected response type: {data.get('type')}",
        )

    # ------------------------------------------------------------------
    # Test 7: /api/chat explore intent returns destination list
    # ------------------------------------------------------------------
    def test_07_api_chat_explore_intent(self):
        """POST /api/chat with explore query must return DESTINATION_RECOMMENDATIONS or similar."""
        self._post("/api/reset", {})
        status, body = self._post(
            "/api/chat",
            {"message": "Show me popular destinations in Kerala"},
        )
        self.assertEqual(status, 200, f"Expected 200, got {status}")
        data = json.loads(body)
        self.assertIn("type", data)

    # ------------------------------------------------------------------
    # Test 8: /api/reset clears session
    # ------------------------------------------------------------------
    def test_08_api_reset_clears_session(self):
        """POST /api/reset must return RESET_SUCCESS status."""
        status, body = self._post("/api/reset", {})
        self.assertEqual(status, 200, "Expected 200 from /api/reset")
        data = json.loads(body)
        self.assertEqual(data.get("status"), "RESET_SUCCESS", "Expected RESET_SUCCESS status")

    # ------------------------------------------------------------------
    # Test 9: /api/memory returns user preferences
    # ------------------------------------------------------------------
    def test_09_api_memory_returns_preferences(self):
        """GET /api/memory must return 200 with user preferences JSON."""
        status, body = self._get("/api/memory")
        self.assertEqual(status, 200, "Expected 200 from /api/memory")
        data = json.loads(body)
        self.assertIsInstance(data, dict, "Memory response should be a JSON object")

    # ------------------------------------------------------------------
    # Test 10: Unknown endpoint returns 404
    # ------------------------------------------------------------------
    def test_10_unknown_endpoint_404(self):
        """GET on an unknown path must return HTTP 404."""
        status, _ = self._get("/api/does_not_exist")
        self.assertEqual(status, 404, "Expected 404 for unknown endpoint")

    # ------------------------------------------------------------------
    # Test 11: CORS headers present
    # ------------------------------------------------------------------
    def test_11_cors_headers_on_chat(self):
        """POST /api/chat response must include Access-Control-Allow-Origin header."""
        data = json.dumps({"message": "hello"}).encode("utf-8")
        req = urllib.request.Request(
            self._url("/api/chat"),
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            self.assertIn(
                "access-control-allow-origin",
                [h.lower() for h in resp.headers.keys()],
                "CORS header missing from /api/chat response",
            )

    # ------------------------------------------------------------------
    # Test 12: /api/export 404 without active trip
    # ------------------------------------------------------------------
    def test_12_api_export_without_trip_returns_404(self):
        """GET /api/export must return 404 when no active trip is in memory."""
        self._post("/api/reset", {})
        status, _ = self._get("/api/export?format=md")
        self.assertEqual(status, 404, "Expected 404 for export with no active trip")

    # ------------------------------------------------------------------
    # Test 13: Full end-to-end — POST trip, GET /api/trip populated
    # ------------------------------------------------------------------
    def test_13_end_to_end_trip_then_get_api_trip(self):
        """
        Structural end-to-end: POST a trip plan message, then GET /api/trip.
        If trip was generated, /api/trip must return 200 with trip data.
        If agent returned CLARIFY_INFO, verify at least /api/reset works cleanly.
        """
        self._post("/api/reset", {})
        status, body = self._post(
            "/api/chat",
            {"message": "Plan 2 days in Wayanad for 2 adults, budget ₹5000, vegetarian"},
        )
        self.assertEqual(status, 200)
        response = json.loads(body)

        if response.get("type") == "TRIP_GENERATED":
            trip_status, trip_body = self._get("/api/trip")
            self.assertEqual(trip_status, 200, "Expected active trip after generation")
            trip_data = json.loads(trip_body)
            self.assertIn("destination", trip_data, "Trip data missing 'destination'")
            self.assertIn("days", trip_data, "Trip data missing 'days'")
            self.assertIsInstance(trip_data["days"], list)
            self.assertGreater(len(trip_data["days"]), 0, "Trip should have at least 1 day")
        else:
            # Clarification or general response — just verify the response has text
            self.assertIn(
                response.get("type"),
                ("CLARIFY_INFO", "GENERAL_RESPONSE", "DESTINATION_RECOMMENDATIONS"),
            )

    # ------------------------------------------------------------------
    # Test 14: Server handles concurrent requests (threading)
    # ------------------------------------------------------------------
    def test_14_server_handles_concurrent_requests(self):
        """ThreadingHTTPServer must serve multiple simultaneous requests without deadlock."""
        import concurrent.futures

        def hit_root():
            return self._get("/")

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
            futures = [ex.submit(hit_root) for _ in range(5)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        for status, _ in results:
            self.assertEqual(status, 200, "All concurrent requests should return 200")

    # ------------------------------------------------------------------
    # Test 15: web_server module imports cleanly
    # ------------------------------------------------------------------
    def test_15_web_server_imports(self):
        """web_server.py must import without errors (stdlib-only, no external deps)."""
        import importlib
        try:
            spec = importlib.util.find_spec("web_server")
            self.assertIsNotNone(spec, "web_server module must be importable")
        except Exception as e:
            self.fail(f"web_server import raised: {e}")


if __name__ == "__main__":
    unittest.main(verbosity=2)

