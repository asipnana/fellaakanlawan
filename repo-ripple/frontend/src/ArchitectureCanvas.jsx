import { useEffect, useState } from 'react';
import ReactFlow, {
  Background,
  Controls,
  useNodesState,
  useEdgesState,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { BlastRadiusNode, applyBlastRadius } from './BlastRadiusOverlay';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const COLUMNS = 4;
const COL_WIDTH = 220;
const ROW_HEIGHT = 120;

function toFlowNodes(graphNodes) {
  return graphNodes.map((node, i) => ({
    id: node.id,
    data: { label: node.id },
    position: {
      x: (i % COLUMNS) * COL_WIDTH,
      y: Math.floor(i / COLUMNS) * ROW_HEIGHT,
    },
    style: {
      background: '#f7f8fa',
      border: '1px solid #e5e7eb',
      borderRadius: 6,
      padding: '6px 12px',
      fontSize: 12,
      color: '#1f2328',
    },
  }));
}

function toFlowEdges(graphEdges) {
  return graphEdges.map((edge) => ({
    id: `${edge.from}->${edge.to}`,
    source: edge.from,
    target: edge.to,
    style: { stroke: '#57606a' },
  }));
}

/** Stable reference — prevents React Flow from re-registering on every render */
const NODE_TYPES = { blastRadiusNode: BlastRadiusNode };

export default function ArchitectureCanvas({ blastRadius }) {
  const [baseNodes, setBaseNodes] = useState([]);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [status, setStatus] = useState('loading'); // 'loading' | 'error' | 'ok'

  // Re-apply blast radius whenever it changes (including clearing to null)
  useEffect(() => {
    if (status !== 'ok') return;
    setNodes(applyBlastRadius(baseNodes, blastRadius));
  }, [blastRadius, baseNodes, status]);

  useEffect(() => {
    fetch(`${API_BASE}/graph`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        const flowNodes = toFlowNodes(data.nodes ?? []);
        setBaseNodes(flowNodes);
        setNodes(flowNodes);
        setEdges(toFlowEdges(data.edges ?? []));
        setStatus('ok');
      })
      .catch(() => setStatus('error'));
  }, []);

  if (status === 'loading') {
    return (
      <div style={overlayStyle}>
        <span style={{ color: '#57606a' }}>Loading graph…</span>
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div style={overlayStyle}>
        <span style={{ color: '#cf222e' }}>Failed to load graph from backend.</span>
      </div>
    );
  }

  return (
    <div style={{ width: '100%', height: '100%' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={NODE_TYPES}
        fitView
      >
        <Background color="#e5e7eb" gap={20} />
        <Controls />
      </ReactFlow>
    </div>
  );
}

const overlayStyle = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  width: '100vw',
  height: '100vh',
  fontFamily: '-apple-system, "Segoe UI", system-ui, sans-serif',
  fontSize: 15,
};
