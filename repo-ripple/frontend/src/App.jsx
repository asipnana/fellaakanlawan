import { useState } from 'react';
import ArchitectureCanvas from './ArchitectureCanvas';
import TaskInput from './TaskInput';

export default function App() {
  const [blastRadius, setBlastRadius] = useState([
  { node_id: "checkout.apply_discount", risk: "direct", reason: "function being changed" },
  { node_id: "invoice.generate", risk: "downstream", reason: "consumes discount output" }
  ]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      <TaskInput onBlastRadius={setBlastRadius} />
      {/* ArchitectureCanvas fills remaining space; blastRadius passed for future use */}
      <div style={{ flex: 1, overflow: 'hidden' }}>
        <ArchitectureCanvas blastRadius={blastRadius} />
      </div>
    </div>
  );
}
