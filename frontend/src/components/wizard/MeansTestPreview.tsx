/**
 * MeansTestPreview - Collapsible sidebar panel showing live eligibility estimate
 *
 * Provides real-time feedback during intake to reduce user anxiety.
 * Uses debounced API calls to avoid flooding the backend.
 * Always includes UPL disclaimer — this is an estimate, not legal advice.
 */

import { useState } from 'react';
import { useDebouncedMeansTest } from '../../hooks/useDebouncedMeansTest';
import { UPLDisclaimer } from '../compliance';
import { UPL_MEANS_TEST_DISCLAIMER } from '../../constants/upl';

interface MeansTestPreviewProps {
  sessionId: number | null;
  currentStep: number;
}

export function MeansTestPreview({ sessionId, currentStep }: MeansTestPreviewProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const { result, isCalculating, statusMessage } = useDebouncedMeansTest({
    sessionId,
    currentStep,
  });

  // Don't render before step 2 (income)
  if (currentStep < 2) return null;

  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);

  return (
    <aside
      className="means-test-preview"
      aria-label="Eligibility estimate"
    >
      <button
        type="button"
        className="means-test-preview-toggle"
        onClick={() => setIsExpanded(!isExpanded)}
        aria-expanded={isExpanded}
        aria-controls="means-test-preview-content"
      >
        <span className="means-test-preview-toggle-text">
          Eligibility Estimate
        </span>
        <svg
          className={`means-test-preview-chevron ${isExpanded ? 'expanded' : ''}`}
          viewBox="0 0 20 20"
          fill="currentColor"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
            clipRule="evenodd"
          />
        </svg>
      </button>

      {isExpanded && (
        <div id="means-test-preview-content" className="means-test-preview-body">
          {isCalculating && (
            <div className="means-test-preview-loading" aria-live="polite">
              <div className="means-test-preview-spinner" aria-hidden="true" />
              <span>Updating estimate...</span>
            </div>
          )}

          {!isCalculating && statusMessage && (
            <p className="means-test-preview-status" aria-live="polite">
              {statusMessage}
            </p>
          )}

          {!isCalculating && result && (
            <div className="means-test-preview-result" aria-live="polite">
              {/* Eligibility indicator */}
              <div
                className={`means-test-preview-indicator ${
                  result.passes_means_test ? 'eligible' : 'review-needed'
                }`}
              >
                <div className="means-test-preview-indicator-icon" aria-hidden="true">
                  {result.passes_means_test ? (
                    <svg viewBox="0 0 20 20" fill="currentColor">
                      <path
                        fillRule="evenodd"
                        d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                        clipRule="evenodd"
                      />
                    </svg>
                  ) : (
                    <svg viewBox="0 0 20 20" fill="currentColor">
                      <path
                        fillRule="evenodd"
                        d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                        clipRule="evenodd"
                      />
                    </svg>
                  )}
                </div>
                <p className="means-test-preview-indicator-text">
                  {result.passes_means_test
                    ? 'Based on your information, you may be eligible for Chapter 7.'
                    : 'Based on your information, Chapter 7 eligibility may need further review.'}
                </p>
              </div>

              {/* Key numbers */}
              <dl className="means-test-preview-details">
                <div className="means-test-preview-detail">
                  <dt>Your Monthly Income</dt>
                  <dd>{formatCurrency(result.current_monthly_income)}</dd>
                </div>
                <div className="means-test-preview-detail">
                  <dt>Median for Household of {result.details.household_size}</dt>
                  <dd>{formatCurrency(result.median_income_threshold / 12)}</dd>
                </div>
                {result.qualifies_for_fee_waiver && (
                  <div className="means-test-preview-detail means-test-preview-detail--highlight">
                    <dt>Fee Waiver</dt>
                    <dd>You may qualify for a filing fee waiver</dd>
                  </div>
                )}
              </dl>
            </div>
          )}

          <UPLDisclaimer text={UPL_MEANS_TEST_DISCLAIMER} variant="inline" />
        </div>
      )}
    </aside>
  );
}

export default MeansTestPreview;
