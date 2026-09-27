import './BlastRadiusOverlay.css';
import { Handle, Position } from 'reactflow';

// ── Risk color constants — the ONLY warm colors in the entire frontend ────────
const RISK = {
  direct:     { border: '#E63946', background: 'rgba(230, 57, 70, 0.18)' },
  downstream: { border: '#F4A261', background: 'rgba(244, 162, 97, 0.18)' },
};

// Neutral node style — must stay in sync with ArchitectureCanvas.jsx NODE_STYLE
const NEUTRAL = {
  border:     '1px solid #8ECAE6',
  background: 'transparent',
  color:      '#F4F7FA',
};

// ── BlastRadiusNode ────────────────────────────────────────────────────────────
// Custom React Flow node used when blast-radius coloring is active.
// data shape: { label, file?, nodeType?, risk?: 'direct'|'downstream', reason?: string }
export function BlastRadiusNode({ data }) {
  const riskColors = RISK[data.risk] || null;

  const nodeStyle = {
    position: 'relative',
    border: riskColors ? `1px solid ${riskColors.border}` : NEUTRAL.border,
    borderRadius: '2px',
    background: riskColors ? riskColors.background : NEUTRAL.background,
    color: NEUTRAL.color,
    fontFamily: '"IBM Plex Mono", monospace',
    fontSize: '11px',
    padding: '8px 12px',
    minWidth: '160px',
    textAlign: 'left',
    boxShadow: 'none',
    // Single allowed animation: soft color transition when risk status changes
    transition: 'background 0.35s ease, border-color 0.35s ease',
  };

  const tooltipStyle = {
    display: 'none',           // shown via CSS :hover on the wrapper
    position: 'absolute',
    bottom: 'calc(100% + 6px)',
    left: '0',
    zIndex: 10,
    minWidth: '180px',
    maxWidth: '260px',
    padding: '8px 10px',
    background: '#123A63',
    border: '1px solid #8ECAE6',
    borderRadius: '2px',
    color: '#F4F7FA',
    fontFamily: '"IBM Plex Sans", sans-serif',
    fontSize: '11px',
    lineHeight: 1.5,
    pointerEvents: 'none',
    whiteSpace: 'normal',
    boxShadow: 'none',
  };

  return (
    // The outer wrapper gets the :hover class that reveals the tooltip via inline
    // style. Because React inline styles can't express :hover, we use a small
    // CSS class injected once into the document head (see below).
    <div className="brn-wrapper" style={nodeStyle}>
      <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />

      {data.label}

      {data.reason && (
        <div className="brn-tooltip" style={tooltipStyle}>
          {data.reason}
        </div>
      )}

      <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
    </div>
  );
}

// ── applyBlastRadius ──────────────────────────────────────────────────────────
// Pure function: merges blast-radius risk data onto a React Flow nodes array.
// Returns a new array — does not mutate the input.
//
// @param {import('reactflow').Node[]} rfNodes  — current nodes from useNodesState
// @param {Array<{node_id, risk, reason}>|null} blastRadius — from the scenario
// @returns {import('reactflow').Node[]}
export function applyBlastRadius(rfNodes, blastRadius) {
  if (!blastRadius || blastRadius.length === 0) {
    // Reset every node to neutral — clear risk and reason
    return rfNodes.map((n) => ({
      ...n,
      type: 'blastRadiusNode',
      data: { ...n.data, risk: undefined, reason: undefined },
    }));
  }

  const lookup = new Map(blastRadius.map((entry) => [entry.node_id, entry]));

  return rfNodes.map((n) => {
    const entry = lookup.get(n.id);
    return {
      ...n,
      type: 'blastRadiusNode',
      data: {
        ...n.data,
        risk:   entry?.risk   ?? undefined,
        reason: entry?.reason ?? undefined,
      },
    };
  });
}
