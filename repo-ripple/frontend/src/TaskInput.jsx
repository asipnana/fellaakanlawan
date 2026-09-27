import { useEffect, useState } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ── Blueprint palette (panel-level) ──────────────────────────────────────────
const PANEL = {
  background:    '#123A63',
  border:        '1px solid #3E6E96',
  text:          '#F4F7FA',
  muted:         '#8ECAE6',
  fontSans:      '"IBM Plex Sans", sans-serif',
  fontMono:      '"IBM Plex Mono", monospace',
};

const panelStyle = {
  width: '100%',
  padding: '20px 16px 16px',
  background: PANEL.background,
  borderBottom: PANEL.border,
  boxSizing: 'border-box',
};

const labelStyle = {
  display: 'block',
  marginBottom: '6px',
  color: PANEL.muted,
  fontFamily: PANEL.fontSans,
  fontSize: '12px',
  textAlign: 'left',
};

// SVG chevron that matches the muted palette colour, used as a custom arrow.
const CHEVRON_SVG = `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%238ECAE6'/%3E%3C/svg%3E")`;

const selectWrapStyle = {
  position: 'relative',
  width: '100%',
};

const selectStyle = {
  display: 'block',
  width: '100%',
  // left padding for text, right padding keeps text clear of the chevron arrow
  padding: '8px 32px 8px 10px',
  background: '#0B2545',
  color: PANEL.text,
  fontFamily: PANEL.fontMono,
  fontSize: '12px',
  border: PANEL.border,
  borderRadius: '2px',
  outline: 'none',
  cursor: 'pointer',
  // Remove native OS chrome so our custom arrow shows instead
  appearance: 'none',
  WebkitAppearance: 'none',
  MozAppearance: 'none',
  // Clip long text with an ellipsis rather than wrapping or overflowing
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  whiteSpace: 'nowrap',
  boxSizing: 'border-box',
  // Custom chevron arrow painted as a background image on the right side
  backgroundImage: CHEVRON_SVG,
  backgroundRepeat: 'no-repeat',
  backgroundPosition: 'right 10px center',
  backgroundSize: '10px 6px',
};

const sheetTitleStyle = {
  marginTop: '10px',
  color: PANEL.muted,
  fontFamily: PANEL.fontSans,
  fontSize: '12px',
  fontWeight: 400,
  textAlign: 'left',
  lineHeight: 1.5,
  // Allow long file paths to wrap rather than overflow the sidebar
  wordBreak: 'break-word',
  overflowWrap: 'break-word',
};

const messageStyle = {
  marginTop: '10px',
  color: PANEL.muted,
  fontFamily: PANEL.fontSans,
  fontSize: '13px',
  textAlign: 'left',
  lineHeight: 1.5,
};

// scenarioData prop: when provided, data is used directly and no fetch is made.
export default function TaskInput({ onScenarioSelected, selectedScenario, scenarioData }) {
  const [scenarios, setScenarios] = useState([]);
  const [fetchState, setFetchState] = useState('loading'); // 'loading' | 'ready' | 'error'

  useEffect(() => {
    if (scenarioData) {
      setScenarios(scenarioData.scenarios || []);
      setFetchState('ready');
      return;
    }
    const controller = new AbortController();
    fetch(`${API_BASE}/impact/scenarios`, { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        setScenarios(data.scenarios || []);
        setFetchState('ready');
      })
      .catch((err) => {
        if (err.name !== 'AbortError') setFetchState('error');
      });
    return () => controller.abort();
  }, [scenarioData]);

  function handleChange(e) {
    const id = e.target.value;
    if (!id) {
      onScenarioSelected(null);
      return;
    }
    const match = scenarios.find((s) => s.task_description === id);
    if (match) onScenarioSelected(match);
  }

  return (
    <div style={panelStyle}>
      <span style={labelStyle}>Change scenario</span>

      {fetchState === 'loading' && (
        <p style={messageStyle}>Retrieving Bob's scenarios…</p>
      )}

      {fetchState === 'error' && (
        <p style={messageStyle}>
          Could not reach the backend — is it running?
        </p>
      )}

      {fetchState === 'ready' && scenarios.length === 0 && (
        <p style={messageStyle}>
          Bob didn't find any notable change scenarios for this repo.
        </p>
      )}

      {fetchState === 'ready' && scenarios.length > 0 && (
        <div style={selectWrapStyle}>
          <select
            style={selectStyle}
            value={selectedScenario?.task_description || ''}
            onChange={handleChange}
          >
            <option value="">Select a scenario…</option>
            {scenarios.map((s) => (
              <option key={s.task_description} value={s.task_description}>
                {s.task_description}
              </option>
            ))}
          </select>
        </div>
      )}

      {selectedScenario && (
        <p style={sheetTitleStyle}>{selectedScenario.task_description}</p>
      )}
    </div>
  );
}
