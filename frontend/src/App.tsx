/**
 * DigniFi - Trauma-informed bankruptcy filing platform
 *
 * Root application component with IntakeProvider for state management
 */

import { IntakeProvider } from './context/IntakeContext';
import { IntakeWizard } from './pages/IntakeWizard';
import './App.css';

function App() {
  return (
    <IntakeProvider>
      <div className="app">
        <IntakeWizard />
      </div>
    </IntakeProvider>
  );
}

export default App;
