/**
 * Wizard Layout - Container for multi-step bankruptcy intake wizard
 *
 * Desktop-first design with trauma-informed UX
 * Accessibility: Keyboard navigation, screen reader support, high contrast
 */

import { ReactNode } from 'react';
import { ProgressIndicator, Button } from '../common';
import { useIntake } from '../../context/IntakeContext';

interface WizardStep {
  number: number;
  label: string;
  component: ReactNode;
}

interface WizardLayoutProps {
  steps: WizardStep[];
  currentStepNumber: number;
  onNext?: () => void | Promise<void>;
  onPrevious?: () => void;
  onComplete?: () => void | Promise<void>;
  nextButtonText?: string;
  previousButtonText?: string;
  completeButtonText?: string;
  canGoNext?: boolean;
  canGoPrevious?: boolean;
  isLastStep?: boolean;
}

export function WizardLayout({
  steps,
  currentStepNumber,
  onNext,
  onPrevious,
  onComplete,
  nextButtonText = 'Continue',
  previousButtonText = 'Go Back',
  completeButtonText = 'Complete Intake',
  canGoNext = true,
  canGoPrevious = true,
  isLastStep = false,
}: WizardLayoutProps) {
  const { isLoading, error, clearError } = useIntake();

  const progressSteps = steps.map((step) => ({
    number: step.number,
    label: step.label,
    isCompleted: step.number < currentStepNumber,
    isCurrent: step.number === currentStepNumber,
  }));

  const currentStep = steps.find((s) => s.number === currentStepNumber);

  const handleNext = async () => {
    if (onNext) {
      try {
        await onNext();
      } catch (err) {
        // Error handled by context
        console.error('Error advancing wizard:', err);
      }
    }
  };

  const handleComplete = async () => {
    if (onComplete) {
      try {
        await onComplete();
      } catch (err) {
        // Error handled by context
        console.error('Error completing wizard:', err);
      }
    }
  };

  return (
    <div className="wizard-layout">
      {/* Header with progress indicator */}
      <header className="wizard-header">
        <div className="wizard-container">
          <h1 className="wizard-title">Bankruptcy Intake</h1>
          <p className="wizard-subtitle">
            We'll guide you through the information needed to understand your options.
          </p>
          <ProgressIndicator steps={progressSteps} currentStep={currentStepNumber} />
        </div>
      </header>

      {/* Main content area */}
      <main className="wizard-content">
        <div className="wizard-container">
          {/* Error display (trauma-informed messaging) */}
          {error && (
            <div
              className="wizard-error"
              role="alert"
              aria-live="assertive"
            >
              <div className="error-icon" aria-hidden="true">
                <svg
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  className="error-icon-svg"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
              <div className="error-content">
                <h3 className="error-title">We encountered an issue</h3>
                <p className="error-message">{error}</p>
                <button
                  type="button"
                  className="error-dismiss"
                  onClick={clearError}
                  aria-label="Dismiss error message"
                >
                  Dismiss
                </button>
              </div>
            </div>
          )}

          {/* Current step content */}
          <div className="wizard-step">
            <h2 className="step-title">{currentStep?.label}</h2>
            <div className="step-content">{currentStep?.component}</div>
          </div>
        </div>
      </main>

      {/* Footer with navigation buttons */}
      <footer className="wizard-footer">
        <div className="wizard-container">
          <div className="wizard-navigation">
            {/* Previous button (hidden on first step) */}
            {currentStepNumber > 1 && (
              <Button
                variant="outline"
                onClick={onPrevious}
                disabled={!canGoPrevious || isLoading}
                icon={
                  <svg
                    viewBox="0 0 20 20"
                    fill="currentColor"
                    className="icon"
                    aria-hidden="true"
                  >
                    <path
                      fillRule="evenodd"
                      d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                }
                iconPosition="left"
              >
                {previousButtonText}
              </Button>
            )}

            {/* Spacer to push next button to right */}
            <div className="navigation-spacer" />

            {/* Next/Complete button */}
            {isLastStep ? (
              <Button
                variant="primary"
                onClick={handleComplete}
                disabled={!canGoNext || isLoading}
                isLoading={isLoading}
                loadingText="Finalizing..."
                icon={
                  <svg
                    viewBox="0 0 20 20"
                    fill="currentColor"
                    className="icon"
                    aria-hidden="true"
                  >
                    <path
                      fillRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                }
                iconPosition="right"
              >
                {completeButtonText}
              </Button>
            ) : (
              <Button
                variant="primary"
                onClick={handleNext}
                disabled={!canGoNext || isLoading}
                isLoading={isLoading}
                loadingText="Saving..."
                icon={
                  <svg
                    viewBox="0 0 20 20"
                    fill="currentColor"
                    className="icon"
                    aria-hidden="true"
                  >
                    <path
                      fillRule="evenodd"
                      d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                }
                iconPosition="right"
              >
                {nextButtonText}
              </Button>
            )}
          </div>

          {/* Help text */}
          <p className="wizard-help-text">
            Your progress is automatically saved. You can return anytime to continue.
          </p>
        </div>
      </footer>

      {/* Loading overlay (for network requests) */}
      {isLoading && (
        <div className="wizard-loading-overlay" aria-hidden="true">
          <div className="loading-spinner">
            <svg
              className="spinner"
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <circle
                className="spinner-track"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="spinner-head"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            <span className="sr-only">Loading, please wait...</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default WizardLayout;
