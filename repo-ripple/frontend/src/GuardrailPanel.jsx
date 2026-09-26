import { useState } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * GuardrailPanel
 * Props:
 *   blastRadius        — array of { node_id, risk, reason } from /impact/analyze, or null
 *   recommendedChecks  — array of strings from the blast radius response, or null
 */
export default function GuardrailPanel({ blastRadius, recommendedChecks }) {
  const [scaffolds, setScaffolds] = useState(null);   // { [node_id]: string }
  const [scaffoldStatus, setScaffoldStatus] = useState('idle'); // 'idle' | 'loading' | 'error'

  const hasTask = blastRadius && blastRadius.length > 0;

  async function handleGenerateScaffolds() {
    setScaffoldStatus('loading');
    setScaffolds(null);
    try {
      const res = await fetch(`${API_BASE}/impact/scaffold-tests`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ blast_radius: blastRadius }),
      });
      if (!res.ok) {
        setScaffoldStatus('error');
        return;
      }
      const data = await res.json();
      setScaffolds(data);
      setScaffoldStatus('idle');
    } catch {
      setScaffoldStatus('error');
    }
  }

  if (!hasTask) {
    return (
      <aside style={panelStyle}>
        <p style={emptyStyle}>No active task. Select one above to see risk zones.</p>
      </aside>
    );
  }

  return (
    <aside style={panelStyle}>
      {/* ── Risk zones ── */}
      <section style={sectionStyle}>
        <h3 style={headingStyle}>Risk Zones</h3>
        <ul style={listStyle}>
          {blastRadius.map((entry) => (
            <li key={entry.node_id} style={riskItemStyle(entry.risk)}>
              <span style={riskBadgeStyle(entry.risk)}>{entry.risk}</span>
              <span style={nodeIdStyle}>{entry.node_id}</span>
              {entry.reason && <span style={reasonStyle}>— {entry.reason}</span>}
            </li>
          ))}
        </ul>
      </section>

      {/* ── Verification checklist ── */}
      {recommendedChecks && recommendedChecks.length > 0 && (
        <section style={sectionStyle}>
          <h3 style={headingStyle}>Verification Checklist</h3>
          <ul style={checklistStyle}>
            {recommendedChecks.map((check, i) => (
              <li key={i} style={checkItemStyle}>
                <input type="checkbox" readOnly style={{ marginRight: 8, cursor: 'default' }} />
                {check}
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* ── Test scaffold generation ── */}
      <section style={sectionStyle}>
        <button
          onClick={handleGenerateScaffolds}
          disabled={scaffoldStatus === 'loading'}
          style={scaffoldButtonStyle}
        >
          {scaffoldStatus === 'loading' ? 'Generating…' : 'Generate test scaffolds'}
        </button>
        {scaffoldStatus === 'error' && (
          <p style={errorStyle}>Failed to generate scaffolds. Is the backend running?</p>
        )}
      </section>

      {/* ── Scaffold output ── */}
      {scaffolds && (
        <section style={sectionStyle}>
          <h3 style={headingStyle}>Generated Test Stubs</h3>
          {Object.entries(scaffolds).map(([nodeId, content]) => (
            <div key={nodeId} style={scaffoldBlockStyle}>
              <p style={scaffoldNodeLabelStyle}>{nodeId}</p>
              <pre style={preStyle}><code>{content}</code></pre>
            </div>
          ))}
        </section>
      )}
    </aside>
  );
}

/* ── Styles ── */

const panelStyle = {
  width: 320,
  minWidth: 280,
  borderLeft: '1px solid #e5e7eb',
  background: '#f7f8fa',
  overflowY: 'auto',
  padding: '12px 16px',
  fontFamily: '-apple-system, "Segoe UI", system-ui, sans-serif',
  fontSize: 13,
  color: '#1f2328',
  boxSizing: 'border-box',
};

const emptyStyle = {
  color: '#57606a',
  fontSize: 13,
  marginTop: 8,
};

const sectionStyle = {
  marginBottom: 20,
};

const headingStyle = {
  fontSize: 12,
  fontWeight: 600,
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
  color: '#57606a',
  margin: '0 0 8px 0',
};

const listStyle = {
  listStyle: 'none',
  padding: 0,
  margin: 0,
  display: 'flex',
  flexDirection: 'column',
  gap: 6,
};

const riskItemStyle = () => ({
  display: 'flex',
  alignItems: 'baseline',
  gap: 6,
  flexWrap: 'wrap',
});

const riskBadgeStyle = (risk) => ({
  fontSize: 11,
  fontWeight: 600,
  padding: '1px 6px',
  borderRadius: 4,
  background: risk === 'direct' ? '#fde8e8' : '#fff3e0',
  color: risk === 'direct' ? '#7d0c14' : '#7a3e00',
  border: `1px solid ${risk === 'direct' ? '#cf222e' : '#e67700'}`,
  whiteSpace: 'nowrap',
});

const nodeIdStyle = {
  fontFamily: 'ui-monospace, "Cascadia Code", monospace',
  fontSize: 12,
  color: '#1f2328',
};

const reasonStyle = {
  color: '#57606a',
  fontSize: 12,
};

const checklistStyle = {
  listStyle: 'none',
  padding: 0,
  margin: 0,
  display: 'flex',
  flexDirection: 'column',
  gap: 6,
};

const checkItemStyle = {
  display: 'flex',
  alignItems: 'flex-start',
  lineHeight: 1.5,
};

const scaffoldButtonStyle = {
  padding: '6px 14px',
  border: 'none',
  borderRadius: 6,
  background: '#3b82d4',
  color: '#ffffff',
  fontSize: 13,
  cursor: 'pointer',
};

const errorStyle = {
  color: '#cf222e',
  fontSize: 12,
  marginTop: 6,
};

const scaffoldBlockStyle = {
  marginBottom: 12,
};

const scaffoldNodeLabelStyle = {
  fontFamily: 'ui-monospace, "Cascadia Code", monospace',
  fontSize: 12,
  color: '#3b82d4',
  margin: '0 0 4px 0',
};

const preStyle = {
  background: '#1f2328',
  color: '#e6edf3',
  borderRadius: 6,
  padding: '10px 12px',
  fontSize: 12,
  overflowX: 'auto',
  margin: 0,
  whiteSpace: 'pre',
};
