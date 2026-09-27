"""
test_backend.py — Repo Ripple end-to-end backend verification (Person A)

Calls all three endpoints, validates shapes, and prints a PASS/FAIL verdict.

Usage (with the backend already running):
    python test_backend.py [--base-url http://localhost:8000]

Requirements:
    pip install requests
"""

import argparse
import sys
from typing import Any

import requests

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PASS_COUNT = 0
FAIL_COUNT = 0


def _ok(label: str, detail: str = "") -> None:
    global PASS_COUNT
    PASS_COUNT += 1
    suffix = f"  ({detail})" if detail else ""
    print(f"  [PASS] {label}{suffix}")


def _fail(label: str, detail: str = "") -> None:
    global FAIL_COUNT
    FAIL_COUNT += 1
    suffix = f"  ({detail})" if detail else ""
    print(f"  [FAIL] {label}{suffix}")


def _check(cond: bool, label: str, detail: str = "") -> None:
    (_ok if cond else _fail)(label, detail)


# ---------------------------------------------------------------------------
# Test: GET /graph
# ---------------------------------------------------------------------------


def test_get_graph(base: str) -> dict[str, Any]:
    print("\n--- GET /graph ---")
    resp = requests.get(f"{base}/graph", timeout=10)
    _check(resp.status_code == 200, "Status 200", str(resp.status_code))

    data = resp.json()
    _check(isinstance(data, dict), "Response is a JSON object")
    _check("nodes" in data, 'Has "nodes" key')
    _check("edges" in data, 'Has "edges" key')
    _check(isinstance(data.get("nodes"), list), '"nodes" is a list')
    _check(isinstance(data.get("edges"), list), '"edges" is a list')

    nodes = data.get("nodes", [])
    edges = data.get("edges", [])

    if nodes:
        first = nodes[0]
        _check("id" in first, "Node has required field: id")
        _check("file" in first, "Node has required field: file")
        _check("type" in first, "Node has required field: type")
        _check(isinstance(first.get("id"), str), "Node.id is a string")
        _check(isinstance(first.get("file"), str), "Node.file is a string")
        _check(isinstance(first.get("type"), str), "Node.type is a string")
    else:
        print("  [INFO] nodes list is empty — graph pass may not have run yet")

    if edges:
        first_edge = edges[0]
        _check("from" in first_edge, "Edge has required field: from")
        _check("to" in first_edge, "Edge has required field: to")
        _check("kind" in first_edge, "Edge has required field: kind")
    else:
        print("  [INFO] edges list is empty")

    return data


# ---------------------------------------------------------------------------
# Test: GET /impact/scenarios
# ---------------------------------------------------------------------------


def test_get_scenarios(base: str) -> list[dict[str, Any]]:
    print("\n--- GET /impact/scenarios ---")
    resp = requests.get(f"{base}/impact/scenarios", timeout=10)
    _check(resp.status_code == 200, "Status 200", str(resp.status_code))

    data = resp.json()
    _check(isinstance(data, dict), "Response is a JSON object")
    _check("scenarios" in data, 'Has "scenarios" key')

    scenarios = data.get("scenarios", [])
    _check(isinstance(scenarios, list), '"scenarios" is a list')

    if not scenarios:
        print("  [INFO] Scenario list is empty — discovery pass may not have run yet")
        return []

    for i, sc in enumerate(scenarios):
        prefix = f"Scenario[{i}]"
        _check("id" in sc, f"{prefix} has 'id'")
        _check(isinstance(sc.get("id"), str) and sc.get("id"), f"{prefix} id is non-empty string")
        _check("task_description" in sc, f"{prefix} has 'task_description'")
        _check(
            isinstance(sc.get("task_description"), str) and sc.get("task_description"),
            f"{prefix} task_description is non-empty string",
        )
        _check("blast_radius" in sc, f"{prefix} has 'blast_radius'")
        _check(isinstance(sc.get("blast_radius"), list), f"{prefix} blast_radius is a list")
        _check("recommended_checks" in sc, f"{prefix} has 'recommended_checks'")
        _check(isinstance(sc.get("recommended_checks"), list), f"{prefix} recommended_checks is a list")

        for j, br in enumerate(sc.get("blast_radius", [])):
            bp = f"{prefix}.blast_radius[{j}]"
            _check("node_id" in br, f"{bp} has 'node_id'")
            _check("risk" in br and br["risk"] in ("direct", "downstream"), f"{bp} risk is 'direct' or 'downstream'")
            _check("reason" in br, f"{bp} has 'reason'")

    print(f"  [INFO] {len(scenarios)} scenario(s) returned")
    return scenarios


# ---------------------------------------------------------------------------
# Test: POST /impact/scaffold-tests
# ---------------------------------------------------------------------------


