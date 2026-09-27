import { useState, useEffect } from 'react';
import './TaskInput.css';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * TaskInput — scenario dropdown populated from GET /impact/scenarios.
 *
 * Props:
 *   onScenarioSelected(scenario | null)  — called with the full scenario object
 *                                          on change, or null when the placeholder
 *                                          is re-selected.
 */
export default function TaskInput({ onScenarioSelected }) {
  const [scenarios, setScenarios] = useState([]);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState(null);

  useEffect(() => {
    fetch(`${API}/impact/scenarios`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => {
        setScenarios(data.scenarios || []);
        setLoading(false);
      })
      .catch(() => {
        setError('Could not load scenarios.');
        setLoading(false);
      });
  }, []);

  function handleChange(e) {
    const idx = e.target.value;
    if (idx === '') {
      onScenarioSelected(null);
    } else {
      onScenarioSelected(scenarios[Number(idx)]);
    }
  }

  // Empty state — fetch succeeded but Bob found no scenarios for this repo
  const isEmpty = !loading && !error && scenarios.length === 0;

  return (
    <div className="task-input">
      <p className="task-input__label">Scenario</p>

      {error && (
        <p className="task-input__error">{error}</p>
      )}

      {isEmpty ? (
        <p className="task-input__empty">
          Bob didn't find any notable change scenarios for this repo.
        </p>
      ) : (
        <select
          className="task-input__select"
          onChange={handleChange}
          defaultValue=""
          disabled={loading || !!error}
          aria-label="Select a scenario"
        >
          <option value="">
            {loading ? 'Loading scenarios…' : '— select a scenario —'}
          </option>
          {scenarios.map((s, i) => (
            <option key={i} value={i}>
              {s.task_description}
            </option>
          ))}
        </select>
      )}
    </div>
  );
}
