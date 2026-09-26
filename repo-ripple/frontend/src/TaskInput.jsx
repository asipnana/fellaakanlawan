import { useState } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const CANNED_TASKS = [
  'Modify how discounts are calculated',
  'Change inventory reservation timeout',
];

export default function TaskInput({ onBlastRadius }) {
  const [selected, setSelected] = useState(CANNED_TASKS[0]);
  const [status, setStatus] = useState('idle'); // 'idle' | 'loading' | 'error_404' | 'error'

  async function handleSubmit(e) {
    e.preventDefault();
    setStatus('loading');

    try {
      const res = await fetch(`${API_BASE}/impact/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_description: selected }),
      });

      if (res.status === 404) {
        setStatus('error_404');
        return;
      }

      if (!res.ok) {
        setStatus('error');
        return;
      }

      const data = await res.json();
      setStatus('idle');
      onBlastRadius(data.blast_radius);
    } catch {
      setStatus('error');
    }
  }

  return (
    <form onSubmit={handleSubmit} style={formStyle}>
      <select
        value={selected}
        onChange={(e) => {
          setSelected(e.target.value);
          setStatus('idle');
        }}
        disabled={status === 'loading'}
        style={selectStyle}
      >
        {CANNED_TASKS.map((task) => (
          <option key={task} value={task}>
            {task}
          </option>
        ))}
      </select>

      <button type="submit" disabled={status === 'loading'} style={buttonStyle}>
        {status === 'loading' ? 'Analyzing…' : 'Analyze Impact'}
      </button>

      {status === 'error_404' && (
        <span style={errorStyle}>Task not recognized by backend (404).</span>
      )}
      {status === 'error' && (
        <span style={errorStyle}>Request failed. Is the backend running?</span>
      )}
    </form>
  );
}

const formStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  padding: '10px 16px',
  background: '#ffffff',
  borderBottom: '1px solid #e5e7eb',
  fontFamily: '-apple-system, "Segoe UI", system-ui, sans-serif',
  fontSize: 14,
};

const selectStyle = {
  flex: 1,
  maxWidth: 380,
  padding: '6px 10px',
  border: '1px solid #e5e7eb',
  borderRadius: 6,
  fontSize: 14,
  color: '#1f2328',
  background: '#f7f8fa',
};

const buttonStyle = {
  padding: '6px 16px',
  border: 'none',
  borderRadius: 6,
  background: '#3b82d4',
  color: '#ffffff',
  fontSize: 14,
  cursor: 'pointer',
};

const errorStyle = {
  color: '#cf222e',
  fontSize: 13,
};
