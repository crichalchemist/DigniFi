/**
 * Progress Indicator - Multi-step wizard progress tracker
 *
 * Trauma-informed design: Emphasizes accomplishment, not shame
 * Accessibility: ARIA labels, keyboard navigation, screen reader support
 */

interface Step {
  number: number;
  label: string;
  isCompleted: boolean;
  isCurrent: boolean;
}

interface ProgressIndicatorProps {
  steps: Step[];
  currentStep: number;
}

export function ProgressIndicator({ steps, currentStep }: ProgressIndicatorProps) {
  return (
    <nav className="progress-indicator" aria-label="Intake progress" role="navigation">
      <ol className="progress-steps">
        {steps.map((step, index) => (
          <li
            key={step.number}
            className={`progress-step ${
              step.isCompleted ? 'completed' : step.isCurrent ? 'current' : 'upcoming'
            }`}
            aria-current={step.isCurrent ? 'step' : undefined}
          >
            <div className="step-marker">
              {step.isCompleted ? (
                <svg
                  className="step-checkmark"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                  aria-hidden="true"
                >
                  <path
                    fillRule="evenodd"
                    d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                    clipRule="evenodd"
                  />
                </svg>
              ) : (
                <span className="step-number" aria-label={`Step ${step.number}`}>
                  {step.number}
                </span>
              )}
            </div>
            <div className="step-label">
              <span className="step-name">{step.label}</span>
              {step.isCompleted && (
                <span className="step-status" aria-label="Completed">
                  Complete
                </span>
              )}
            </div>
            {index < steps.length - 1 && (
              <div
                className={`step-connector ${step.isCompleted ? 'completed' : ''}`}
                aria-hidden="true"
              />
            )}
          </li>
        ))}
      </ol>

      {/* Below 1024px the numbered row is hidden and this summary and stripe show instead
          (global.css): nine labelled steps don't fit a phone at the 16px text floor */}
      <div className="progress-compact">
        <p className="progress-compact-text">
          {`Step ${currentStep} of ${steps.length}: ${steps[currentStep - 1]?.label ?? ''}`}
        </p>
        <div className="progress-stripe" aria-hidden="true">
          {steps.map((step) => (
            <span
              key={step.number}
              className={`progress-stripe-segment ${
                step.isCompleted || step.isCurrent ? 'filled' : ''
              }`}
            />
          ))}
        </div>
      </div>

      {/* Progress percentage for screen readers */}
      <div className="sr-only" aria-live="polite" aria-atomic="true">
        You have completed {steps.filter((s) => s.isCompleted).length} of {steps.length} steps. You
        are on step {currentStep}: {steps[currentStep - 1]?.label}.
      </div>
    </nav>
  );
}

export default ProgressIndicator;
