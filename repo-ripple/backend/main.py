"""
main.py — Repo Ripple backend service.

Endpoints:
    GET  /graph                  → full node/edge graph (from graph.json)
    POST /impact/analyze         → blast radius for a canned task description
    POST /impact/scaffold-tests  → test stub file contents for a blast radius

Run with:
    uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="Repo Ripple API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev-only; tighten for production
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory graph store — loaded once at startup from graph.json
# ---------------------------------------------------------------------------

GRAPH_JSON_PATH = Path(__file__).parent.parent / "analyzer" / "graph.json"

_graph: dict[str, Any] = {"nodes": [], "edges": []}


def _load_graph() -> None:
    """Read graph.json into memory.  Called once on startup."""
    global _graph
    if not GRAPH_JSON_PATH.exists():
        # Graceful degradation: serve an empty graph so the frontend doesn't
        # crash before Person B's graph.json is ready.
        return
    with GRAPH_JSON_PATH.open("r", encoding="utf-8") as fh:
        _graph = json.load(fh)


_load_graph()

# ---------------------------------------------------------------------------
# Canned blast-radius scenarios (section 5 of the project brief — immutable)
# ---------------------------------------------------------------------------

_BLAST_RADIUS_MAP: dict[str, dict[str, Any]] = {
    "Modify how discounts are calculated": {
        "blast_radius": [
            {
                "node_id": "checkout.apply_discount",
                "risk": "direct",
                "reason": "function being changed",
            },
            {
                "node_id": "discounts.calculate",
                "risk": "direct",
                "reason": "core discount calculation logic",
            },
            {
                "node_id": "invoice.generate",
                "risk": "downstream",
                "reason": "consumes discount output",
            },
            {
                "node_id": "checkout.finalize_order",
                "risk": "downstream",
                "reason": "checkout totals depend on discounted amount",
            },
        ],
        "recommended_checks": [
            "Re-run invoice generation tests after changing discount logic",
            "Confirm checkout totals still match invoice totals for edge-case discounts",
        ],
    },
    "Change inventory reservation timeout": {
        "blast_radius": [
            {
                "node_id": "inventory.set_reservation_timeout",
                "risk": "direct",
                "reason": "timeout configuration being changed",
            },
            {
                "node_id": "inventory.reserve",
                "risk": "direct",
                "reason": "reservation logic reads the timeout constant",
            },
            {
                "node_id": "checkout.finalize_order",
                "risk": "downstream",
                "reason": "checkout calls inventory.reserve; timeout affects order completion window",
            },
            {
                "node_id": "checkout.apply_discount",
                "risk": "downstream",
                "reason": "order confirmation flow may expire before discount is applied",
            },
        ],
        "recommended_checks": [
            "Verify that existing in-flight reservations are not invalidated by the new timeout",
            "Confirm order-confirmation emails still fire within the new timeout window",
            "Re-run checkout integration tests with both short and long timeout values",
        ],
    },
}

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class AnalyzeRequest(BaseModel):
    task_description: str


class ScaffoldRequest(BaseModel):
    blast_radius: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/graph")
def get_graph() -> dict[str, Any]:
    """Return the full node/edge graph loaded from graph.json."""
    return _graph


@app.post("/impact/analyze")
def analyze_impact(body: AnalyzeRequest) -> dict[str, Any]:
    """Map a canned task description to its blast radius.

    Returns 404 if the task_description doesn't match a known scenario.
    """
    result = _BLAST_RADIUS_MAP.get(body.task_description)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Task description '{body.task_description}' is not a recognised "
                "demo scenario.  Supported tasks: "
                + ", ".join(f'"{t}"' for t in _BLAST_RADIUS_MAP)
            ),
        )
    return {
        "task_description": body.task_description,
        **result,
    }


@app.post("/impact/scaffold-tests")
def scaffold_tests(body: ScaffoldRequest) -> dict[str, Any]:
    """Generate skeleton unit-test stubs for each node in the blast radius.

    Returns a dict mapping each node_id to its test stub file contents.
    No real assertions are generated — scaffolds only.
    """
    stubs: dict[str, str] = {}

    for entry in body.blast_radius:
        node_id: str = entry.get("node_id", "unknown")
        # Normalise node_id to a valid Python identifier for the function name
        safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", node_id)
        stub = (
            f'"""Auto-generated test scaffold for {node_id}."""\n'
            f"\n"
            f"\n"
            f"def test_{safe_name}():\n"
            f"    # TODO: assert expected behavior\n"
            f"    pass\n"
        )
        stubs[node_id] = stub

    return {"stubs": stubs}
