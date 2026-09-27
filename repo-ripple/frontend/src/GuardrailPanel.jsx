import { useState } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ── Blueprint palette ─────────────────────────────────────────────────────────
const PANEL = {
  background:  '#123A63',
  border:      '1px solid #3E6E96',
  text:        '#F4F7FA',
  muted:       '#8ECAE6',
  dimmed:      '#5A7FA0',
  codeBg:      '#0B2545',
  directColor: '#E63946',
  downColor:   '#F4A261',
  fontSans:    '"IBM Plex Sans", sans-serif',
  fontMono:    '"IBM Plex Mono", monospace',
};

// ── Styles ────────────────────────────────────────────────────────────────────
const panelStyle = {
  width: '100%',
  height: '100%',
  overflowY: 'auto',
  padding: '20px 16px 24px',
  background: PANEL.background,
  borderTop: PANEL.border,
  boxSizing: 'border-box',
  fontFamily: PANEL.fontSans,
};

const sectionHeadStyle = {
  margin: '0 0 10px',
  color: PANEL.muted,
  fontSize: '11px',
  fontFamily: PANEL.fontMono,
  letterSpacing: '0.08em',
  textTransform: 'uppercase',
};

const emptyStateStyle = {
  color: PANEL.dimmed,
  fontSize: '13px',
  lineHeight: 1.6,
  margin: 0,
};

const checklistStyle = {
  margin: '0 0 20px',
  padding: 0,
  listStyle: 'none',
};

const checkItemStyle = {
  display: 'flex',
  alignItems: 'flex-start',
  gap: '8px',
  marginBottom: '8px',
  color: PANEL.text,
  fontSize: '13px',
  lineHeight: 1.5,
};

const checkboxStyle = {
  marginTop: '2px',
  flexShrink: 0,
  accentColor: PANEL.muted,
  cursor: 'pointer',
};

const dividerStyle = {
  border: 'none',
  borderTop: '1px solid #3E6E96',
  margin: '20px 0',
  opacity: 0.5,
};

const buttonStyle = {
  display: 'inline-block',
  padding: '7px 14px',
  background: 'transparent',
  color: PANEL.muted,
  fontFamily: PANEL.fontMono,
  fontSize: '12px',
  border: PANEL.border,
  borderRadius: '2px',
  cursor: 'pointer',
  outline: 'none',
  transition: 'color 0.2s, border-color 0.2s',
};

const buttonLoadingStyle = {
  ...buttonStyle,
  color: PANEL.dimmed,
  borderColor: PANEL.dimmed,
  cursor: 'not-allowed',
};

const errorStyle = {
  marginTop: '10px',
  color: PANEL.directColor,
  fontFamily: PANEL.fontMono,
  fontSize: '12px',
};

const scaffoldBlockStyle = {
  marginTop: '16px',
  display: 'flex',
  flexDirection: 'column',
  gap: '12px',
};

const fileHeadStyle = {
  margin: '0 0 4px',
  color: PANEL.muted,
  fontFamily: PANEL.fontMono,
  fontSize: '11px',
};

const codeBlockStyle = {
  margin: 0,
  padding: '10px 12px',
  background: PANEL.codeBg,
  border: PANEL.border,
  borderRadius: '2px',
  color: PANEL.text,
  fontFamily: PANEL.fontMono,
  fontSize: '11px',
  lineHeight: 1.6,
  overflowX: 'auto',
  whiteSpace: 'pre',
  wordBreak: 'normal',
};

