/**
 * Intake Wizard - Main container for multi-step bankruptcy intake
 *
 * Orchestrates the wizard flow, manages step navigation,
 * and handles data persistence to backend API.
 */

import { useState, useEffect } from 'react';
import { useIntake } from '../context/IntakeContext';
import { api } from '../api/client';
import { WizardLayout } from '../components/wizard/WizardLayout';
import { DebtorInfoStep, IncomeInfoStep } from '../components/wizard/steps';
import type { DebtorInfo, IncomeInfo } from '../types/api';

// ============================================================================
// Wizard Configuration
// ============================================================================

const WIZARD_STEPS = [
  { number: 1, label: 'Your Information', key: 'debtor_info' },
  { number: 2, label: 'Income', key: 'income_info' },
  { number: 3, label: 'Expenses', key: 'expense_info' },
  { number: 4, label: 'Assets', key: 'assets' },
  { number: 5, label: 'Amounts Owed', key: 'debts' }, // Trauma-informed: "amounts owed" vs "debts"
  { number: 6, label: 'Review & Results', key: 'review' },
];

export function IntakeWizard() {
  const { session, createSession, updateCurrentStep, completeSession } = useIntake();
  const [currentStepNumber, setCurrentStepNumber] = useState(1);
  const [canProceed, setCanProceed] = useState(false);

  // Step-specific data
  const [debtorData, setDebtorData] = useState<Partial<DebtorInfo>>({});
  const [incomeData, setIncomeData] = useState<Partial<IncomeInfo>>({});

  // =========================================================================
  // Initialize session on mount
  // =========================================================================

  useEffect(() => {
    if (!session) {
      // Create new session (default to Illinois Northern District for MVP)
      createSession(1); // District ID 1 = ILND
    } else {
      // Resume from saved step
      setCurrentStepNumber(session.current_step);

      // Load existing data
      if (session.debtor_info) {
        setDebtorData(session.debtor_info);
      }
      if (session.income_info) {
        setIncomeData(session.income_info);
      }
    }
  }, []);

  // =========================================================================
  // Navigation Handlers
  // =========================================================================

  const handleNext = async () => {
    if (!session) return;

    // Save current step data before advancing
    try {
      await saveCurrentStepData();

      // Advance to next step
      const nextStep = currentStepNumber + 1;
      await updateCurrentStep(nextStep);
      setCurrentStepNumber(nextStep);
      setCanProceed(false); // Reset validation for next step
    } catch (error) {
      console.error('Error advancing to next step:', error);
    }
  };

  const handlePrevious = () => {
    const prevStep = currentStepNumber - 1;
    if (prevStep >= 1) {
      setCurrentStepNumber(prevStep);
      // Load data for previous step if needed
    }
  };

  const handleComplete = async () => {
    try {
      await saveCurrentStepData();
      await completeSession();
      // Navigate to results page (implement later)
      console.log('Intake completed successfully!');
    } catch (error) {
      console.error('Error completing intake:', error);
    }
  };

  // =========================================================================
  // Data Persistence
  // =========================================================================

  const saveCurrentStepData = async () => {
    if (!session) return;

    const currentStep = WIZARD_STEPS[currentStepNumber - 1];

    switch (currentStep.key) {
      case 'debtor_info':
        await api.debtor.createOrUpdate(session.id, debtorData);
        break;

      case 'income_info':
        await api.income.createOrUpdate(session.id, incomeData);
        break;

      // Add other steps as they're implemented
      default:
        console.log(`Saving data for ${currentStep.key} not yet implemented`);
    }
  };

  // =========================================================================
  // Render Step Content
  // =========================================================================

  const renderStepContent = (stepNumber: number) => {
    switch (stepNumber) {
      case 1:
        return (
          <DebtorInfoStep
            initialData={debtorData}
            onDataChange={setDebtorData}
            onValidationChange={setCanProceed}
          />
        );

      case 2:
        return (
          <IncomeInfoStep
            initialData={incomeData}
            onDataChange={setIncomeData}
            onValidationChange={setCanProceed}
          />
        );

      case 3:
        return (
          <div className="placeholder-step">
            <h3>Expenses Step</h3>
            <p>This step will collect your monthly expenses.</p>
            <button type="button" onClick={() => setCanProceed(true)}>
              Mark as complete (placeholder)
            </button>
          </div>
        );

      case 4:
        return (
          <div className="placeholder-step">
            <h3>Assets Step</h3>
            <p>This step will collect information about your assets.</p>
            <button type="button" onClick={() => setCanProceed(true)}>
              Mark as complete (placeholder)
            </button>
          </div>
        );

      case 5:
        return (
          <div className="placeholder-step">
            <h3>Amounts Owed Step</h3>
            <p>This step will collect information about amounts you owe.</p>
            <button type="button" onClick={() => setCanProceed(true)}>
              Mark as complete (placeholder)
            </button>
          </div>
        );

      case 6:
        return (
          <div className="placeholder-step">
            <h3>Review & Results</h3>
            <p>This will show your means test results and Form 101 preview.</p>
            <button type="button" onClick={() => setCanProceed(true)}>
              Mark as complete (placeholder)
            </button>
          </div>
        );

      default:
        return <div>Unknown step</div>;
    }
  };

  const wizardSteps = WIZARD_STEPS.map((step) => ({
    ...step,
    component: renderStepContent(step.number),
  }));

  // =========================================================================
  // Render
  // =========================================================================

  if (!session) {
    return (
      <div className="wizard-loading">
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
        </div>
        <p>Starting your intake session...</p>
      </div>
    );
  }

  return (
    <WizardLayout
      steps={wizardSteps}
      currentStepNumber={currentStepNumber}
      onNext={handleNext}
      onPrevious={handlePrevious}
      onComplete={handleComplete}
      canGoNext={canProceed}
      canGoPrevious={currentStepNumber > 1}
      isLastStep={currentStepNumber === WIZARD_STEPS.length}
    />
  );
}

export default IntakeWizard;
