import { useEffect, useRef, useState } from 'react';
import ReactFlow, {
  Background,
  BackgroundVariant,
  Controls,
  useNodesState,
  useEdgesState,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { BlastRadiusNode, applyBlastRadius } from './BlastRadiusOverlay';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const COLUMNS = 4;
const COL_WIDTH = 260;
const ROW_HEIGHT = 140;

// Blueprint palette — neutral only; risk colors live in BlastRadiusOverlay.jsx
const COLORS = {
  nodeBorder:      '#8ECAE6',
  nodeText:        '#F4F7FA',
  nodeBackground:  'transparent',
  edgeStroke:      '#3E6E96',
  canvasBg:        '#0B2545',
};

const NODE_STYLE = {
  border: `1px solid ${COLORS.nodeBorder}`,
  borderRadius: '2px',
  background: COLORS.nodeBackground,
  color: COLORS.nodeText,
  fontFamily: '"IBM Plex Mono", monospace',
  fontSize: '11px',
  padding: '8px 12px',
  minWidth: '160px',
  textAlign: 'left',
  boxShadow: 'none',
};

// Stable reference — must be defined outside the component to avoid React Flow warnings
const NODE_TYPES = { blastRadiusNode: BlastRadiusNode };

function toFlowNodes(graphNodes) {
  return graphNodes.map((node, i) => ({
    id: node.id,
    type: 'blastRadiusNode',
    data: { label: node.id, file: node.file, nodeType: node.type },
    position: {
      x: (i % COLUMNS) * COL_WIDTH,
      y: Math.floor(i / COLUMNS) * ROW_HEIGHT,
    },
  }));
}

function toFlowEdges(graphEdges) {
  return graphEdges.map((edge) => ({
    id: `${edge.from}->${edge.to}::${edge.kind || 'default'}`,
    source: edge.from,
    target: edge.to,
    label: edge.kind || undefined,
    style: { stroke: COLORS.edgeStroke, strokeWidth: 1 },
    labelStyle: {
      fill: COLORS.edgeStroke,
      fontFamily: '"IBM Plex Sans", sans-serif',
      fontSize: '10px',
    },
    labelBgStyle: { fill: COLORS.canvasBg },
  }));
}

const containerStyle = {
  width: '100%',
  height: '100%',
  background: COLORS.canvasBg,
};

const centeredMessageStyle = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  width: '100%',
  height: '100%',
  background: COLORS.canvasBg,
  color: COLORS.nodeText,
  fontFamily: '"IBM Plex Sans", sans-serif',
  fontSize: '14px',
};

export default function ArchitectureCanvas({ blastRadius }) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [status, setStatus] = useState('loading'); // 'loading' | 'error' | 'ready'
  const baseNodesRef = useRef([]);

  // Fetch graph on mount
  useEffect(() => {
    const controller = new AbortController();
    fetch(`${API_BASE}/graph`, { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        const rfNodes = toFlowNodes(data.nodes || []);
        const rfEdges = toFlowEdges(data.edges || []);
        baseNodesRef.current = rfNodes;
        setNodes(rfNodes);
        setEdges(rfEdges);
        setStatus('ready');
      })
      .catch((err) => {
        if (err.name !== 'AbortError') setStatus('error');
      });
    return () => controller.abort();
  }, []);

  // Apply blast-radius colors whenever the prop changes.
  useEffect(() => {
    if (!baseNodesRef.current.length) return;
    setNodes(applyBlastRadius(baseNodesRef.current, blastRadius || null));
  }, [blastRadius]);

  if (status === 'loading') {
    return <div style={centeredMessageStyle}>Loading graph…</div>;
  }
  if (status === 'error') {
    return (
      <div style={centeredMessageStyle}>
        Could not load graph — is the backend running?
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={NODE_TYPES}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.1}
        proOptions={{ hideAttribution: true }}
      >
        <Background
          variant={BackgroundVariant.Lines}
          color="#3E6E96"
          gap={32}
          size={1}
          style={{ opacity: 0.25 }}
        />
        <Controls
          style={{
            background: '#123A63',
            border: '1px solid #3E6E96',
            borderRadius: '2px',
          }}
        />
      </ReactFlow>
    </div>
  );
}
