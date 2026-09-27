import json
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Repo Ripple API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Artifact paths — resolved relative to this file ──────────────────────────
_HERE = Path(__file__).parent.parent  # repo-ripple/
_ANALYZER = _HERE / "analyzer"

_GRAPH_PATH     = _ANALYZER / "graph.json"
_SCENARIO_PATH  = _ANALYZER / "impact_scenarios.json"


def _load_json(path: Path) -> dict:
    if not path.exists():
        raise HTTPException(status_code=503, detail=f"Artifact not found: {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))


# ── Pydantic models ───────────────────────────────────────────────────────────

class BlastRadiusEntry(BaseModel):
    node_id: str
    risk: str
    reason: str = ""


class ScaffoldRequest(BaseModel):
    blast_radius: List[BlastRadiusEntry]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/graph")
def get_graph():
    """Return the full node/edge graph produced by the graph pass."""
    return _load_json(_GRAPH_PATH)


@app.get("/impact/scenarios")
def get_scenarios():
    """Return the Bob-discovered scenario list as-is."""
    return _load_json(_SCENARIO_PATH)


@app.post("/impact/scaffold-tests")
def scaffold_tests(body: ScaffoldRequest):
    """
    For each entry in blast_radius, generate a skeleton test stub.
    Returns a JSON array of { node_id, stub } objects.
    """
    results = []
    for entry in body.blast_radius:
        func_name = "test_" + entry.node_id.replace(".", "_")
        stub = (
            f"def {func_name}():\n"
            f"    # TODO: assert expected behavior for {entry.node_id} "
            f"({entry.risk} risk)\n"
            f"    pass"
        )
        results.append({"node_id": entry.node_id, "stub": stub})
    return results
