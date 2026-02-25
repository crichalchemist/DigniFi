/**
 * Login Page - Trauma-informed sign-in experience
 *
 * Uses existing FormField component for consistency.
 * Error messages are dignity-preserving ("We couldn't find that account").
 */

import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { FormField } from '../components/common/FormField';
import { Button } from '../components/common/Button';

export function LoginPage() {
  const { login, isLoading, error, clearError, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  // Redirect if already authenticated
  if (isAuthenticated) {
    navigate('/intake', { replace: true });
    return null;
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    clearError();

    try {
      await login(username, password);
      navigate('/intake', { replace: true });
    } catch {
      // Error is handled by AuthContext
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-header">
          <h1 className="auth-title">Welcome back</h1>
          <p className="auth-subtitle">
            Sign in to continue your filing process
          </p>
        </div>

        {error && (
          <div className="wizard-error" role="alert">
            <div>
              <p className="error-title">Unable to sign in</p>
              <p className="error-message">{error}</p>
              <button className="error-dismiss" onClick={clearError}>
                Dismiss
              </button>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} noValidate>
          <FormField
            label="Username or email"
            name="username"
            type="text"
            required
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />

          <FormField
            label="Password"
            name="password"
            type="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />

          <Button
            type="submit"
            variant="primary"
            fullWidth
            isLoading={isLoading}
            loadingText="Signing in..."
            disabled={!username || !password}
          >
            Sign In
          </Button>
        </form>

        <p className="auth-footer-text">
          Don't have an account?{' '}
          <Link to="/register" className="auth-link">
            Create one here
          </Link>
        </p>
      </div>
    </div>
  );
}

export default LoginPage;
