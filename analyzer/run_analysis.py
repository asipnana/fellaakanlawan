"""
analyzer/run_analysis.py
========================
AI Analysis Engine for Repo Ripple.

Drives IBM Bob (Agent mode) against the /sample-repo directory to produce
a dependency graph. Bob performs the actual AST parsing and cross-file
dependency resolution — this script orchestrates Bob and post-processes
its structured findings into graph.json.

Usage (from repo root):
    python analyzer/run_analysis.py
or with a custom repo path:
    python analyzer/run_analysis.py --repo-path ./sample-repo --output ./analyzer/graph.json
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import sys
from pathlib import Path
from typing import Any

# Maximum number of non-empty files sent to Bob in a single batch prompt.
# With BATCH_SIZE=3 and our current sample-repo (5 substantive files after
# skipping empty __init__.py files), this produces 2 batches = 2 Bob calls.
BATCH_SIZE = 3

# ---------------------------------------------------------------------------
# Bob integration
# We prefer the IBM Bob Python SDK when available (running inside Bob IDE).
# Otherwise we fall back to invoking the `bob` CLI as a subprocess.
# ---------------------------------------------------------------------------

try:
    import bob  # IBM Bob Python SDK (available inside Bob's embedded runtime)
    _BOB_SDK_AVAILABLE = True
except ImportError:
    _BOB_SDK_AVAILABLE = False


# ---------------------------------------------------------------------------
# Bob prompt templates
# ---------------------------------------------------------------------------

_PROMPT_EXTRACT_SYMBOLS_BATCH = """\
You are analyzing a batch of Python source files as part of a dependency-graph analysis.

{files_block}

For EACH file, extract its symbols and return a single JSON object whose keys are
the file paths listed above and whose values each have exactly these fields:
- "functions_defined": list of function names defined at module or class level
- "functions_called": list of objects like {{"caller": "<fn_name>", "callee": "<fn_name>"}}
  where caller is a function defined in this file and callee is any function it calls
  (exclude Python builtins like print, len, max, range, etc.)
- "imports": list of import strings exactly as written in the file
  (e.g. "from discounts.discounts import calculate as discounts_calculate, is_valid_code")
- "implicit_data_consumers": list of function names in this file that consume the
  return value of a function from another module (even without a direct import)

Return ONLY the JSON object keyed by file path — no prose, no markdown fences.
Example shape (two files):
{{
  "checkout/checkout.py": {{"functions_defined": [...], "functions_called": [...], "imports": [...], "implicit_data_consumers": [...]}},
  "discounts/discounts.py": {{"functions_defined": [...], "functions_called": [...], "imports": [...], "implicit_data_consumers": [...]}}
}}
"""

_PROMPT_RESOLVE_CROSS_FILE = """\
You are resolving cross-file relationships in a Python codebase.

Below is a JSON summary of every file in the repo:
{per_file_summary}

Return a JSON array of edge objects for relationships that are NOT already
captured by direct function calls or explicit imports. Only report a pair
as "implicit" when there is NO direct call/import path between them —
for example, shared mutable state, data flowing through a third party, or
a return value consumed indirectly. Do NOT report a pair as "implicit" if
a direct function call or import already connects them.

Each edge object must have exactly these fields:
- "from": "<module_dot_function>" — the caller/consumer (e.g. "checkout.apply_discount")
- "to":   "<module_dot_function>" — the callee/producer (e.g. "invoice.generate")
- "kind": "implicit"

