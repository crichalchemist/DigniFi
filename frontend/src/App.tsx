/**
 * DigniFi - Trauma-informed bankruptcy filing platform
 *
 * Root application component with AuthProvider, IntakeProvider, and routing.
 * IntakeLayout wraps /intake and /forms in a single IntakeProvider so session
 * state persists across the wizard → dashboard navigation.
 */

import { BrowserRouter, Routes, Route, Outlet } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { IntakeProvider } from './context/IntakeContext';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { SkipNavigation } from './components/common';
import { LandingPage } from './pages/LandingPage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { IntakeWizard } from './pages/IntakeWizard';
import { FormDashboard } from './pages/FormDashboard';
import { Component, type ReactNode, type ErrorInfo } from 'react';
import './App.css';

/** Catch render errors so the whole app doesn't go blank. */
class ErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null };
  static getDerivedStateFromError(error: Error) { return { error }; }
  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('ErrorBoundary caught:', error, info.componentStack);
  }
  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: '2rem', maxWidth: '600px', margin: '0 auto' }}>
          <h1>Something went wrong</h1>
          <p>We encountered an unexpected error. Please try refreshing the page.</p>
          <pre style={{ fontSize: '0.8rem', overflow: 'auto', background: '#f5f5f5', padding: '1rem' }}>
            {this.state.error.message}
          </pre>
          <button onClick={() => window.location.href = '/'}>Return Home</button>
        </div>
      );
    }
    return this.props.children;
  }
}

/** Shared IntakeProvider for wizard + dashboard routes. */
function IntakeLayout() {
  return (
    <IntakeProvider>
      <Outlet />
    </IntakeProvider>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <SkipNavigation />
        <ErrorBoundary>
        <div className="app">
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route element={<ProtectedRoute />}>
              <Route element={<IntakeLayout />}>
                <Route path="/intake" element={<IntakeWizard />} />
                <Route path="/forms" element={<FormDashboard />} />
              </Route>
            </Route>
          </Routes>
        </div>
        </ErrorBoundary>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
