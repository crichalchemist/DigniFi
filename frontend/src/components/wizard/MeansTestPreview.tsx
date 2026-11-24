/**
 * MeansTestPreview - Collapsible sidebar panel showing the income test's result
 *
 * Provides real-time feedback during intake to reduce user anxiety.
 * Uses debounced API calls to avoid flooding the backend.
 * The result is the form's arithmetic, never a verdict: its words come from the outcome
 * (utils/meansOutcome.ts), and every result ends with the court's decision (UPL).
 */

import { useState } from 'react';
import { useDebouncedMeansTest } from '../../hooks/useDebouncedMeansTest';
import { UPLDisclaimer } from '../compliance';
import { UPL_MEANS_TEST_DISCLAIMER } from '../../constants/upl';
import {
  MEANS_TEST_INCOME_LABEL,
  MEANS_TEST_PREVIEW_TITLE,
  MEANS_TEST_UPDATING,
  MEDIAN_FOR_HOUSEHOLD_OF,
} from '../../constants/copy';
import { meansOutcomeSentences } from '../../utils/meansOutcome';

interface MeansTestPreviewProps {
  sessionId: number | null;
  currentStep: number;
  /** Counts the Amounts Owed saves that changed line 16's or the Supp's answers (F0) */
  routeAnswersSaved?: number;
}

export function MeansTestPreview({
  sessionId,
  currentStep,
  routeAnswersSaved,
}: MeansTestPreviewProps) {
  // Collapsed by default so the result stays unobtrusive; the styled header
  // invites the filer to open it when they want reassurance.
  const [isExpanded, setIsExpanded] = useState(false);
  const { result, isCalculating, statusMessage } = useDebouncedMeansTest({
    sessionId,
    currentStep,
    routeAnswersSaved,
  });

  // Don't render before step 2 (income)
  if (currentStep < 2) return null;

  const formatCurrency = (amount: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);

  // An older reply, or a test's body, may omit these keys
  const sentences = result
    ? meansOutcomeSentences(
        result.outcome ?? null,
        result.family_size ?? null,
        result.tables_gap ?? null,
        result.open_on ?? null,
        'sidebar'
      )
    : [];

  return (
    <aside className="means-test-preview" aria-label={MEANS_TEST_PREVIEW_TITLE}>
      <button
        type="button"
        className="means-test-preview-toggle"
        onClick={() => setIsExpanded(!isExpanded)}
        aria-expanded={isExpanded}
        aria-controls="means-test-preview-content"
      >
        <span className="means-test-preview-toggle-text">{MEANS_TEST_PREVIEW_TITLE}</span>
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
              <span>{MEANS_TEST_UPDATING}</span>
            </div>
          )}

          {!isCalculating && statusMessage && (
            <p className="means-test-preview-status" aria-live="polite">
              {statusMessage}
            </p>
          )}

          {!isCalculating && result && (
            <div className="means-test-preview-result" aria-live="polite">
              {/* The outcome's words, then the court's decision. With no outcome neither shows. */}
              {sentences.length > 0 && (
                <div className="means-test-preview-indicator">
                  <p className="means-test-preview-indicator-text">{sentences.join(' ')}</p>
                  <UPLDisclaimer text={UPL_MEANS_TEST_DISCLAIMER} variant="inline" />
                </div>
              )}

              {/* Key numbers */}
              <dl className="means-test-preview-details">
                <div className="means-test-preview-detail">
                  <dt>{MEANS_TEST_INCOME_LABEL}</dt>
                  <dd>{formatCurrency(result.cmi)}</dd>
                </div>
                <div className="means-test-preview-detail">
                  <dt>
                    {MEDIAN_FOR_HOUSEHOLD_OF} {result.family_size}
                  </dt>
                  <dd>{formatCurrency(result.median_income_threshold / 12)}</dd>
                </div>
              </dl>
            </div>
          )}
        </div>
      )}
    </aside>
  );
}

export default MeansTestPreview;
