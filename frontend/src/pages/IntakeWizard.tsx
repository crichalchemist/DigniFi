/**
 * Intake Wizard - Main container for multi-step bankruptcy intake
 *
 * Orchestrates the wizard flow, manages step navigation,
 * and handles data persistence to backend API.
 */

import { useState, useEffect, useMemo, useRef, useLayoutEffect } from 'react';
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
  ExecutoryContract,
  Codebtor,
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
  const [contractsData, setContractsData] = useState<ExecutoryContract[]>([]);
  const [codebtorsData, setCodebtorsData] = useState<Codebtor[]>([]);

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

    // Contracts and codebtors have their own endpoints, and a new session has none yet. Both
    // lists load before any step shows: Review lists them (DIG-166), and Continue on steps 6
    // and 7 saves the whole list, so a list that failed to load is never saved as empty.
    const openSession = async (): Promise<{
      fresh: IntakeSession;
      contracts: ExecutoryContract[];
      codebtors: Codebtor[];
    }> => {
      if (sessionIdToRead === null) {
        // No session in context AND no saved session — create a new one (District ID 1 = ILND)
        return { fresh: await createSession(1), contracts: [], codebtors: [] };
      }
      let fresh: IntakeSession;
      try {
        fresh = await loadSession(sessionIdToRead);
      } catch (error) {
        // A 404 means the saved session is gone or belongs to someone else (a shared
        // computer). Retrying cannot help, so start a new one, as for a new filer.
        if (error instanceof APIClientError && error.statusCode === 404) {
          return { fresh: await createSession(1), contracts: [], codebtors: [] };
        }
        throw error;
      }
      const [contracts, codebtors] = await Promise.all([
        api.intake.contracts(fresh.id),
        api.intake.codebtors(fresh.id),
      ]);
      return { fresh, contracts, codebtors };
    };

    openSession()
      .then(({ fresh, contracts, codebtors }) => {
        if (cancelled) return;
        setCurrentStepNumber(fresh.current_step);
        if (fresh.debtor_info) setDebtorData(fresh.debtor_info);
        if (fresh.income_info) setIncomeData(fresh.income_info);
        if (fresh.expense_info) setExpenseData(hydrateAmounts(fresh.expense_info, EXPENSE_FIELDS));
        if (fresh.assets)
          setAssetsData(fresh.assets.map((asset) => hydrateAmounts(asset, ASSET_AMOUNT_FIELDS)));
        if (fresh.debts)
          setDebtsData(fresh.debts.map((debt) => hydrateAmounts(debt, DEBT_AMOUNT_FIELDS)));
        setContractsData(contracts);
        setCodebtorsData(codebtors);
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

  // What saving the step on screen sends: PATCH /api/intake/sessions/{id}/, whose nested
  // serializer creates and updates each section. null for Review, and for Contracts and
  // Codebtors, whose lists save through their own endpoints (saveCurrentStepData).
  // useAutoSave compares it with the step's last saved or loaded copy, so a step that only
  // shows what the server holds (a blank row, a recomputed total) sends nothing.
  const currentStepKey = WIZARD_STEPS[currentStepNumber - 1]?.key;
  const currentStepBody = useMemo((): Partial<IntakeSession> | null => {
    switch (currentStepKey) {
      case 'debtor_info':
        return { debtor_info: debtorData } as Partial<IntakeSession>;

      case 'income_info':
        // Send the months alone: IncomeInfoStep re-emits them as stored unless the filer
        // entered source amounts. Echoing other fields read from the server (a blank
        // marital_status) is a 400 that would strand the filer on Income.
        return {
          income_info: { monthly_income: incomeData.monthly_income },
        } as Partial<IntakeSession>;

      case 'expense_info': {
        // The 13 amounts alone. The total is read-only on the server: the step adds it up in
        // floating point, so it can differ from the server's decimal sum in the last digit. A
        // blank box is sent as 0, the column's default; left out, a box the filer cleared would
        // keep its old amount on the server (DIG-55).
        const expenses: Partial<ExpenseInfo> = {};
        for (const field of EXPENSE_FIELDS) expenses[field] = expenseData[field] ?? 0;
        return { expense_info: expenses } as Partial<IntakeSession>;
      }

      case 'assets':
        // Filter out empty/blank asset forms before sending
        return {
          assets: assetsData.filter((a) => a.asset_type && a.description?.trim()),
        } as Partial<IntakeSession>;

      case 'debts':
        // Filter empty forms — debt_type, is_secured, and priority_classification
        // are already set by DebtsStep via DEBT_CATEGORY_META lookup
        return {
          debts: debtsData.filter((d) => d.creditor_name?.trim()),
        } as Partial<IntakeSession>;

      default:
        return null;
    }
  }, [currentStepKey, debtorData, incomeData, expenseData, assetsData, debtsData]);

  const { saveStatus, saveNow, lastSavedAt } = useAutoSave({
    data: currentStepBody,
    // Until the read returns, the steps hold empty placeholders, not the session's data, so
    // they are kept under no step's name.
    dataKey: sessionRead === 'done' ? currentStepKey : undefined,
    onSave: (body) => saveCurrentStepData(body),
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
      // Each step reports its own validity once it shows (Contracts and Codebtors too, DIG-165)
      setCanProceed(false);
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
      // The filer stays on Review, where WizardLayout shows the reason the context recorded
      // (DIG-150). If only the means test failed, the intake is already complete, and
      // pressing Complete again retries both calls.
      console.error('Error completing intake:', error);
    }
  };

  // =========================================================================
  // Data Persistence
  // =========================================================================

  const saveCurrentStepData = async (body: Partial<IntakeSession> | null) => {
    if (!session) return;

    // Contracts and codebtors save as whole lists, only from Continue: their step body is null,
    // so autosave never sends them. Blank rows are left out. The saved rows come back with
    // their ids, so the next save updates them instead of adding them again (DIG-147).
    if (currentStepKey === 'contracts') {
      const named = contractsData.filter((contract) => contract.counterparty_name.trim());
      setContractsData(await api.intake.saveContracts(session.id, named));
      return;
    }
    if (currentStepKey === 'codebtors') {
      const named = codebtorsData.filter((codebtor) => codebtor.name.trim());
      setCodebtorsData(await api.intake.saveCodebtors(session.id, named));
      return;
    }

    if (body === null) {
      console.log(`Saving data for ${currentStepKey} not yet implemented`);
      return;
    }

    await api.intake.updateSession(session.id, body);
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
        return (
          <ContractsStep
            initialData={contractsData}
            onDataChange={setContractsData}
            onValidationChange={setCanProceed}
          />
        );

      case 7:
        return (
          <CodebtorsStep
            initialData={codebtorsData}
            onDataChange={setCodebtorsData}
            onValidationChange={setCanProceed}
          />
        );

      case 8:
        return (
          <ReviewStep
            debtorData={debtorData}
            incomeData={incomeData}
            expenseData={expenseData}
            assetsData={assetsData}
            debtsData={debtsData}
            contractsData={contractsData}
            codebtorsData={codebtorsData}
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
