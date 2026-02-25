/**
 * Landing Page - First impression for DigniFi
 *
 * Trauma-informed, dignity-preserving messaging.
 * Redirects authenticated users straight to intake.
 */

import { useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/common/Button';

export function LandingPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      navigate('/intake', { replace: true });
    }
  }, [isAuthenticated, isLoading, navigate]);

  if (isLoading) return null;

  return (
    <div className="landing-page">
      {/* Hero Section */}
      <header className="landing-hero">
        <div className="landing-container">
          <h1 className="landing-title">
            Take the first step toward financial relief
          </h1>
          <p className="landing-subtitle">
            DigniFi guides you through the bankruptcy filing process with
            clear, plain-language explanations — at no cost. You deserve a
            fresh start.
          </p>
          <div className="landing-cta-group">
            <Link to="/register">
              <Button variant="primary" size="lg">
                Get Started
              </Button>
            </Link>
            <Link to="/login">
              <Button variant="outline" size="lg">
                Sign In
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Value Propositions */}
      <section className="landing-values" aria-label="Why DigniFi">
        <div className="landing-container">
          <div className="landing-cards">
            <article className="landing-card">
              <div className="landing-card-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 1v22M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6" />
                </svg>
              </div>
              <h2 className="landing-card-title">Free to Use</h2>
              <p className="landing-card-text">
                Filing for bankruptcy shouldn't cost money you don't have.
                DigniFi is completely free — no hidden fees, no premium
                tiers.
              </p>
            </article>

            <article className="landing-card">
              <div className="landing-card-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                  <path d="M7 11V7a5 5 0 0110 0v4" />
                </svg>
              </div>
              <h2 className="landing-card-title">Private &amp; Secure</h2>
              <p className="landing-card-text">
                Your financial information is encrypted and never shared.
                We believe your story is yours to tell, on your terms.
              </p>
            </article>

            <article className="landing-card">
              <div className="landing-card-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M12 16v-4M12 8h.01" />
                </svg>
              </div>
              <h2 className="landing-card-title">Legal Information</h2>
              <p className="landing-card-text">
                We explain what the law says in plain language so you can
                make informed decisions. This is information, not legal
                advice.
              </p>
            </article>
          </div>
        </div>
      </section>

      {/* UPL Disclaimer Footer */}
      <footer className="landing-footer">
        <div className="landing-container">
          <p className="landing-disclaimer">
            DigniFi provides legal <strong>information</strong>, not legal
            advice. This platform does not create an attorney-client
            relationship. If you need legal advice, please consult a
            licensed attorney in your jurisdiction.
          </p>
        </div>
      </footer>
    </div>
  );
}

export default LandingPage;
