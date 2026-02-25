/**
 * ProtectedRoute - Redirects unauthenticated users to login
 *
 * Shows a loading spinner while auth state is being restored (silent refresh).
 * Renders child routes via <Outlet /> when authenticated.
 */

import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

export function ProtectedRoute() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="wizard-loading" role="status" aria-label="Checking authentication">
        <svg className="loading-spinner spinner" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="10" stroke="#667eea" strokeWidth="4" opacity="0.3" />
          <path
            fill="#667eea"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
        <p>Loading your session...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}

export default ProtectedRoute;
