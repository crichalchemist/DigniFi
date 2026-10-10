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
import { api, APIClientError } from '../api/client';
import { trackEvent } from '../utils/analytics';
import { hydrateAmounts } from '../utils/parseAmount';
import { Button } from '../components/common';
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
import { EXPENSE_FIELDS } from '../types/api';

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

// DRF sends these decimals as strings ("2500.00"). The steps add and compare them,
// so they become numbers as session data enters wizard state.
const ASSET_AMOUNT_FIELDS = ['current_value', 'amount_owed'] as const;
const DEBT_AMOUNT_FIELDS = ['amount_owed', 'monthly_payment'] as const;

export function IntakeWizard() {
  const navigate = useNavigate();
  const {
    session,
    createSession,
    loadSession,
    updateCurrentStep,
    completeSession,
    calculateMeansTest,
  } = useIntake();
  const [currentStepNumber, setCurrentStepNumber] = useState(1);
  const [canProceed, setCanProceed] = useState(false);
  const sessionStartRef = useRef<number>(0);

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
  // Read the session on mount
  // =========================================================================

  // Fixed at mount: the session in context, else the saved resume pointer, else null for a
  // filer with no saved session. A failed read is retried for this same session rather
  // than starting a new one, even if the pointer was cleared in the meantime.
  const [sessionIdToRead] = useState<number | null>(() => {
    const savedSessionId = localStorage.getItem('current_session_id');
    return session?.id ?? (savedSessionId ? parseInt(savedSessionId, 10) : null);
  });
  const [sessionRead, setSessionRead] = useState<'pending' | 'failed' | 'done'>('pending');
  const [readAttempt, setReadAttempt] = useState(0);

  // Every wizard entry re-reads the session, and no step renders until the read returns
  // (DIG-1, DIG-30). The copy in context can predate an upload on /documents; a step that
  // mounted on it would autosave that stale copy over what the server now holds.
  useEffect(() => {
    let cancelled = false;

    const openSession = async (): Promise<IntakeSession> => {
      if (sessionIdToRead === null) {
        // No session in context AND no saved session — create a new one (District ID 1 = ILND)
        return createSession(1);
      }
      try {
        return await loadSession(sessionIdToRead);
      } catch (error) {
        // A 404 means the saved session is gone or belongs to someone else (a shared
        // computer). Retrying cannot help, so start a new one, as for a new filer.
        if (error instanceof APIClientError && error.statusCode === 404) {
          return createSession(1);
        }
        throw error;
      }
    };

    openSession()
      .then((fresh) => {
        if (cancelled) return;
        setCurrentStepNumber(fresh.current_step);
        if (fresh.debtor_info) setDebtorData(fresh.debtor_info);
        if (fresh.income_info) setIncomeData(fresh.income_info);
        if (fresh.expense_info) setExpenseData(hydrateAmounts(fresh.expense_info, EXPENSE_FIELDS));
        if (fresh.assets)
          setAssetsData(fresh.assets.map((asset) => hydrateAmounts(asset, ASSET_AMOUNT_FIELDS)));
        if (fresh.debts)
          setDebtsData(fresh.debts.map((debt) => hydrateAmounts(debt, DEBT_AMOUNT_FIELDS)));
        setSessionRead('done');
      })
      .catch(() => {
        if (!cancelled) setSessionRead('failed');
      });

    return () => {
      cancelled = true;
    };
    // Runs once per wizard entry and once per Try again. createSession and loadSession are
    // fresh closures on every render, so listing them would re-read on every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [readAttempt]);

  const handleRetry = () => {
    setSessionRead('pending');
    setReadAttempt((attempt) => attempt + 1);
  };

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

      // Document upload sits between step 1 and step 2. The debtor's own details are
      // typed by hand; uploads then pre-fill the financial steps that follow, so the
      // detour has to happen before Income rather than after Review. current_step is
      // already persisted as 2, so returning to /intake resumes at Income — see the
      // session-read effect above.
      if (nextStep === 2) {
        navigate('/documents');
        return;
      }

      setCurrentStepNumber(nextStep);
      // Contracts (6) and Codebtors (7) are optional — pre-approve so Continue stays enabled
      setCanProceed(nextStep === 6 || nextStep === 7);
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

      case 'income_info':
        // Send the months alone: IncomeInfoStep re-emits them as stored unless the filer
        // entered source amounts. Echoing other fields read from the server (a blank
        // marital_status) is a 400 that would strand the filer on Income.
        await api.intake.updateSession(session.id, {
          income_info: { monthly_income: incomeData.monthly_income },
        } as Partial<IntakeSession>);
        break;

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

  if (sessionRead === 'failed') {
    return (
      <div className="wizard-loading">
        <p role="alert">
          We couldn't get your latest information just now. Please try again in a moment.
        </p>
        <Button onClick={handleRetry}>Try again</Button>
      </div>
    );
  }

  // Steps mount only once the read has filled them, so the first autosave sends server data.
  if (!session || sessionRead !== 'done') {
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
        <p>
          {sessionIdToRead === null
            ? 'Starting your intake session...'
            : 'Loading your information...'}
        </p>
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
