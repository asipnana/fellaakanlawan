"""
Repo Ripple — Streamlit dashboard
Understand any codebase, change anything safely.

Reads analyzer/graph.json and analyzer/impact_scenarios.json from the repo root
(the same artifacts produced by the Bob analysis passes) and presents them as an
interactive UI.  No backend server is required — everything runs in the browser
via Streamlit.
"""

import json
import textwrap
from pathlib import Path

import streamlit as st

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Repo Ripple",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Paths ─────────────────────────────────────────────────────────────────────
_HERE = Path(__file__).parent
GRAPH_PATH    = _HERE / "analyzer" / "graph.json"
SCENARIO_PATH = _HERE / "analyzer" / "impact_scenarios.json"

# ── Risk colours (match the React frontend palette) ───────────────────────────
RISK_COLOUR = {"direct": "#E63946", "downstream": "#F4A261"}
RISK_LABEL  = {"direct": "🔴 direct", "downstream": "🟠 downstream"}

# ── Data loading ──────────────────────────────────────────────────────────────
@st.cache_data
def load_graph(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


@st.cache_data
def load_scenarios(path: Path) -> dict:
    if not path.exists():
        return {"scenarios": []}
    return json.loads(path.read_text(encoding="utf-8"))


# ── Scaffold generator (mirrors GuardrailPanel.jsx logic) ────────────────────
def generate_stub(node_id: str, risk: str, reason: str) -> str:
    safe_name = node_id.replace(".", "_")
    context = f"# Risk context: {reason}" if reason else f"# Target: {node_id}"
    return textwrap.dedent(f"""\
        import pytest
        from unittest.mock import patch, MagicMock


        def test_{safe_name}():
            {context}
            # Risk level: {risk}

            # Arrange
            # TODO: set up any required fixtures or mock dependencies

            # Act
            # TODO: call the function or trigger the behavior under test

            # Assert
            # TODO: verify the expected outcome

            pytest.fail("Test not implemented yet - refer to verification checklist")
    """)


# ── DOT graph builder ─────────────────────────────────────────────────────────
def build_dot(graph: dict, highlight_ids: set[str]) -> str:
    """Return a Graphviz DOT string for the given graph, highlighting blast-radius nodes."""
    lines = [
        'digraph G {',
        '  graph [bgcolor="#0B2545" fontname="monospace" pad="0.4"]',
        '  node  [fontname="monospace" fontsize="10" fontcolor="#F4F7FA"'
        '         style="filled" shape="box" margin="0.2,0.1"]',
        '  edge  [fontname="monospace" fontsize="9"  fontcolor="#8ECAE6"'
        '         color="#3E6E96" arrowsize="0.7"]',
    ]

    for node in graph.get("nodes", []):
        nid = node["id"]
        label = f'{nid}\\n({node["file"]})'
        risk = highlight_ids.get(nid)
        if risk == "direct":
            fill, border = "#5C1A20", "#E63946"
        elif risk == "downstream":
            fill, border = "#5C3010", "#F4A261"
        else:
            fill, border = "#123A63", "#8ECAE6"
        lines.append(
            f'  "{nid}" [label="{label}" fillcolor="{fill}" color="{border}"]'
        )

    edge_labels = {"imports": "imports", "calls": "calls", "implicit": "implicit ↘"}
    for edge in graph.get("edges", []):
        style = 'style="dashed"' if edge["kind"] == "implicit" else ""
        label = edge_labels.get(edge["kind"], edge["kind"])
        lines.append(
            f'  "{edge["from"]}" -> "{edge["to"]}" [label="{label}" {style}]'
        )

    lines.append("}")
    return "\n".join(lines)


# ═════════════════════════════════════════════════════════════════════════════
# UI
# ═════════════════════════════════════════════════════════════════════════════

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <h1 style="font-family:monospace;color:#F4F7FA;margin-bottom:2px;">
        🔍 Repo Ripple
    </h1>
    <p style="color:#8ECAE6;font-size:14px;margin-top:0;">
        Understand any codebase, change anything safely.
    </p>
    """,
    unsafe_allow_html=True,
)
st.divider()

# ── Load data ─────────────────────────────────────────────────────────────────
graph     = load_graph(GRAPH_PATH)
scenarios = load_scenarios(SCENARIO_PATH)

graph_ok    = bool(graph.get("nodes"))
scenario_ok = bool(scenarios.get("scenarios"))

if not graph_ok or not scenario_ok:
    st.warning(
        "**Analyzer artifacts not found.** "
        "Run the Bob graph pass and scenario discovery pass first, then re-deploy.\n\n"
        f"Expected:\n- `{GRAPH_PATH.relative_to(_HERE)}`\n- `{SCENARIO_PATH.relative_to(_HERE)}`"
    )
    st.stop()

nodes     = graph["nodes"]
edges     = graph["edges"]
sc_list   = scenarios["scenarios"]

# ── Sidebar — scenario picker ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Change scenario")
    st.caption("Bob-discovered scenarios for this repo")

    options = ["— select a scenario —"] + [s["task_description"] for s in sc_list]
    choice  = st.selectbox("Scenario", options, label_visibility="collapsed")

    selected = None
    if choice != options[0]:
        selected = next((s for s in sc_list if s["task_description"] == choice), None)

    st.divider()
    st.markdown("#### Graph summary")
    st.metric("Nodes", len(nodes))
    st.metric("Edges", len(edges))
    st.metric("Scenarios", len(sc_list))

# ── Build highlight map ───────────────────────────────────────────────────────
highlight: dict[str, str] = {}   # node_id → risk level
if selected:
    for entry in selected.get("blast_radius", []):
        highlight[entry["node_id"]] = entry["risk"]

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_graph, tab_blast, tab_guardrail = st.tabs(
    ["🗺 Architecture Map", "💥 Blast Radius", "🛡 Guardrails & Test Scaffolds"]
)

# ─────────────────────────────────────────────────────────────────────────────
# Tab 1 — Architecture Map
# ─────────────────────────────────────────────────────────────────────────────
with tab_graph:
    st.markdown("#### Living Architecture Map")
    if not selected:
        st.info("Select a scenario in the sidebar to highlight its blast radius on the graph.")

    try:
        import graphviz  # noqa: F401 — optional dep, graceful fallback below
        dot_src = build_dot(graph, highlight)
        st.graphviz_chart(dot_src, use_container_width=True)
    except ImportError:
        st.warning(
            "`graphviz` is not available in this environment. "
            "Showing the node/edge table instead."
        )
        col_n, col_e = st.columns(2)
        with col_n:
            st.markdown("**Nodes**")
            for n in nodes:
                risk = highlight.get(n["id"])
                badge = f" {RISK_LABEL[risk]}" if risk else ""
                st.markdown(f"- `{n['id']}` *({n['type']})*{badge}")
        with col_e:
            st.markdown("**Edges**")
            for e in edges:
                st.markdown(f"- `{e['from']}` → `{e['to']}` *[{e['kind']}]*")

# ─────────────────────────────────────────────────────────────────────────────
# Tab 2 — Blast Radius
# ─────────────────────────────────────────────────────────────────────────────
with tab_blast:
    if not selected:
        st.info("Select a scenario in the sidebar to see its blast radius.")
    else:
        blast = selected.get("blast_radius", [])
        st.markdown(f"#### Blast radius — `{selected['task_description']}`")

        if not blast:
            st.success("Bob found no affected nodes for this scenario.")
        else:
            direct_nodes     = [e for e in blast if e["risk"] == "direct"]
            downstream_nodes = [e for e in blast if e["risk"] == "downstream"]

            col_d, col_ds = st.columns(2)

            with col_d:
                st.markdown(
                    f'<span style="color:{RISK_COLOUR["direct"]};font-weight:600;">'
                    f"🔴 Direct ({len(direct_nodes)})</span>",
                    unsafe_allow_html=True,
                )
                for entry in direct_nodes:
                    with st.container(border=True):
                        st.markdown(f"**`{entry['node_id']}`**")
                        st.caption(entry.get("reason", ""))

            with col_ds:
                st.markdown(
                    f'<span style="color:{RISK_COLOUR["downstream"]};font-weight:600;">'
                    f"🟠 Downstream ({len(downstream_nodes)})</span>",
                    unsafe_allow_html=True,
                )
                for entry in downstream_nodes:
                    with st.container(border=True):
                        st.markdown(f"**`{entry['node_id']}`**")
                        st.caption(entry.get("reason", ""))

# ─────────────────────────────────────────────────────────────────────────────
# Tab 3 — Guardrails & Test Scaffolds
# ─────────────────────────────────────────────────────────────────────────────
with tab_guardrail:
    if not selected:
        st.info("Select a scenario in the sidebar to see its guardrails and generate test scaffolds.")
    else:
        blast = selected.get("blast_radius", [])

        # ── Verification checklist ────────────────────────────────────────────
        checks = selected.get("recommended_checks", [])
        if checks:
            st.markdown("#### ✅ Verification checklist")
            for check in checks:
                st.checkbox(check, key=f"chk_{hash(check)}")
            st.divider()

        # ── Test scaffold generator ───────────────────────────────────────────
        st.markdown("#### 🧪 Test scaffolds")

        if not blast:
            st.info("No affected nodes — nothing to scaffold.")
        else:
            if st.button("⚡ Generate test scaffolds", type="primary"):
                st.session_state["scaffolds_generated"] = True

            if st.session_state.get("scaffolds_generated"):
                st.caption(
                    f"Generated {len(blast)} scaffold(s) — "
                    "copy each stub into your test suite and implement the TODOs."
                )
                for entry in blast:
                    stub = generate_stub(
                        entry["node_id"],
                        entry["risk"],
                        entry.get("reason", ""),
                    )
                    with st.expander(
                        f"`{entry['node_id']}` — {RISK_LABEL.get(entry['risk'], entry['risk'])}",
                        expanded=False,
                    ):
                        st.code(stub, language="python")

        # Clear scaffolds when scenario changes
        if "scaffolds_generated" in st.session_state and not st.session_state.get("scaffolds_generated"):
            del st.session_state["scaffolds_generated"]
