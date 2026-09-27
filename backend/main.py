"""
main.py — Repo Ripple backend (Person A)

FastAPI service that serves the two pre-generated analyzer artifacts
(graph.json and impact_scenarios.json) and generates test scaffolds on
demand.  All reasoning was already done offline by IBM Bob — this service
does nothing more than read files and return data.

Run:
    uvicorn backend.main:app --reload
or from the /backend directory:
    uvicorn main:app --reload
"""

import json
import re
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Paths to the pre-generated analyzer artifacts
# ---------------------------------------------------------------------------

_ANALYZER_DIR = Path(__file__).parent.parent / "analyzer"
_GRAPH_PATH = _ANALYZER_DIR / "graph.json"
_SCENARIOS_PATH = _ANALYZER_DIR / "impact_scenarios.json"

# ---------------------------------------------------------------------------
# In-memory store — loaded once at startup
# ---------------------------------------------------------------------------

_graph: dict[str, Any] = {"nodes": [], "edges": []}
_scenarios: list[dict[str, Any]] = []


def _load_artifacts() -> None:
    """Load graph.json and impact_scenarios.json into the in-memory store.

    Missing or malformed files are handled gracefully:
    - graph.json missing/broken → empty graph (service still starts)
    - impact_scenarios.json missing/empty → empty scenario list (200, not error)
    """
    global _graph, _scenarios

    # --- graph.json ---
    if _GRAPH_PATH.exists():
        try:
            _graph = json.loads(_GRAPH_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"[WARN] graph.json is not valid JSON: {exc} — using empty graph")
            _graph = {"nodes": [], "edges": []}
    else:
        print(f"[WARN] graph.json not found at {_GRAPH_PATH} — using empty graph")

    # --- impact_scenarios.json ---
    if _SCENARIOS_PATH.exists():
        try:
            raw = json.loads(_SCENARIOS_PATH.read_text(encoding="utf-8"))
            # Support both {"scenarios": [...]} wrapper and a bare list.
            if isinstance(raw, dict):
                _scenarios = raw.get("scenarios", [])
            elif isinstance(raw, list):
                _scenarios = raw
            else:
                _scenarios = []
        except json.JSONDecodeError as exc:
            print(f"[WARN] impact_scenarios.json is not valid JSON: {exc} — returning empty list")
            _scenarios = []
    else:
        print(f"[INFO] impact_scenarios.json not found at {_SCENARIOS_PATH} — returning empty scenario list")
        _scenarios = []


_load_artifacts()

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Repo Ripple API",
    description="Serves Living Architecture Map data and Bob-discovered impact scenarios.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # dev only — frontend on localhost:5173
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class BlastRadiusItem(BaseModel):
    node_id: str
    risk: str        # "direct" | "downstream"
    reason: str


class ScaffoldRequest(BaseModel):
    blast_radius: list[BlastRadiusItem]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/graph", summary="Return the full Living Architecture Map")
def get_graph() -> dict[str, Any]:
    """Returns the node/edge graph produced by the graph pass (graph.json)."""
    return _graph


@app.get(
    "/impact/scenarios",
    summary="Return the list of Bob-discovered change scenarios",
)
def get_scenarios() -> dict[str, Any]:
    """Returns the scenario list from impact_scenarios.json as-is.

    This is a plain file-serving endpoint — Bob already did the discovery
    offline.  Returns an empty list (not an error) if the discovery pass
    hasn't run yet or genuinely found nothing.
    """
    return {"scenarios": _scenarios}


def _node_id_to_function_name(node_id: str) -> str:
    """Convert a node id such as 'checkout.apply_discount' to a safe
    Python identifier 'test_checkout_apply_discount'."""
    safe = re.sub(r"[^a-zA-Z0-9_]", "_", node_id)
    return f"test_{safe}"


@app.post(
    "/impact/scaffold-tests",
    summary="Generate unit-test stubs for the supplied blast radius",
)
def scaffold_tests(body: ScaffoldRequest) -> dict[str, Any]:
    """For each node_id in the blast_radius, return a Python test stub.

    The stub is a function named ``test_<node_id>`` with a single
    ``# TODO: assert expected behavior`` body — no real assertions.

    Body shape::

        {"blast_radius": [
            {"node_id": "checkout.apply_discount", "risk": "direct",
             "reason": "function being changed"},
            ...
        ]}
    """
    if not body.blast_radius:
        raise HTTPException(
            status_code=422,
            detail="blast_radius must be a non-empty list.",
        )

    stubs: list[dict[str, str]] = []
    for entry in body.blast_radius:
        fn_name = _node_id_to_function_name(entry.node_id)
        stub_code = (
            f"def {fn_name}():\n"
            f'    """Auto-generated stub for {entry.node_id} '
            f'({entry.risk} risk).\n'
            f"    Reason: {entry.reason}\n"
            f'    """\n'
            f"    # TODO: assert expected behavior\n"
            f"    pass\n"
        )
        stubs.append({
            "node_id": entry.node_id,
            "risk": entry.risk,
            "function_name": fn_name,
            "stub": stub_code,
        })

    return {"stubs": stubs}


# ---------------------------------------------------------------------------
# Dev entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
