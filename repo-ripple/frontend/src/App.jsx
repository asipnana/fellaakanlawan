import { useState } from 'react';
import ArchitectureCanvas from './ArchitectureCanvas';
import TaskInput from './TaskInput';
import GuardrailPanel from './GuardrailPanel';

// ── Layout constants ──────────────────────────────────────────────────────────
const SIDEBAR_WIDTH = 320;

const appStyle = {
  display: 'flex',
  flexDirection: 'column',
  width: '100vw',
  height: '100vh',
  overflow: 'hidden',
  background: '#0B2545',
};

const headerStyle = {
  flexShrink: 0,
  padding: '12px 20px',
  background: '#0B2545',
  borderBottom: '1px solid #3E6E96',
  display: 'flex',
  alignItems: 'center',
  gap: '12px',
};

const logoStyle = {
  color: '#F4F7FA',
  fontFamily: '"IBM Plex Mono", monospace',
  fontSize: '15px',
  fontWeight: 600,
  letterSpacing: '0.05em',
  margin: 0,
};

const taglineStyle = {
  color: '#8ECAE6',
  fontFamily: '"IBM Plex Sans", sans-serif',
  fontSize: '12px',
  margin: 0,
};

const bodyStyle = {
  flex: 1,
  display: 'flex',
  overflow: 'hidden',
};

const canvasAreaStyle = {
  flex: 1,
  overflow: 'hidden',
  position: 'relative',
};

const sidebarStyle = {
  width: `${SIDEBAR_WIDTH}px`,
  flexShrink: 0,
  display: 'flex',
  flexDirection: 'column',
  overflow: 'hidden',
  borderLeft: '1px solid #3E6E96',
};

// ── App ───────────────────────────────────────────────────────────────────────
export default function App() {
  const [selectedScenario, setSelectedScenario] = useState(null);

  // blastRadius is undefined until a scenario has been chosen (null = cleared,
  // array = active selection — even an empty one)
  const blastRadius =
    selectedScenario ? (selectedScenario.blast_radius ?? []) : undefined;

  const recommendedChecks = selectedScenario?.recommended_checks ?? [];

  return (
    <div style={appStyle}>

      {/* Header */}
      <header style={headerStyle}>
        <h1 style={logoStyle}>Repo Ripple</h1>
        <span style={taglineStyle}>Understand any codebase, change anything safely.</span>
      </header>

      {/* Body: canvas + sidebar */}
      <div style={bodyStyle}>

        {/* Living Architecture Map */}
        <div style={canvasAreaStyle}>
          <ArchitectureCanvas blastRadius={blastRadius || null} />
        </div>

        {/* Right sidebar */}
        <aside style={sidebarStyle}>

          {/* Scenario picker (top of sidebar) */}
          <TaskInput
            onScenarioSelected={setSelectedScenario}
            selectedScenario={selectedScenario}
          />

          {/* Guardrail panel — fills remaining sidebar space */}
          <GuardrailPanel
            blastRadius={blastRadius}
            recommendedChecks={recommendedChecks}
          />

        </aside>
      </div>

    </div>
  );
}
