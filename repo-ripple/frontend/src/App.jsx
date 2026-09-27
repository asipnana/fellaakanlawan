import { useState } from 'react';
import ArchitectureCanvas from './ArchitectureCanvas.jsx';
import TaskInput from './TaskInput.jsx';
import './App.css';

// GuardrailPanel is Person D's component — imported here once it exists.
// import GuardrailPanel from './GuardrailPanel.jsx';

export default function App() {
  // selectedScenario shape: { task_description, blast_radius, recommended_checks } | null
  const [selectedScenario, setSelectedScenario] = useState(null);

  return (
    <div className="app-shell">
      <div className="app-canvas">
        <ArchitectureCanvas
          blastRadius={selectedScenario?.blast_radius ?? null}
        />
      </div>
      <div className="app-panel">
        <TaskInput onScenarioSelected={setSelectedScenario} />
        {/* <GuardrailPanel scenario={selectedScenario} /> */}
      </div>
    </div>
  );
}
