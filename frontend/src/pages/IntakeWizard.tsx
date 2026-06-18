/**
 * Intake Wizard - Main container for multi-step bankruptcy intake
 *
 * Orchestrates the wizard flow, manages step navigation,
 * and handles data persistence to backend API.
 */

import { useState, useEffect, useRef, useLayoutEffect } from 'react';
import { useAutoSave } from '../hooks/useAutoSave';
import { useNavigate } from 'react-router-dom';
import { useIntake } from '../context/IntakeContext';
import { api } from '../api/client';
import { trackEvent } from '../utils/analytics';
import { WizardLayout } from '../components/wizard/WizardLayout';
import { MeansTestPreview } from '../components/wizard/MeansTestPreview';
import {
  DebtorInfoStep,
  IncomeInfoStep,
  ExpenseInfoStep,
  AssetsStep,
  DebtsStep,
  ContractsStep,
  CodebtorsStep,
  ReviewStep,
} from '../components/wizard/steps';
import type {
  IntakeSession,
  DebtorInfo,
  IncomeInfo,
  ExpenseInfo,
  AssetInfo,
  DebtInfo,
} from '../types/api';

// ============================================================================
// Wizard Configuration
// ============================================================================

const WIZARD_STEPS = [
  { number: 1, label: 'Your Information', key: 'debtor_info' },
  { number: 2, label: 'Income', key: 'income_info' },
  { number: 3, label: 'Expenses', key: 'expense_info' },
  { number: 4, label: 'Assets', key: 'assets' },
  { number: 5, label: 'Amounts Owed', key: 'debts' },
  { number: 6, label: 'Contracts & Leases', key: 'contracts' },
  { number: 7, label: 'Codebtors', key: 'codebtors' },
  { number: 8, label: 'Review & Results', key: 'review' },
];

