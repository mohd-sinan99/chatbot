# Smart Travel Planner AI Agent

An AI travel planning assistant built around core agentic design patterns and evaluated against PRD requirements and lessons **L1 – L8**.

---

## 🌟 Key Features & Curriculum Alignment

1. **A loop: think → act → look (📘 L1, L3)**
   - Implemented in [`agent/core_loop.py`](agent/core_loop.py) with [`agent/react_parser.py`](agent/react_parser.py).
   - At each step, the agent analyzes its current plan step (`Think`), selects and invokes an appropriate tool (`Act`), and inspects the output to record facts (`Look`).
2. **2–4 tools, clearly described (📘 L2)**
   - Implemented in [`agent/tools/`](agent/tools/).
   - 4 focused tools with strict parameter schemas:
     1. `search_destination_and_attractions`: Verified highlights, timings, entry fees, authentic local eateries, and accommodation options.
     2. `calculate_budget_breakdown`: Itemized math for stay, food, commute, activities, and contingency.
     3. `find_transport_options`: Bus, train, cab routes, fare brackets, and booking portals.
     4. `get_travel_advisory_and_weather`: Live real-time weather forecasts (Open-Meteo), packing lists, night travel bans, and forest permits.
3. **Fixing errors when a tool fails (📘 L2)**
   - Resilient execution wrapper in [`agent/tools/base.py`](agent/tools/base.py).
   - Traps exceptions, feeds structured diagnostics back to the agent loop, and enables automatic self-correction without crashing.
4. **Memory between tasks (📘 L4)**
   - Implemented in [`agent/memory.py`](agent/memory.py).
   - Persists user preferences (home city, budget style, diet), past destinations, and active trip drafts to [`data/memory.json`](data/memory.json).
5. **A plan before it acts (📘 L5)**
   - Implemented in [`agent/planner.py`](agent/planner.py).
   - `PlannerEngine` constructs a linear checklist before triggering tools, tracking progress from `PENDING` $\to$ `IN_PROGRESS` $\to$ `COMPLETED`.
6. **Safety: asks you first, step limit, log (📘 L7)**
   - Implemented in [`agent/safety.py`](agent/safety.py).
   - **Asks you first:** Human-in-the-loop approval if an estimated trip cost exceeds the user's budget.
   - **Step limit:** Hard ceiling (`max_steps = 10`) preventing infinite loops.
   - **Structured log:** Audit trail recording `[THOUGHT]`, `[ACTION]`, and `[LOOK]` at every step.
7. **Live Weather & Operational Constraints (Phase 3 & PRD 6.2, 6.7)**
   - Implemented in [`agent/tools/weather_service.py`](agent/tools/weather_service.py) (Open-Meteo live API) and [`agent/constraints.py`](agent/constraints.py) (day-of-week closure detection, e.g. Edakkal Caves closed on Mondays, with automatic day re-sequencing).
8. **Geographic Pacing, Budget Optimizer & Multi-Format Exporters (Phase 4 & PRD 6.2, 6.3, 12)**
   - **Geographic Clustering & Pacing Engine:** [`agent/pacing.py`](agent/pacing.py) eliminates criss-crossing and embeds authentic dining/lunch stops with dietary filtering (e.g. pure vegetarian messes).
   - **Budget Optimizer:** [`agent/budget_optimizer.py`](agent/budget_optimizer.py) generates 3 comparative packages (`Eco-Saver`, `Comfort`, `Deluxe`), calculates exact overrun deltas, and suggests trade-offs.
   - **Multi-Format Exporters:** [`agent/exporter.py`](agent/exporter.py) exports clean Markdown (`.md`), shareable JSON (`.json`), and print-ready styled HTML (`.html`) to the `exports/` folder.
9. **Tests: fake LLM first, then a real one (📘 L8)**
   - **Tier 1 (Fake LLM — Unit Tests):** 34 deterministic tests across [`tests/test_fake_llm.py`](tests/test_fake_llm.py), [`tests/test_memory.py`](tests/test_memory.py), [`tests/test_phase2.py`](tests/test_phase2.py), [`tests/test_phase3.py`](tests/test_phase3.py), and [`tests/test_phase4.py`](tests/test_phase4.py).
   - **Tier 1 (Web API Tests):** 15 endpoint tests in [`tests/test_phase5.py`](tests/test_phase5.py) — spins up a live server on a random port and validates all REST endpoints, CORS headers, and concurrent request handling.
   - **Tier 2 (Real LLM):** Integration test in [`tests/test_real_llm.py`](tests/test_real_llm.py) (gracefully skipped when `GEMINI_API_KEY` is absent).
   - **Total: 49 tests — `Ran 49 tests in 12.7s — OK (skipped=1)`**
10. **Web Dashboard & REST API (Phase 5 & PRD Section 12)**
    - Full interactive dual-pane UI in [`web/`](web/) (chat left + trip dashboard right).
    - Served by [`web_server.py`](web_server.py) using Python stdlib `ThreadingHTTPServer` — zero external dependencies.
    - REST endpoints: `GET /api/trip`, `GET /api/memory`, `GET /api/export?format=html|md|json`, `POST /api/chat`, `POST /api/reset`.

---

## 🚀 Quick Start

### 1. Run the Streamlit Web Application (Interactive UI)
```powershell
python -m streamlit run app.py
# Access UI at: http://localhost:8501
```

### 2. Run the Full Test Suite (54 Tests)
```powershell
python -m unittest discover -s tests -p "test_*.py" -v
# Expected: Ran 54 tests in ~9s — OK (skipped=1)
```

### 3. Run with Docker / Docker Compose (Phase 7)
```powershell
# Build and run the web app in Docker
docker compose up --build
# Then open: http://127.0.0.1:8000
```

### 4. Launch the Native Python Web Dashboard (Phase 5)
```powershell
python main.py --web --port 8000
# Then open: http://127.0.0.1:8000
```

### 5. Run the Interactive CLI / Benchmark Demo
```powershell
# Run the PRD benchmark demo (2-day Wayanad trip under ₹5,000)
python main.py --demo

# Run with a custom travel query
python main.py --query "Plan a 3-day weekend trip to Coorg for 2 people"

# Explore destination ideas
python main.py --query "Suggest weekend getaway ideas from Bangalore"

# Interactive session (supports chat, 'compare budget', 'export', and revisions)
python main.py
```
