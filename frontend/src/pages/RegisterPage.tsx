/**
 * Register Page - Account creation with required UPL disclaimer
 *
 * UPL disclaimer checkbox is required — the DB enforces this via CheckConstraint.
 * Auto-logs in after successful registration.
 */

import { useState, useEffect, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { FormField } from '../components/common/FormField';
import { Button } from '../components/common/Button';

const UPL_DISCLAIMER_TEXT =
  'I understand that DigniFi provides legal information, not legal advice. ' +
  'This platform does not create an attorney-client relationship. ' +
  'If I need legal advice, I should consult a licensed attorney.';

export function RegisterPage() {
  const { register, isLoading, error, clearError, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [agreedToUpl, setAgreedToUpl] = useState(false);
  const [agreedToTerms, setAgreedToTerms] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/intake', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    clearError();
    setLocalError(null);

    if (password !== confirmPassword) {
      setLocalError('Passwords do not match. Please try again.');
      return;
    }

    try {
      await register({
        email,
        username,
        password,
        agreed_to_upl_disclaimer: agreedToUpl,
        agreed_to_terms: agreedToTerms,
      });
      navigate('/intake', { replace: true });
    } catch {
      // Error handled by AuthContext
    }
  };

  const displayError = localError || error;
  const formValid =
    email && username && password && confirmPassword && agreedToUpl && agreedToTerms;

  return (
    <div className="auth-page">
      <div className="auth-card auth-card--wide">
        <div className="auth-header">
          <h1 className="auth-title">Create your account</h1>
          <p className="auth-subtitle">
            Get started on your path to financial relief
          </p>
        </div>

        {displayError && (
          <div className="wizard-error" role="alert">
            <div>
              <p className="error-title">Unable to create account</p>
              <p className="error-message">{displayError}</p>
              <button
                className="error-dismiss"
                onClick={() => {
                  clearError();
                  setLocalError(null);
                }}
              >
                Dismiss
              </button>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} noValidate>
          <FormField
            label="Email address"
            name="email"
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />

          <FormField
            label="Username"
            name="username"
            type="text"
            required
            autoComplete="username"
            helpText="This will be used to sign in"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />

          <div className="form-row">
            <FormField
              label="Password"
              name="password"
              type="password"
              required
              autoComplete="new-password"
              helpText="At least 8 characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />

            <FormField
              label="Confirm password"
              name="confirmPassword"
              type="password"
              required
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
            />
          </div>

          {/* UPL Disclaimer — required by DB constraint */}
          <div className="auth-checkbox-group">
            <label className="auth-checkbox-label">
              <input
                type="checkbox"
                checked={agreedToUpl}
                onChange={(e) => setAgreedToUpl(e.target.checked)}
                aria-required="true"
                className="auth-checkbox"
              />
              <span>
                <strong>Legal Information Acknowledgment</strong>
                <span className="required-indicator" aria-label="required"> *</span>
                <br />
                <span className="auth-checkbox-text">{UPL_DISCLAIMER_TEXT}</span>
              </span>
            </label>
          </div>

          <div className="auth-checkbox-group">
            <label className="auth-checkbox-label">
              <input
                type="checkbox"
                checked={agreedToTerms}
                onChange={(e) => setAgreedToTerms(e.target.checked)}
                aria-required="true"
                className="auth-checkbox"
              />
              <span>
                I agree to the{' '}
                <a href="/terms" className="auth-link" target="_blank" rel="noopener">
                  Terms of Service
                </a>
                <span className="required-indicator" aria-label="required"> *</span>
              </span>
            </label>
          </div>

          <Button
            type="submit"
            variant="primary"
            fullWidth
            isLoading={isLoading}
            loadingText="Creating your account..."
            disabled={!formValid}
          >
            Create Account
          </Button>
        </form>

        <p className="auth-footer-text">
          Already have an account?{' '}
          <Link to="/login" className="auth-link">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}

export default RegisterPage;
