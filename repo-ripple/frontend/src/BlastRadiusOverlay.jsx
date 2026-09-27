import { Handle, Position } from 'reactflow';
import './BlastRadiusOverlay.css';

/* ── Risk style maps ────────────────────────────────────────────────────── */
const STYLE_NEUTRAL = {
  background: '#123A63',
  border: '1px solid #3E6E96',
  color: '#F4F7FA',
};

const STYLE_DIRECT = {
  background: '#1a0a0b',
  border: '1px solid #E63946',
  color: '#F4F7FA',
  boxShadow: '0 0 8px #E63946',
};

const STYLE_DOWNSTREAM = {
  background: '#1a1005',
  border: '1px solid #F4A261',
  color: '#F4F7FA',
  boxShadow: '0 0 8px #F4A261',
};

function riskStyle(risk) {
  if (risk === 'direct')     return STYLE_DIRECT;
  if (risk === 'downstream') return STYLE_DOWNSTREAM;
  return STYLE_NEUTRAL;
}

/**
 * BlastRadiusNode — custom React Flow node.
 *
 * data shape:
 *   label  string   node id
 *   file   string   source file path
 *   risk   'direct' | 'downstream' | null
 *   reason string | null   shown as tooltip on hover when risk is set
 */
export function BlastRadiusNode({ data }) {
  const style = riskStyle(data.risk);
  const riskClass = data.risk ? `blast-node blast-node--${data.risk}` : 'blast-node';

  return (
    <div className={riskClass} style={style}>
      {/* Invisible handles so React Flow can route edges */}
      <Handle type="target" position={Position.Top}    style={{ opacity: 0 }} />
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />

      <span className="blast-node__label">{data.label}</span>
      {data.file && (
        <span className="blast-node__file">{data.file}</span>
      )}

      {/* Tooltip: only rendered when risk is set */}
      {data.reason && (
        <div className="blast-node__tooltip">{data.reason}</div>
      )}
    </div>
  );
}

/**
 * applyBlastRadius — pure function.
 *
 * Merges blast radius data into a React Flow nodes array.
 * Returns a NEW array — does not mutate baseNodes.
 *
 * @param {object[]} baseNodes   Original node array (neutral, from fetch).
 * @param {object[]|null} blastRadius  blast_radius entries [{node_id, risk, reason}]
 * @returns {object[]}
 */
export function applyBlastRadius(baseNodes, blastRadius) {
  if (!baseNodes || baseNodes.length === 0) return baseNodes;

  // Build a lookup map from node_id → {risk, reason}
  const lookup = new Map();
  if (blastRadius && blastRadius.length > 0) {
    for (const entry of blastRadius) {
      lookup.set(entry.node_id, { risk: entry.risk, reason: entry.reason });
    }
  }

  return baseNodes.map((node) => {
    const hit = lookup.get(node.id);
    return {
      ...node,
      data: {
        ...node.data,
        risk:   hit ? hit.risk   : null,
        reason: hit ? hit.reason : null,
      },
    };
  });
}