// ── Component ─────────────────────────────────────────────────────────────────
export default function GuardrailPanel({ blastRadius, recommendedChecks }) {
  const [scaffoldState, setScaffoldState] = useState('idle'); // 'idle' | 'loading' | 'done' | 'error'
  const [scaffoldFiles, setScaffoldFiles] = useState([]);
  const [scaffoldError, setScaffoldError] = useState('');

  const nothingSelected = blastRadius === undefined || blastRadius === null;
  const emptyBlast = !nothingSelected && (!blastRadius || blastRadius.length === 0);

  function handleGenerateScaffolds() {
    setScaffoldState('loading');
    setScaffoldFiles([]);
    setScaffoldError('');

    fetch(`${API_BASE}/impact/scaffold-tests`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ blast_radius: blastRadius }),
    })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        // Expect: { files: [{ filename, content }] }
        setScaffoldFiles(data.files || []);
        setScaffoldState('done');
      })
      .catch((err) => {
        setScaffoldError(err.message || 'Request failed');
        setScaffoldState('error');
      });
  }

  // ── Empty states ────────────────────────────────────────────────────────────
  if (nothingSelected) {
    return (
      <div style={panelStyle}>
        <p style={emptyStateStyle}>
          No scenario selected. Choose one of Bob's discovered scenarios above to see risk zones.
        </p>
      </div>
    );
  }

  if (emptyBlast) {
    return (
      <div style={panelStyle}>
        <p style={emptyStateStyle}>
          Bob didn't find anything in this repo affected by this scenario.
        </p>
      </div>
    );
  }

  // ── Active state ────────────────────────────────────────────────────────────
  return (
    <div style={panelStyle}>

      {/* Blast-radius node list */}
      <p style={sectionHeadStyle}>Affected nodes</p>
      <ul style={{ ...checklistStyle, marginBottom: '20px' }}>
        {blastRadius.map((entry) => (
          <li
            key={entry.node_id}
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: '8px',
              marginBottom: '6px',
              fontFamily: PANEL.fontMono,
              fontSize: '11px',
              lineHeight: 1.5,
            }}
          >
            <span
              style={{
                flexShrink: 0,
                color: entry.risk === 'direct' ? PANEL.directColor : PANEL.downColor,
                fontWeight: 700,
              }}
            >
              {entry.risk === 'direct' ? '●' : '◎'}
            </span>
            <span>
              <span style={{ color: entry.risk === 'direct' ? PANEL.directColor : PANEL.downColor }}>
                {entry.node_id}
              </span>
              {entry.reason && (
                <span style={{ color: PANEL.dimmed }}> — {entry.reason}</span>
              )}
            </span>
          </li>
        ))}
      </ul>
      <hr style={dividerStyle} />

      {/* Recommended checks */}
      {recommendedChecks && recommendedChecks.length > 0 && (
        <>
          <p style={sectionHeadStyle}>Verification checklist</p>
          <ul style={checklistStyle}>
            {recommendedChecks.map((check, i) => (
              <li key={i} style={checkItemStyle}>
                <input type="checkbox" style={checkboxStyle} />
                <span>{check}</span>
              </li>
            ))}
          </ul>
          <hr style={dividerStyle} />
        </>
      )}

      {/* Test scaffold section */}
      <p style={sectionHeadStyle}>Test scaffolds</p>

      {scaffoldState === 'idle' && (
        <button
          style={buttonStyle}
          onClick={handleGenerateScaffolds}
          onMouseEnter={(e) => {
            e.currentTarget.style.color = PANEL.text;
            e.currentTarget.style.borderColor = PANEL.text;
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.color = PANEL.muted;
            e.currentTarget.style.borderColor = '#3E6E96';
          }}
        >
          Generate test scaffolds
        </button>
      )}

      {scaffoldState === 'loading' && (
        <button style={buttonLoadingStyle} disabled>
          Generating…
        </button>
      )}

      {scaffoldState === 'error' && (
        <>
          <button style={buttonStyle} onClick={handleGenerateScaffolds}>
            Retry
          </button>
          <p style={errorStyle}>Error: {scaffoldError}</p>
        </>
      )}

      {scaffoldState === 'done' && scaffoldFiles.length === 0 && (
        <p style={emptyStateStyle}>No stub files returned by the backend.</p>
      )}

      {scaffoldState === 'done' && scaffoldFiles.length > 0 && (
        <div style={scaffoldBlockStyle}>
          {scaffoldFiles.map((f) => (
            <div key={f.filename}>
              <p style={fileHeadStyle}>{f.filename}</p>
              <pre style={codeBlockStyle}>{f.content}</pre>
            </div>
          ))}
        </div>
      )}

    </div>
  );
}