Return ONLY a JSON array — no prose, no markdown fences.
"""


# ---------------------------------------------------------------------------
# Bob invocation
# ---------------------------------------------------------------------------

def _call_bob_agent(prompt: str) -> str:
    """
    Send a prompt to IBM Bob (Agent mode) and return the response as a string.
    Prefers the SDK; falls back to the `bob` CLI subprocess.
    """
    if _BOB_SDK_AVAILABLE:
        session = bob.AgentSession()
        response = session.run(prompt)
        return response.text if hasattr(response, "text") else str(response)

    # CLI fallback — run `bob run "<prompt>"` in headless mode.
    # bob.cmd is the Windows wrapper for the npm-installed bob CLI.
    import subprocess

    result = subprocess.run(
        ["bob.cmd", "run", "--format", "json", prompt],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"bob CLI exited with code {result.returncode}.\n"
            f"stderr: {result.stderr[:800]}"
        )
    # `bob run --format json` emits a JSON envelope; extract the text content.
    try:
        envelope = json.loads(result.stdout)
        # Shape: {"result": {"content": [{"type": "text", "text": "..."}]}}
        content_blocks = (
            envelope.get("result", {}).get("content", [])
            or envelope.get("content", [])
        )
        for block in content_blocks:
            if isinstance(block, dict) and block.get("type") == "text":
                return block["text"]
        # Fallback: return raw stdout if structure differs
        return result.stdout
    except (json.JSONDecodeError, AttributeError):
        return result.stdout


def _parse_bob_json(raw: str) -> Any:
    """
    Extract the first valid JSON value from Bob's raw response.
    Bob sometimes wraps output in prose or markdown fences — this strips that.
    """
    raw = raw.strip()

    # Strip markdown fences (```json ... ``` or ``` ... ```)
    if raw.startswith("```"):
        lines = raw.splitlines()
        inner = [ln for ln in lines[1:] if ln.strip() != "```"]
        raw = "\n".join(inner).strip()

    # Direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Scan for first { or [ and parse from there
    for open_ch, close_ch in [("{", "}"), ("[", "]")]:
        start = raw.find(open_ch)
        end = raw.rfind(close_ch)
        if start != -1 and end > start:
            try:
                return json.loads(raw[start: end + 1])
            except json.JSONDecodeError:
                continue

    raise ValueError(f"Could not extract valid JSON from Bob response:\n{raw[:400]}")


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _to_forward_slash(path_str: str) -> str:
    """Normalise OS path separators to forward-slash for graph.json portability."""
    return path_str.replace("\\", "/")


def _module_id_from_path(file_path: Path, repo_root: Path) -> str:
    """
    Convert a file path to the top-level module id used as node id prefix.

    Per the data contract in section 4 of the project brief (immutable):
      checkout/checkout.py   ->  checkout
      invoice/generate.py    ->  invoice
      inventory/reserve.py   ->  inventory
      discounts/discounts.py ->  discounts
      checkout/__init__.py   ->  checkout
      main.py                ->  main   (root-level file)

    Node ids are therefore 2-level: "<module>.<function>"
    e.g. checkout.apply_discount, invoice.generate
    """
    rel = file_path.relative_to(repo_root)
    # Root-level file (e.g. main.py) — use filename without extension
    if len(rel.parts) == 1:
        return rel.parts[0][:-3] if rel.parts[0].endswith(".py") else rel.parts[0]
    # Subfolder file — use top-level folder name as module id
    return rel.parts[0]


# ---------------------------------------------------------------------------
# Per-file emptiness check and batch analysis
# ---------------------------------------------------------------------------

_EMPTY_FINDINGS: dict = {
    "functions_defined": [],
    "functions_called": [],
    "imports": [],
    "implicit_data_consumers": [],
}


def _is_empty_file(file_path: Path) -> bool:
    """
    Return True if the file has zero substantive lines after stripping
    comments and blank lines.  Used to skip trivially empty files (e.g.
    bare __init__.py) without sending them to Bob.
    """
    for line in file_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return False
    return True


def analyze_batch_with_bob(
    batch: list[tuple[Path, str, str]],  # (file_path, rel_path, source)
    repo_root: Path,
) -> list[dict]:
    """
    Send a single Bob prompt for a batch of files and split the response
    back into per-file findings dicts (each enriched with module_id + file).

    batch     — list of (file_path, rel_path, source) tuples, all non-empty files.
    repo_root — root of the repo being analyzed (needed for _module_id_from_path).
    Returns one findings dict per file in the same order as `batch`.
    """
    # Build the files_block: path header + fenced source for each file
    blocks = []
    for _, rel_path, source in batch:
        blocks.append(
            f"File path: {rel_path}\n"
            f"File contents:\n```python\n{source}\n```"
        )
    files_block = "\n\n".join(blocks)

    prompt = _PROMPT_EXTRACT_SYMBOLS_BATCH.format(files_block=files_block)
    raw = _call_bob_agent(prompt)

    try:
        parsed = _parse_bob_json(raw)
    except ValueError:
        parsed = {}

    # Bob should return a dict keyed by file path; guard against malformed output
    if not isinstance(parsed, dict):
        parsed = {}

    results: list[dict] = []
    for file_path, rel_path, _ in batch:
        # Look up by the exact rel_path key we sent to Bob
        file_findings = parsed.get(rel_path)
        if not isinstance(file_findings, dict):
            file_findings = {}
        file_findings["module_id"] = _module_id_from_path(file_path, repo_root)
        file_findings["file"] = rel_path
        results.append(file_findings)
    return results


# ---------------------------------------------------------------------------
# Graph node construction
# ---------------------------------------------------------------------------

def _build_nodes(per_file_findings: list[dict]) -> list[dict]:
    """
    Emit one module node per module_id and one function node per defined function.

    Module node rules:
    - Skipped entirely if every file sharing that module_id is empty (no
      functions_defined, no functions_called, no imports).  Pure package-marker
      __init__.py files with nothing in them add no value to the graph.
    - When emitted, the "file" field points to the most substantive file for
      that module_id — the one with the most functions_defined.  This means
      e.g. "checkout" -> "checkout/checkout.py" (3 functions), not
      "checkout/__init__.py" (0 functions), even though __init__.py sorts first.

    Function node rules are unchanged: only emit functions Bob actually found.
    """
    # Pass 1 — group findings by module_id so we can pick the best representative
    # file and decide whether to emit a module node at all.
    from collections import defaultdict
    by_module: dict[str, list[dict]] = defaultdict(list)
    for f in per_file_findings:
        by_module[f["module_id"]].append(f)

    def _is_substantive(f: dict) -> bool:
        """True if Bob found any content in this file."""
        return bool(
            f.get("functions_defined")
            or f.get("functions_called")
            or f.get("imports")
        )

    def _best_file(findings: list[dict]) -> str:
        """Return the file path of the finding with the most functions_defined."""
        return max(
            findings,
            key=lambda f: len(f.get("functions_defined") or []),
        ).get("file", "")

    # Pass 2 — emit nodes in original file order so output is stable / predictable.
    nodes: list[dict] = []
    seen: set[str] = set()

    for f in per_file_findings:
        module_id = f["module_id"]
        file_path = f.get("file", "")
        fns_defined = f.get("functions_defined", [])

        # Module node — emit once per module_id, only if the module has substance
        if module_id not in seen:
            module_findings = by_module[module_id]
            if any(_is_substantive(mf) for mf in module_findings):
                representative_file = _best_file(module_findings)
                nodes.append({"id": module_id, "file": representative_file, "type": "module"})
            seen.add(module_id)  # always mark seen to avoid re-checking siblings

        # Function nodes — only emit functions Bob actually found
        for fn in fns_defined:
            if not isinstance(fn, str) or not fn.strip():
                continue
            node_id = f"{module_id}.{fn}"
            if node_id not in seen:
                nodes.append({"id": node_id, "file": file_path, "type": "function"})
                seen.add(node_id)

    return nodes


# ---------------------------------------------------------------------------
# Explicit edge construction from Bob's per-file findings
# ---------------------------------------------------------------------------

def _parse_import_strings(
    imports: list[str],
) -> tuple[list[tuple[str, str | None]], dict[str, str]]:
    """
    Parse a list of import strings into:
      - edges_info: list of (module, real_symbol_or_None) pairs for import edges
      - alias_map:  dict mapping local alias -> real symbol name, for de-aliasing
                    calls that Bob reports under the alias name

    Handles multi-symbol and aliased imports, e.g.:
      "from discounts.discounts import calculate as discounts_calculate, is_valid_code"
      edges_info -> [("discounts.discounts", "calculate"),
                     ("discounts.discounts", "is_valid_code")]
      alias_map  -> {"discounts_calculate": "calculate"}

      "from inventory.reserve import reserve as inventory_reserve"
      edges_info -> [("inventory.reserve", "reserve")]
      alias_map  -> {"inventory_reserve": "reserve"}
    """
    edges_info: list[tuple[str, str | None]] = []
    alias_map: dict[str, str] = {}

    for imp in imports:
        s = imp.strip()
        if s.startswith("from "):
            parts = s[5:].split(" import ", 1)
            if len(parts) == 2:
                module = parts[0].strip()
                for raw_sym in parts[1].split(","):
                    raw_sym = raw_sym.strip()
                    if not raw_sym:
                        continue
                    # Handle "Y as Z" — real name is Y, local alias is Z
                    if " as " in raw_sym:
                        real, alias = [t.strip() for t in raw_sym.split(" as ", 1)]
                        alias_map[alias] = real
                        edges_info.append((module, real))
                    else:
                        edges_info.append((module, raw_sym))
        elif s.startswith("import "):
            module = s[7:].strip().split()[0]
            edges_info.append((module, None))

    return edges_info, alias_map


def _build_explicit_edges(
    per_file_findings: list[dict], nodes: list[dict]
) -> list[dict]:
    """
    Build edges for:
    1. Import edges: module -> imported symbol/module
    2. Call edges: specific caller function -> specific callee function
       (uses the caller/callee pairs Bob returned, NOT a fan-out from all functions)

    Alias resolution: if Bob reports a callee by its local alias (e.g.
    "discounts_calculate" from `import calculate as discounts_calculate`),
    we de-alias it to the real symbol name before matching against node ids.
    """
    node_ids: set[str] = {n["id"] for n in nodes}
    # Map id -> type so call matching only resolves to function nodes
    node_type: dict[str, str] = {n["id"]: n["type"] for n in nodes}

    edges: list[dict] = []
    seen: set[tuple[str, str, str]] = set()

    def _add(from_id: str, to_id: str, kind: str) -> None:
        if from_id in node_ids and to_id in node_ids and from_id != to_id:
            key = (from_id, to_id, kind)
            if key not in seen:
                edges.append({"from": from_id, "to": to_id, "kind": kind})
                seen.add(key)

    for f in per_file_findings:
        module_id = f["module_id"]

        # --- Import edges (module-level) + build per-file alias map ---
        edges_info, alias_map = _parse_import_strings(f.get("imports", []))
        for mod, sym in edges_info:
            # `mod` is the literal dotted import path from source, e.g.
            # "discounts.discounts", "inventory.reserve", "invoice.generate".
            # Our node ids are 2-level using the TOP-LEVEL folder name only
            # (per _module_id_from_path), so "discounts.discounts" -> "discounts".
            # We must derive top_level_module first, then build candidate ids —
            # never use the raw `mod` string directly as a node id.
            top_level_module = mod.split(".")[0]
            if sym and f"{top_level_module}.{sym}" in node_ids:
                # Specific function node exists — prefer it
                to_id = f"{top_level_module}.{sym}"
            else:
                # Fall back to the module node
                to_id = top_level_module
            _add(module_id, to_id, "imports")

        # --- Call edges (function-level, using Bob's caller/callee pairs) ---
        for call in f.get("functions_called", []):
            if not isinstance(call, dict):
                continue
            caller_fn = call.get("caller", "")
            callee_fn = call.get("callee", "")
            if not caller_fn or not callee_fn:
                continue

            # De-alias: if Bob reported the callee by its local alias, resolve
            # to the real imported symbol name before matching node ids
            resolved_callee = alias_map.get(callee_fn, callee_fn)

            from_id = f"{module_id}.{caller_fn}"
            # Match resolved callee only to function-type nodes outside current module
            callee_candidates = [
                nid for nid in node_ids
                if nid.endswith(f".{resolved_callee}")
                and not nid.startswith(f"{module_id}.")
                and node_type.get(nid) == "function"
            ]
            for to_id in callee_candidates:
                _add(from_id, to_id, "calls")

    return edges


# ---------------------------------------------------------------------------
# Cross-file implicit edge resolution (second Bob call)
# ---------------------------------------------------------------------------

def resolve_implicit_edges_with_bob(
    per_file_findings: list[dict],
    node_ids: set[str],
    explicit_pairs: set[tuple[str, str]],
) -> list[dict]:
    """
    Ask Bob to surface implicit cross-file data-flow edges that aren't
    captured by direct imports/calls.

    explicit_pairs — set of (from_id, to_id) tuples already present in
    explicit_edges.  Any Bob-returned edge whose (from, to) pair already
    appears here is dropped regardless of the "kind" label Bob chose,
    preventing contradictory duplicate edges such as:
      {"from": "A", "to": "B", "kind": "calls"}    <- from explicit pass
      {"from": "A", "to": "B", "kind": "implicit"}  <- Bob repeating it
    """
    summary = json.dumps(
        [
            {
                "module_id": f["module_id"],
                "file": f.get("file"),
                "functions_defined": f.get("functions_defined", []),
                "functions_called": f.get("functions_called", []),
                "imports": f.get("imports", []),
                "implicit_data_consumers": f.get("implicit_data_consumers", []),
            }
            for f in per_file_findings
        ],
        indent=2,
    )
    prompt = _PROMPT_RESOLVE_CROSS_FILE.format(per_file_summary=summary)
    raw = _call_bob_agent(prompt)

    try:
        bob_edges = _parse_bob_json(raw)
    except ValueError:
        print("[warn] Bob cross-file pass returned unparseable output; skipping.", file=sys.stderr)
        return []

    if not isinstance(bob_edges, list):
        print("[warn] Bob cross-file pass did not return a list; skipping.", file=sys.stderr)
        return []

    seen: set[tuple[str, str]] = set()
    valid: list[dict] = []
    for edge in bob_edges:
        if not isinstance(edge, dict):
            continue
        from_id = edge.get("from", "")
        to_id = edge.get("to", "")
        pair = (from_id, to_id)
        if (
            from_id in node_ids
            and to_id in node_ids
            and from_id != to_id
            and pair not in explicit_pairs
            and pair not in seen
        ):
            valid.append({"from": from_id, "to": to_id, "kind": "implicit"})
            seen.add(pair)
    return valid


# ---------------------------------------------------------------------------
# Main analysis pipeline
# ---------------------------------------------------------------------------

def run_analysis(repo_path: Path, output_path: Path) -> dict:
    """
    Full pipeline:
      1. Discover all .py files under repo_path.
      2. Bob per-file: extract functions_defined, functions_called, imports.
      3. Build nodes from Bob's findings.
      4. Build explicit edges (imports + calls) from Bob's per-file data.
      5. Bob cross-file: resolve implicit data-flow edges.
      6. Merge, deduplicate, write graph.json.
    """
    python_files = sorted(repo_path.rglob("*.py"))
    if not python_files:
        raise FileNotFoundError(f"No Python files found under {repo_path}")

    # Step 1 & 2 — skip empty files, batch non-empty files, call Bob in parallel

    # Partition: empty files get synthesized findings, non-empty files go to Bob
    empty_findings: list[dict] = []
    non_empty: list[tuple[Path, str, str]] = []  # (file_path, rel_path, source)
    for py_file in python_files:
        rel = _to_forward_slash(str(py_file.relative_to(repo_path)))
        if _is_empty_file(py_file):
            print(f"      skip (empty) > {rel}")
            f = dict(_EMPTY_FINDINGS)
            f["module_id"] = _module_id_from_path(py_file, repo_path)
            f["file"] = rel
            empty_findings.append(f)
        else:
            source = py_file.read_text(encoding="utf-8")
            non_empty.append((py_file, rel, source))

    # Split non-empty files into batches of BATCH_SIZE
    batches: list[list[tuple[Path, str, str]]] = [
        non_empty[i: i + BATCH_SIZE] for i in range(0, max(len(non_empty), 1), BATCH_SIZE)
    ]
    # Guard: if non_empty is empty, batches should be empty too
    if not non_empty:
        batches = []

    print(
        f"[1/4] Found {len(python_files)} Python files "
        f"({len(non_empty)} non-empty -> {len(batches)} batch(es), "
        f"{len(python_files) - len(non_empty)} skipped as empty) "
        f"— calling IBM Bob..."
    )

    # Submit all batches in parallel (ThreadPoolExecutor, max 5 workers)
    batch_results: list[list[dict]] = [[] for _ in batches]
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_idx = {
            executor.submit(analyze_batch_with_bob, batch, repo_path): idx
            for idx, batch in enumerate(batches)
        }
        for future in concurrent.futures.as_completed(future_to_idx):
            idx = future_to_idx[future]
            batch_results[idx] = future.result()

    # Flatten batch results in original file order, then append empty-file findings
    non_empty_findings: list[dict] = [f for batch in batch_results for f in batch]

    # Restore original file order: merge empty + non-empty by their rel path
    non_empty_by_rel = {f["file"]: f for f in non_empty_findings}
    empty_by_rel = {f["file"]: f for f in empty_findings}
    per_file_findings: list[dict] = []
    for py_file in python_files:
        rel = _to_forward_slash(str(py_file.relative_to(repo_path)))
        if rel in non_empty_by_rel:
            per_file_findings.append(non_empty_by_rel[rel])
        else:
            per_file_findings.append(empty_by_rel[rel])

    # Step 3 — nodes
    print("[2/4] Building graph nodes from Bob's findings...")
    nodes = _build_nodes(per_file_findings)
    node_ids = {n["id"] for n in nodes}

    # Step 4 — explicit edges
    print("[3/4] Building explicit edges (imports + calls)...")
    explicit_edges = _build_explicit_edges(per_file_findings, nodes)
    explicit_pairs: set[tuple[str, str]] = {(e["from"], e["to"]) for e in explicit_edges}

    # Step 5 — implicit edges via second Bob call
    print("[4/4] Calling IBM Bob for cross-file implicit dependency resolution...")
    implicit_edges = resolve_implicit_edges_with_bob(
        per_file_findings, node_ids, explicit_pairs
    )

    # Step 6 — merge & deduplicate
    seen_keys: set[tuple[str, str, str]] = set()
    merged_edges: list[dict] = []
    for edge in explicit_edges + implicit_edges:
        key = (edge["from"], edge["to"], edge["kind"])
        if key not in seen_keys:
            merged_edges.append(edge)
            seen_keys.add(key)

    graph = {"nodes": nodes, "edges": merged_edges}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(graph, indent=2), encoding="utf-8")
    print(f"\ngraph.json written to {output_path}")
    return graph


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Repo Ripple - Bob Analysis Engine")
    parser.add_argument(
        "--repo-path",
        default=str(Path(__file__).parent.parent / "sample-repo"),
        help="Path to the repository to analyze (default: ../sample-repo)",
    )
    parser.add_argument(
        "--output",
        default=str(Path(__file__).parent / "graph.json"),
        help="Path to write graph.json (default: ./graph.json)",
    )
    args = parser.parse_args()

    repo_path = Path(args.repo_path).resolve()
    output_path = Path(args.output).resolve()

    if not repo_path.exists():
        print(f"Error: repo path does not exist: {repo_path}", file=sys.stderr)
        sys.exit(1)

    print("Repo Ripple - AI Analysis Engine")
    print(f"  repo   : {repo_path}")
    print(f"  output : {output_path}")
    print(f"  bob SDK: {'available' if _BOB_SDK_AVAILABLE else 'not found - using CLI subprocess'}")
    print()

    graph = run_analysis(repo_path, output_path)

    node_count = len(graph["nodes"])
    edge_count = len(graph["edges"])
    fn_nodes = sum(1 for n in graph["nodes"] if n["type"] == "function")
    mod_nodes = sum(1 for n in graph["nodes"] if n["type"] == "module")
    kind_counts = {}
    for e in graph["edges"]:
        kind_counts[e["kind"]] = kind_counts.get(e["kind"], 0) + 1

    print()
    print(f"Summary: {node_count} nodes ({mod_nodes} modules, {fn_nodes} functions), "
          f"{edge_count} edges {kind_counts}")
