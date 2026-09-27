import { useState, useEffect, useRef } from 'react';
import ReactFlow, {
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  BackgroundVariant,
} from 'reactflow';
import 'reactflow/dist/style.css';
import './ArchitectureCanvas.css';
import { BlastRadiusNode, applyBlastRadius } from './BlastRadiusOverlay.jsx';

/* ── Stable custom node type map (module-level avoids React Flow warning) ── */
const NODE_TYPES = { blastNode: BlastRadiusNode };

/* ── Grid layout constants ──────────────────────────────────────────────── */
const COLUMNS    = 4;
const COL_WIDTH  = 240;
const ROW_HEIGHT = 130;

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/* ── Graph → React Flow transforms ─────────────────────────────────────── */
function toFlowNodes(graphNodes) {
  return graphNodes.map((n, i) => ({
    id:       n.id,
    type:     'blastNode',
    position: {
      x: (i % COLUMNS) * COL_WIDTH,
      y: Math.floor(i / COLUMNS) * ROW_HEIGHT,
    },
    data: {
      label:  n.id,
      file:   n.file,
      type:   n.type,
      risk:   null,
      reason: null,
    },
  }));
}

function toFlowEdges(graphEdges) {
  return graphEdges.map((e) => ({
    id:     `${e.from}->${e.to}`,
    source: e.from,
    target: e.to,
    style:  { stroke: '#3E6E96', strokeWidth: 1.5 },
  }));
}

/* ── Component ──────────────────────────────────────────────────────────── */
export default function ArchitectureCanvas({ blastRadius }) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [status, setStatus]              = useState('idle');
  const baseNodesRef                     = useRef([]);

  /* Fetch graph on mount */
  useEffect(() => {
    setStatus('loading');
    fetch(`${API}/graph`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => {
        const flowNodes = toFlowNodes(data.nodes || []);
        const flowEdges = toFlowEdges(data.edges || []);
        baseNodesRef.current = flowNodes;
        setNodes(flowNodes);
        setEdges(flowEdges);
        setStatus('ready');
      })
      .catch(() => setStatus('error'));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  /* Apply / clear blast radius whenever the prop changes */
  useEffect(() => {
    if (status !== 'ready') return;
    setNodes(applyBlastRadius(baseNodesRef.current, blastRadius));
  }, [blastRadius, status]); // eslint-disable-line react-hooks/exhaustive-deps

  if (status === 'loading') {
    return <div className="canvas-message">Loading graph…</div>;
  }
  if (status === 'error') {
    return <div className="canvas-message canvas-message--error">Could not load graph.</div>;
  }

  return (
    <div className="canvas-root">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={NODE_TYPES}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.1}
        attributionPosition="bottom-left"
      >
        <Background
          variant={BackgroundVariant.Lines}
          color="#3E6E96"
          gap={32}
          size={0.5}
          style={{ opacity: 0.25 }}
        />
        <Controls
          style={{
            background: '#123A63',
            border: '1px solid #3E6E96',
            borderRadius: 4,
          }}
        />
      </ReactFlow>
    </div>
  );
}