def test_scaffold_tests(base: str, scenarios: list[dict[str, Any]]) -> None:
    print("\n--- POST /impact/scaffold-tests ---")

    if not scenarios:
        print("  [SKIP] No scenarios available — skipping scaffold test")
        return

    first_scenario = scenarios[0]
    blast_radius = first_scenario.get("blast_radius", [])

    if not blast_radius:
        print("  [SKIP] First scenario has an empty blast_radius — skipping scaffold test")
        return

    payload = {"blast_radius": blast_radius}
    resp = requests.post(f"{base}/impact/scaffold-tests", json=payload, timeout=10)
    _check(resp.status_code == 200, "Status 200", str(resp.status_code))

    data = resp.json()
    _check(isinstance(data, dict), "Response is a JSON object")
    _check("stubs" in data, 'Has "stubs" key')

    stubs = data.get("stubs", [])
    _check(isinstance(stubs, list), '"stubs" is a list')
    _check(
        len(stubs) == len(blast_radius),
        f"One stub per blast_radius entry",
        f"expected {len(blast_radius)}, got {len(stubs)}",
    )

    for i, stub in enumerate(stubs):
        prefix = f"Stub[{i}]"
        _check("node_id" in stub, f"{prefix} has 'node_id'")
        _check("stub" in stub, f"{prefix} has 'stub' (code string)")
        _check(
            isinstance(stub.get("stub"), str) and "TODO" in stub["stub"],
            f"{prefix} stub code contains TODO placeholder",
        )

    # Validate the empty blast_radius case returns 422.
    print("\n  [Checking empty blast_radius returns 422]")
    empty_resp = requests.post(
        f"{base}/impact/scaffold-tests", json={"blast_radius": []}, timeout=10
    )
    _check(empty_resp.status_code == 422, "Empty blast_radius → 422", str(empty_resp.status_code))


# ---------------------------------------------------------------------------
# Manual verification checklist (printed for human review)
# ---------------------------------------------------------------------------

MANUAL_CHECKLIST = """
╔══════════════════════════════════════════════════════════════════════════╗
║            MANUAL VERIFICATION CHECKLIST — do before demo               ║
╚══════════════════════════════════════════════════════════════════════════╝

1. Start the backend:
       cd /path/to/repo-ripple
       uvicorn backend.main:app --reload --port 8000

2. Confirm /graph returns real data from the analyzer:
       curl -s http://localhost:8000/graph | python -m json.tool | head -40

3. Confirm /impact/scenarios returns real scenarios (not an empty list):
       curl -s http://localhost:8000/impact/scenarios | python -m json.tool

4. Confirm the scenarios match what Bob actually discovered (not hardcoded):
   - Open analyzer/impact_scenarios.json in an editor
   - Compare the task_description values to what you see in the browser/curl
   - They should match verbatim

5. *** KEY CHECK — prove it's not a static file ***
   - Point run_analysis.py and discover_scenarios.py at a SECOND local repo
     (different codebase) and regenerate both JSON artifacts
   - Restart the backend (to reload from disk)
   - Hit GET /impact/scenarios again
   - Confirm the scenarios are different from the first run
   This proves the dropdown is driven by Bob's live analysis, not a fixed list

6. Confirm POST /impact/scaffold-tests works with real blast_radius data:
       curl -s -X POST http://localhost:8000/impact/scaffold-tests \\
         -H "Content-Type: application/json" \\
         -d '{"blast_radius": [{"node_id": "checkout.apply_discount",
              "risk": "direct", "reason": "function being changed"}]}' \\
         | python -m json.tool

7. Confirm the frontend loads and the dropdown is populated:
       cd frontend && npm run dev
       Open http://localhost:5173 — the scenario dropdown should not be empty

8. Confirm CORS is not blocking the frontend (check browser console for errors)

9. Confirm the server handles a missing impact_scenarios.json gracefully:
       mv analyzer/impact_scenarios.json analyzer/impact_scenarios.json.bak
       # restart backend
       curl http://localhost:8000/impact/scenarios
       # expect: {"scenarios": []}  — a 200, not a 500
       mv analyzer/impact_scenarios.json.bak analyzer/impact_scenarios.json
"""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Repo Ripple backend E2E tests")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of the running backend (default: http://localhost:8000)",
    )
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    print(f"Running end-to-end backend tests against: {base}\n")

    try:
        graph_data = test_get_graph(base)
    except Exception as exc:
        print(f"\n[ERROR] Could not reach backend at {base}: {exc}")
        print("Make sure the server is running before executing this script.")
        sys.exit(1)

    scenarios = test_get_scenarios(base)
    test_scaffold_tests(base, scenarios)

    # --- verdict ---
    print(f"\n{'='*60}")
    total = PASS_COUNT + FAIL_COUNT
    if FAIL_COUNT == 0:
        print(f"  PASS  {PASS_COUNT}/{total} checks passed")
    else:
        print(f"  FAIL  {PASS_COUNT}/{total} checks passed, {FAIL_COUNT} failed")
    print(f"{'='*60}")

    print(MANUAL_CHECKLIST)

    sys.exit(0 if FAIL_COUNT == 0 else 1)


if __name__ == "__main__":
    main()