export function IntakeWizard() {
  const navigate = useNavigate();
  const { session, createSession, updateCurrentStep, completeSession, calculateMeansTest } =
    useIntake();
  const [currentStepNumber, setCurrentStepNumber] = useState(1);
  const [canProceed, setCanProceed] = useState(false);
  const sessionStartRef = useRef<number>(0);
  const syncedSessionIdRef = useRef<number | null>(null);

  // Initialize session start time after first render
  useLayoutEffect(() => {
    sessionStartRef.current = Date.now();
  }, []);

  // Step-specific data
  const [debtorData, setDebtorData] = useState<Partial<DebtorInfo>>({});
  const [incomeData, setIncomeData] = useState<Partial<IncomeInfo>>({});
  const [expenseData, setExpenseData] = useState<Partial<ExpenseInfo>>({});
  const [assetsData, setAssetsData] = useState<Partial<AssetInfo>[]>([]);
  const [debtsData, setDebtsData] = useState<Partial<DebtInfo>[]>([]);

  // =========================================================================
  // Initialize session on mount
  // =========================================================================

  useEffect(() => {
    if (!session) {
      // No session in context yet — create a new one (District ID 1 = ILND)
      createSession(1);
    } else if (syncedSessionIdRef.current !== session.id) {
      // Session became available (loaded from localStorage or just created).
      // Sync wizard state once per session id to avoid overwriting in-flight steps.
      syncedSessionIdRef.current = session.id;
      // eslint-disable-next-line react-hooks/set-state-in-effect -- initializer: syncing external session state into local wizard state on session arrival
      setCurrentStepNumber(session.current_step);
      if (session.debtor_info) setDebtorData(session.debtor_info);
      if (session.income_info) setIncomeData(session.income_info);
      if (session.expense_info) setExpenseData(session.expense_info);
      if (session.assets) setAssetsData(session.assets);
      if (session.debts) setDebtsData(session.debts);
    }
  }, [session, createSession]);

  // =========================================================================
  // Autosave
  // =========================================================================

  // The data object for the step currently on screen. useAutoSave watches this;
  // when it changes (the user typing), it debounces a call to saveCurrentStepData.
  const currentStepKey = WIZARD_STEPS[currentStepNumber - 1]?.key;
  const currentStepData =
    currentStepKey === 'debtor_info'
      ? debtorData
      : currentStepKey === 'income_info'
        ? incomeData
        : currentStepKey === 'expense_info'
          ? expenseData
          : currentStepKey === 'assets'
            ? assetsData
            : currentStepKey === 'debts'
              ? debtsData
              : null;

  const { saveStatus, saveNow, lastSavedAt } = useAutoSave({
    data: currentStepData,
    // saveCurrentStepData reads the latest step state from its closure, so the
    // `data` snapshot useAutoSave passes to onSave is intentionally unused here.
    onSave: () => saveCurrentStepData(),
    // Only autosave a complete, valid step (see architecture rationale). 'review' has nothing
    // to save; disabled until a session exists.
    enabled: !!session && canProceed && currentStepKey !== 'review',
  });

  // =========================================================================
  // Navigation Handlers
  // =========================================================================

  const handleNext = async () => {
    if (!session) return;

    // Save the current step immediately (flushes any pending debounce). If it
    // fails, do NOT advance — the WizardLayout indicator shows the error.
    const saved = await saveNow();
    if (!saved) return;

    // Advance to next step (updateCurrentStep can rethrow, so keep in try/catch)
    try {
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
    // Save the current step immediately. If it fails, do NOT complete.
    const saved = await saveNow();
    if (!saved) return;

    try {
      await completeSession();
      trackEvent('intake_completed', {
        total_duration_ms: Date.now() - sessionStartRef.current,
        session_id: session?.id,
      });
      const result = await calculateMeansTest();
      if (result.qualifies_for_fee_waiver) {
        navigate('/fee-waiver');
      } else {
        navigate('/sofa');
      }
    } catch (error) {
      console.error('Error completing intake:', error);
      navigate('/forms');
    }
  };

  // =========================================================================
  // Data Persistence
  // =========================================================================

  const saveCurrentStepData = async () => {
    if (!session) return;

    const currentStep = WIZARD_STEPS[currentStepNumber - 1];

    // All step data is saved via PATCH /api/intake/sessions/{id}/
    // The backend IntakeSessionSerializer handles nested create/update
    switch (currentStep.key) {
      case 'debtor_info':
        await api.intake.updateSession(session.id, {
          debtor_info: debtorData,
        } as Partial<IntakeSession>);
        break;

      case 'income_info': {
        // Transform detailed income data to backend format (6-month array)
        // MVP Assumption: Current monthly income is consistent for last 6 months
        const incomePayload = {
          ...incomeData,
          monthly_income: Array(6).fill(incomeData.total_monthly_income || 0),
        };
        await api.intake.updateSession(session.id, {
          income_info: incomePayload,
        } as Partial<IntakeSession>);
        break;
      }

      case 'expense_info':
        await api.intake.updateSession(session.id, {
          expense_info: expenseData,
        } as Partial<IntakeSession>);
        break;

      case 'assets': {
        // Filter out empty/blank asset forms before sending
        const filledAssets = assetsData.filter((a) => a.asset_type && a.description?.trim());
        await api.intake.updateSession(session.id, {
          assets: filledAssets,
        } as Partial<IntakeSession>);
        break;
      }

      case 'debts': {
        // Filter empty forms — debt_type, is_secured, and priority_classification
        // are already set by DebtsStep via DEBT_CATEGORY_META lookup
        const filledDebts = debtsData.filter((d) => d.creditor_name?.trim());
        await api.intake.updateSession(session.id, {
          debts: filledDebts,
        } as Partial<IntakeSession>);
        break;
      }

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
          <ExpenseInfoStep
            initialData={expenseData}
            onDataChange={setExpenseData}
            onValidationChange={setCanProceed}
          />
        );

      case 4:
        return (
          <AssetsStep
            initialData={assetsData}
            onDataChange={setAssetsData}
            onValidationChange={setCanProceed}
          />
        );

      case 5:
        return (
          <DebtsStep
            initialData={debtsData}
            onDataChange={setDebtsData}
            onValidationChange={setCanProceed}
          />
        );

      case 6:
        return <ContractsStep />;

      case 7:
        return <CodebtorsStep />;

      case 8:
        return (
          <ReviewStep
            debtorData={debtorData}
            incomeData={incomeData}
            expenseData={expenseData}
            assetsData={assetsData}
            debtsData={debtsData}
            onValidationChange={setCanProceed}
          />
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
      sidebar={<MeansTestPreview sessionId={session.id} currentStep={currentStepNumber} />}
      saveStatus={saveStatus}
      lastSavedAt={lastSavedAt}
    />
  );
}

export default IntakeWizard;
