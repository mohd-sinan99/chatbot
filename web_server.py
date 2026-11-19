"""
Web Application Server & REST API (PRD Section 12 & Phase 5)
Provides real-time web dashboard and API endpoints using Python standard library (zero external dependencies).
Serves dual-pane interactive UI: Chat Pane (Left) + Live Itinerary & Budget Dashboard (Right).
"""

import os
import json
import urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any

from agent.memory import TripMemoryStore
from agent.conversation import ConversationalAgent
from agent.exporter import ItineraryExporter
from agent.safety import ExecutionLogger

STATIC_DIR = os.path.join(os.path.dirname(__file__), "web")
EXPORTS_DIR = os.path.join(os.path.dirname(__file__), "exports")


class TravelAppHandler(BaseHTTPRequestHandler):
    """HTTP request handler for REST API and static UI assets."""

    # Shared agent instance across requests
    agent = ConversationalAgent(logger=ExecutionLogger(verbose=True))

    def _send_json(self, data: Any, status: int = 200) -> None:
        """Send a JSON HTTP response."""
        resp_bytes = json.dumps(data, default=lambda o: o.to_dict() if hasattr(o, "to_dict") else str(o)).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(resp_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(resp_bytes)

    def _serve_file(self, filepath: str, content_type: str) -> None:
        """Serve a static file from disk."""
        if not os.path.exists(filepath):
            self.send_error(404, "File not found")
            return
        with open(filepath, "rb") as f:
            content = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_OPTIONS(self):
        """Handle CORS pre-flight."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # 1. Static UI routes
        if path in ("/", "/index.html"):
            self._serve_file(os.path.join(STATIC_DIR, "index.html"), "text/html; charset=utf-8")
        elif path == "/style.css":
            self._serve_file(os.path.join(STATIC_DIR, "style.css"), "text/css; charset=utf-8")
        elif path == "/app.js":
            self._serve_file(os.path.join(STATIC_DIR, "app.js"), "application/javascript; charset=utf-8")

        # 2. REST API: Get active trip
        elif path == "/api/trip":
            active = self.agent.memory.get_active_trip()
            if active:
                self._send_json(active.to_dict())
            else:
                self._send_json({"message": "No active trip found."}, status=404)

        # 3. REST API: Get memory / profile
        elif path == "/api/memory":
            prefs = self.agent.memory.get_user_preferences("default_user")
            self._send_json(prefs.to_dict())

        # 4. REST API: Export files download
        elif path == "/api/export":
            active = self.agent.memory.get_active_trip()
            if not active:
                self.send_error(404, "No active trip to export")
                return
            export_files = ItineraryExporter.export_all(active, output_dir=EXPORTS_DIR)
            fmt = query.get("format", ["html"])[0].lower()

            if fmt == "html":
                self._serve_file(export_files["html"], "text/html; charset=utf-8")
            elif fmt in ("md", "markdown"):
                self._serve_file(export_files["markdown"], "text/markdown; charset=utf-8")
            elif fmt == "json":
                self._serve_file(export_files["json"], "application/json; charset=utf-8")
            else:
                self._send_json(export_files)

        else:
            self.send_error(404, "Endpoint not found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)

        # 1. REST API: Chat Turn
        if path == "/api/chat":
            try:
                body = json.loads(post_data.decode("utf-8")) if post_data else {}
                message = body.get("message", "").strip()
                if not message:
                    self._send_json({"error": "Empty message"}, status=400)
                    return

                response = self.agent.process_message(message, user_id="default_user")
                self._send_json(response)
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)

        # 2. REST API: Reset Session
        elif path == "/api/reset":
            self.agent.memory.set_active_trip_id(None)
            self.agent.pending_params = {}
            self.agent.awaiting_clarification_field = None
            self._send_json({"status": "RESET_SUCCESS"})

        else:
            self.send_error(404, "Endpoint not found")


def start_server(port: int = 8000) -> None:
    """Start the web application server on localhost."""
    server_address = ("127.0.0.1", port)
    httpd = ThreadingHTTPServer(server_address, TravelAppHandler)
    print(f"\n=======================================================")
    print(f"  🌍 SMART TRAVEL PLANNER - WEB APPLICATION RUNNING")
    print(f"  Access UI at: http://127.0.0.1:{port}")
    print(f"=======================================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server. Goodbye!")
        httpd.server_close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Smart Travel Planner Web Server")
    parser.add_argument("--port", type=int, default=8000, help="Port to run on (default 8000)")
    args = parser.parse_args()
    start_server(port=args.port)
