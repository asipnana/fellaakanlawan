import { useState } from 'react';
import { Handle, Position } from 'reactflow';

/** Neutral node style — mirrors ArchitectureCanvas baseline */
const NEUTRAL_STYLE = {
  background: '#f7f8fa',
  border: '1px solid #e5e7eb',
  borderRadius: 6,
  padding: '6px 12px',
  fontSize: 12,
  color: '#1f2328',
  transition: 'background 0.25s, border-color 0.25s',
};

const RISK_STYLE = {
  direct: {
    background: '#fde8e8',
    border: '1px solid #cf222e',
    color: '#7d0c14',
  },
  downstream: {
    background: '#fff3e0',
    border: '1px solid #e67700',
    color: '#7a3e00',
  },
};

/**
 * Custom React Flow node that shows a tooltip on hover when a reason is present.
 * `data.label`  — display text
 * `data.reason` — tooltip text (optional)
 * `data.risk`   — "direct" | "downstream" | undefined
 */
export function BlastRadiusNode({ data }) {
  const [hovered, setHovered] = useState(false);

  const riskOverride = data.risk ? RISK_STYLE[data.risk] : {};
  const nodeStyle = { ...NEUTRAL_STYLE, ...riskOverride };

  return (
    <div
      style={nodeStyle}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* React Flow connection handles */}
      <Handle type="target" position={Position.Left} style={{ opacity: 0 }} />
      <Handle type="source" position={Position.Right} style={{ opacity: 0 }} />

      <span>{data.label}</span>

      {hovered && data.reason && (
        <div style={tooltipStyle}>
          {data.reason}
        </div>
      )}
    </div>
  );
}

/**
 * Merges blast_radius entries into an existing React Flow nodes array.
 * Returns a new array — does not mutate the input.
 *
 * @param {Array} flowNodes   — current React Flow nodes
 * @param {Array|null} blastRadius — blast_radius array from /impact/analyze, or null
 * @returns {Array} updated React Flow nodes with risk data attached
 */
export function applyBlastRadius(flowNodes, blastRadius) {
  if (!blastRadius || blastRadius.length === 0) {
    // Strip any previous blast-radius data
    return flowNodes.map((n) => ({
      ...n,
      type: undefined,
      data: { label: n.data.label },
    }));
  }

  const riskMap = new Map(blastRadius.map((entry) => [entry.node_id, entry]));

  return flowNodes.map((n) => {
    const entry = riskMap.get(n.id);
    return {
      ...n,
      type: 'blastRadiusNode',
      data: {
        label: n.data.label,
        risk: entry?.risk,
        reason: entry?.reason,
      },
    };
  });
}

const tooltipStyle = {
  position: 'absolute',
  top: 'calc(100% + 6px)',
  left: '50%',
  transform: 'translateX(-50%)',
  background: '#1f2328',
  color: '#ffffff',
  padding: '4px 8px',
  borderRadius: 4,
  fontSize: 11,
  whiteSpace: 'nowrap',
  pointerEvents: 'none',
  zIndex: 10,
};
