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

const selectStyle = {
  display: 'block',
  width: '100%',
  padding: '7px 10px',
  background: '#0B2545',
  color: PANEL.text,
  fontFamily: PANEL.fontMono,
  fontSize: '12px',
  border: PANEL.border,
  borderRadius: '2px',
  outline: 'none',
  cursor: 'pointer',
  appearance: 'none',
  WebkitAppearance: 'none',
};

const sheetTitleStyle = {
  marginTop: '14px',
  color: PANEL.text,
  fontFamily: PANEL.fontSans,
  fontSize: '14px',
  fontWeight: 600,
  textAlign: 'left',
  lineHeight: 1.4,
};

const messageStyle = {
  marginTop: '10px',
  color: PANEL.muted,
  fontFamily: PANEL.fontSans,
  fontSize: '13px',
  textAlign: 'left',
  lineHeight: 1.5,
};

export default function TaskInput({ onScenarioSelected, selectedScenario }) {
  const [scenarios, setScenarios] = useState([]);
  const [fetchState, setFetchState] = useState('loading'); // 'loading' | 'ready' | 'error'

  useEffect(() => {
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
  }, []);

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
      )}

      {selectedScenario && (
        <p style={sheetTitleStyle}>{selectedScenario.task_description}</p>
      )}
    </div>
  );
}
