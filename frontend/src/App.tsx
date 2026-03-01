/**
 * DigniFi - Trauma-informed bankruptcy filing platform
 *
 * Root application component with AuthProvider, IntakeProvider, and routing.
 */

import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { IntakeProvider } from './context/IntakeContext';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { SkipNavigation } from './components/common';
import { LandingPage } from './pages/LandingPage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { IntakeWizard } from './pages/IntakeWizard';
import { FormDashboard } from './pages/FormDashboard';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <SkipNavigation />
        <div className="app">
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route element={<ProtectedRoute />}>
              <Route
                path="/intake"
                element={
                  <IntakeProvider>
                    <IntakeWizard />
                  </IntakeProvider>
                }
              />
              <Route
                path="/forms"
                element={
                  <IntakeProvider>
                    <FormDashboard />
                  </IntakeProvider>
                }
              />
            </Route>
          </Routes>
        </div>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
