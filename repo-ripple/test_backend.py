"""
test_backend.py — end-to-end verification for the Repo Ripple backend.

Usage:
    # Make sure the backend is running first:
    #   cd backend && uvicorn main:app --port 8000
    python test_backend.py

Prints a PASS/FAIL verdict for each check and a final PASS/FAIL summary.

Manual checklist is printed at the end (curl commands, etc.).
"""

from __future__ import annotations

import sys
import urllib.request
import urllib.error
import json

BASE_URL = "http://localhost:8000"
CANNED_TASK = "Modify how discounts are calculated"


def _request(method: str, path: str, body: dict | None = None) -> tuple[int, dict]:
    """Minimal HTTP helper using only the stdlib."""
    url = BASE_URL + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

results: list[tuple[str, bool, str]] = []  # (name, passed, detail)


def check(name: str, passed: bool, detail: str = "") -> None:
    results.append((name, passed, detail))
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))


# ── GET /graph ───────────────────────────────────────────────────────────────

print("\n── GET /graph ──────────────────────────────────────────────────────")
status, body = _request("GET", "/graph")

check("Response is HTTP 200", status == 200, f"got {status}")
check("Response has 'nodes' key", "nodes" in body)
check("Response has 'edges' key", "edges" in body)
check("'nodes' is a list", isinstance(body.get("nodes"), list))
check("'edges' is a list", isinstance(body.get("edges"), list))

if isinstance(body.get("nodes"), list) and body["nodes"]:
    first_node = body["nodes"][0]
    check(
        "Each node has 'id', 'file', 'type' keys",
        all(k in first_node for k in ("id", "file", "type")),
        f"first node keys: {list(first_node.keys())}",
    )

if isinstance(body.get("edges"), list) and body["edges"]:
    first_edge = body["edges"][0]
    check(
        "Each edge has 'from', 'to', 'kind' keys",
        all(k in first_edge for k in ("from", "to", "kind")),
        f"first edge keys: {list(first_edge.keys())}",
    )

# ── POST /impact/analyze ─────────────────────────────────────────────────────

print("\n── POST /impact/analyze ────────────────────────────────────────────")
status, body = _request("POST", "/impact/analyze", {"task_description": CANNED_TASK})

check("Response is HTTP 200", status == 200, f"got {status}")
check("Response has 'task_description'", "task_description" in body)
check("task_description echoed correctly", body.get("task_description") == CANNED_TASK)
check("Response has 'blast_radius'", "blast_radius" in body)
check("Response has 'recommended_checks'", "recommended_checks" in body)
check("'blast_radius' is a list", isinstance(body.get("blast_radius"), list))
check(
    "'blast_radius' is non-empty",
    isinstance(body.get("blast_radius"), list) and len(body["blast_radius"]) > 0,
)
check(
    "'recommended_checks' is a non-empty list",
    isinstance(body.get("recommended_checks"), list) and len(body["recommended_checks"]) > 0,
)

if isinstance(body.get("blast_radius"), list) and body["blast_radius"]:
    first = body["blast_radius"][0]
    check(
        "Each blast_radius entry has 'node_id', 'risk', 'reason'",
        all(k in first for k in ("node_id", "risk", "reason")),
        f"first entry keys: {list(first.keys())}",
    )

blast_radius = body.get("blast_radius", [])

# ── POST /impact/analyze — unknown task returns 404 ─────────────────────────

print("\n── POST /impact/analyze (unknown task → 404) ───────────────────────")
status404, body404 = _request("POST", "/impact/analyze", {"task_description": "unknown task"})
check("Unknown task returns HTTP 404", status404 == 404, f"got {status404}")

# ── POST /impact/scaffold-tests ──────────────────────────────────────────────

print("\n── POST /impact/scaffold-tests ─────────────────────────────────────")
status, body = _request("POST", "/impact/scaffold-tests", {"blast_radius": blast_radius})

check("Response is HTTP 200", status == 200, f"got {status}")
check("Response has 'stubs' key", "stubs" in body)
check("'stubs' is a dict", isinstance(body.get("stubs"), dict))

if blast_radius and isinstance(body.get("stubs"), dict):
    expected_count = len(blast_radius)
    actual_count = len(body["stubs"])
    check(
        f"One stub per affected node ({expected_count} expected)",
        actual_count == expected_count,
        f"got {actual_count}",
    )

    for entry in blast_radius:
        nid = entry["node_id"]
        stub = body["stubs"].get(nid, "")
        check(
            f"Stub for '{nid}' contains a test_ function",
            "def test_" in stub,
            "stub missing def test_*" if "def test_" not in stub else "",
        )
        check(
            f"Stub for '{nid}' contains TODO comment",
            "# TODO" in stub,
        )

# ---------------------------------------------------------------------------
# Final verdict
# ---------------------------------------------------------------------------

print("\n" + "=" * 60)
passed_count = sum(1 for _, p, _ in results if p)
total = len(results)
all_passed = passed_count == total

print(f"Result: {passed_count}/{total} checks passed")
print("FINAL VERDICT:", "PASS ✓" if all_passed else "FAIL ✗")

# ---------------------------------------------------------------------------
# Manual checklist
# ---------------------------------------------------------------------------

print("""
══════════════════════════════════════════════════════════════
Manual verification checklist (curl commands)
══════════════════════════════════════════════════════════════

1. Start the backend:
   cd repo-ripple/backend
   uvicorn main:app --reload --port 8000

2. Confirm the graph loads (should show nodes/edges from graph.json):
   curl -s http://localhost:8000/graph | python -m json.tool

3. Analyze the first canned task:
   curl -s -X POST http://localhost:8000/impact/analyze \\
     -H "Content-Type: application/json" \\
     -d '{"task_description": "Modify how discounts are calculated"}' \\
     | python -m json.tool

4. Analyze the second canned task:
   curl -s -X POST http://localhost:8000/impact/analyze \\
     -H "Content-Type: application/json" \\
     -d '{"task_description": "Change inventory reservation timeout"}' \\
     | python -m json.tool

5. Verify 404 for an unknown task:
   curl -s -o /dev/null -w "%{http_code}" -X POST \\
     http://localhost:8000/impact/analyze \\
     -H "Content-Type: application/json" \\
     -d '{"task_description": "something unknown"}'
   # Expected: 404

6. Generate test scaffolds (paste a real blast_radius from step 3):
   curl -s -X POST http://localhost:8000/impact/scaffold-tests \\
     -H "Content-Type: application/json" \\
     -d '{"blast_radius": [{"node_id": "checkout.apply_discount", "risk": "direct", "reason": "function being changed"}]}' \\
     | python -m json.tool

7. Confirm CORS headers are present (required by the React frontend):
   curl -I -X OPTIONS http://localhost:8000/graph \\
     -H "Origin: http://localhost:5173"
   # Should include: access-control-allow-origin: *
""")

sys.exit(0 if all_passed else 1)
