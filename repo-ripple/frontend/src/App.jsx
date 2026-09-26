import { useState } from 'react';
import ArchitectureCanvas from './ArchitectureCanvas';
import TaskInput from './TaskInput';

export default function App() {
  const [blastRadius, setBlastRadius] = useState(null);

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
