/**
 * Intake Wizard - Main container for multi-step bankruptcy intake
 *
 * Orchestrates the wizard flow, manages step navigation,
 * and handles data persistence to backend API.
 */

import { useState, useEffect, useMemo, useRef, useLayoutEffect } from 'react';
import { useAutoSave } from '../hooks/useAutoSave';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useIntake } from '../context/IntakeContext';
import { api, APIClientError } from '../api/client';
import { trackEvent } from '../utils/analytics';
import { hydrateAmounts } from '../utils/parseAmount';
import { membersToSend, sentMember } from '../utils/householdRows';
import { entriesToSend, hydrateEntries, sentEntry } from '../utils/incomeEntries';
import type { EntryRow } from '../utils/incomeEntries';
import { Button } from '../components/common';
import { WizardLayout } from '../components/wizard/WizardLayout';
import { MeansTestPreview } from '../components/wizard/MeansTestPreview';
import {
  DebtorInfoStep,
  IncomeInfoStep,
  TakeHomePayStep,
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
  AssetLineAnswer,
  DebtInfo,
  ExecutoryContract,
  Codebtor,
  CompletionError,
  HouseholdMember,
  IncomeEntry,
  IncomePeriod,
  SpouseIncome,
  WizardRow,
} from '../types/api';
import {
  ASSISTANCE_AMOUNT_FIELDS,
  CURRENT_INCOME_FIELDS,
  DEDUCTION_FIELDS,
  EXPENSE_FIELDS,
  EXPENSE_SPECIFY_FIELDS,
  INCOME_FIELDS,
} from '../types/api';
import { WIZARD_STEPS } from '../constants/wizardSteps';

// ============================================================================
// Wizard Configuration
// ============================================================================

// DRF sends these decimals as strings ("2500.00"). The steps add and compare them,
// so they become numbers as session data enters wizard state.
const ASSET_AMOUNT_FIELDS = ['current_value', 'amount_owed'] as const;
const DEBT_AMOUNT_FIELDS = ['amount_owed', 'monthly_payment'] as const;
// The income amounts, the filer's and the spouse's: the ten, the ten now, the two assistance
// amounts and the eight payroll deductions (the Take-home pay step's)
const INCOME_AMOUNT_KEYS = [
  ...INCOME_FIELDS,
  ...CURRENT_INCOME_FIELDS,
  ...ASSISTANCE_AMOUNT_FIELDS,
  ...DEDUCTION_FIELDS,
] as const;

/** One person's eight deductions and the 5h text, a blank deduction as null (3e2 spec §7.4) */
function addDeductions(body: Partial<IncomeInfo>, data: Partial<IncomeInfo>) {
  for (const field of DEDUCTION_FIELDS) body[field] = data[field] ?? null;
  body.payroll_other_specify = data.payroll_other_specify ?? '';
}

/**
 * Adds one person's "now different" answer, the current ten only while it is "yes" (the server
 * keeps what an earlier "yes" stored), and the five assistance fields, always (3e2 spec §7.4).
 * The same keys for the filer's body and the spouse's.
 */
function addNowAndAssistance(body: Partial<IncomeInfo>, data: Partial<IncomeInfo>) {
  body.income_now_different = data.income_now_different ?? null;
  if (data.income_now_different === 'yes') {
    for (const field of CURRENT_INCOME_FIELDS) body[field] = data[field] ?? null;
  }
  body.assistance_answer = data.assistance_answer ?? null;
  body.cash_assistance_kind = data.cash_assistance_kind ?? '';
  body.cash_assistance_amount = data.cash_assistance_amount ?? null;
  body.noncash_assistance_kind = data.noncash_assistance_kind ?? '';
  body.noncash_assistance_value = data.noncash_assistance_value ?? null;
}

/** A row as the server takes it, without the browser's own key */
function withoutKey<Row extends { _key: string }>(row: Row): Partial<Row> {
  const sent: Partial<Row> = { ...row };
  delete sent._key;
  return sent;
}

/**
 * The id each sent row came back with, by the row's key. A session save returns a list it was
 * sent in the order sent (DIG-273), so the row sent at each position takes the id at that
 * position, a row sent with a stale or foreign id included.
 */
function savedIds(sent: { _key: string }[], saved: { id: number }[] | undefined) {
  if (saved?.length !== sent.length) {
    throw new Error('The session save did not return each row it was sent');
  }
  return new Map(sent.map((row, index) => [row._key, saved[index].id]));
}

/**
 * Writes each saved row's id into the row with the same key, wherever that row now sits. A key no
 * longer present (a row removed while its save was on its way) is skipped. Nothing else comes from
 * the reply, so the amounts stay as the filer typed them.
 */
function withSavedIds<Row extends { _key: string; id?: number }>(
  rows: Row[],
  ids: Map<string, number>
): Row[] {
  return rows.map((row) => {
    const id = ids.get(row._key);
    return id === undefined ? row : { ...row, id };
  });
}

export function IntakeWizard() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
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
  // Set while a Continue or Complete press is saving, so a second press can't save the step
  // again: a list saved twice prints each row twice on Schedule G or H
  const pressInFlightRef = useRef(false);
  // How many saves of each list have gone out. A reply writes its ids only if no later save of
  // the list has gone out since: that save left before these ids arrived, so the server has
  // already replaced any row this one created, and the later save's reply brings the ids that hold
  const listSavesRef = useRef({ assets: 0, debts: 0, members: 0, entries: 0, spouseEntries: 0 });

  // Initialize session start time after first render
  useLayoutEffect(() => {
    sessionStartRef.current = Date.now();
  }, []);

  // Step-specific data
  const [debtorData, setDebtorData] = useState<Partial<DebtorInfo>>({});
  // Saved under `household`, beside the debtor's answers
  const [county, setCounty] = useState<string | null>(null);
  const [incomeData, setIncomeData] = useState<Partial<IncomeInfo>>({});
  // The Income step's household list, saved under `household` beside the income, and whether
  // the filer said no one else lives with them or depends on them
  const [householdRows, setHouseholdRows] = useState<WizardRow<HouseholdMember>[]>([]);
  const [noOneElse, setNoOneElse] = useState(false);
  const [spouseIncomeData, setSpouseIncomeData] = useState<SpouseIncome>({});
  // The Income step's businesses and rental properties, the filer's and the spouse's, and whether
  // each said they have none
  const [entryRows, setEntryRows] = useState<EntryRow[]>([]);
  const [noEntries, setNoEntries] = useState(false);
  const [spouseEntryRows, setSpouseEntryRows] = useState<EntryRow[]>([]);
  const [spouseNoEntries, setSpouseNoEntries] = useState(false);
  const [expenseData, setExpenseData] = useState<Partial<ExpenseInfo>>({});
  const [assetsData, setAssetsData] = useState<WizardRow<AssetInfo>[]>([]);
  const [assetAnswers, setAssetAnswers] = useState<Record<string, AssetLineAnswer>>({});
  const [debtsData, setDebtsData] = useState<WizardRow<DebtInfo>[]>([]);
  const [contractsData, setContractsData] = useState<ExecutoryContract[]>([]);
  const [codebtorsData, setCodebtorsData] = useState<Codebtor[]>([]);
  // What Complete last said is missing, listed on Review until the step changes
  const [completionErrors, setCompletionErrors] = useState<CompletionError[]>([]);

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
  // Fixed at mount too: the step a link names (`?step=<key>`, from a refusal on the forms
  // dashboard), opened instead of the saved step once the read returns, and then dropped from the
  // address. Opening it sends no update_step, so the saved step stays where Continue last put it.
  const [linkedStep] = useState(
    () => WIZARD_STEPS.find((step) => step.key === searchParams.get('step'))?.number
  );
  const [sessionRead, setSessionRead] = useState<'pending' | 'failed' | 'done'>('pending');
  const [readAttempt, setReadAttempt] = useState(0);

  // Every wizard entry re-reads the session, and no step renders until the read returns
  // (DIG-1, DIG-30). The copy in context can predate an upload on /documents; a step that
  // mounted on it would autosave that stale copy over what the server now holds.
  useEffect(() => {
    let cancelled = false;

    // Contracts and codebtors have their own endpoints, and a new session has none yet. Both
    // lists load before any step shows: Review lists them (DIG-166), and Continue on steps 7
    // and 8 saves the whole list, so a list that failed to load is never saved as empty.
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
        setCurrentStepNumber(linkedStep ?? fresh.current_step);
        // The link has done its work. Dropped from the address in place, with no new history
        // entry, so a refresh, or Back to the wizard from a later page, opens the saved step,
        // not the linked one again.
        if (linkedStep !== undefined) {
          setSearchParams(
            (params) => {
              const next = new URLSearchParams(params);
              next.delete('step');
              return next;
            },
            { replace: true }
          );
        }
        if (fresh.debtor_info) setDebtorData(fresh.debtor_info);
        if (fresh.household) {
          setCounty(fresh.household.county);
          // A loaded row's key is its id. A list loaded as [] is the filer's "no one else".
          const members = fresh.household.members;
          setHouseholdRows((members ?? []).map((m) => ({ _key: String(m.id), ...m })));
          setNoOneElse(members?.length === 0);
        }
        if (fresh.income_info) {
          setIncomeData(hydrateAmounts(fresh.income_info, INCOME_AMOUNT_KEYS));
          // A list loaded as [] is the filer's "I have none"
          setEntryRows(hydrateEntries(fresh.income_info.business_and_rental));
          setNoEntries(fresh.income_info.business_and_rental?.length === 0);
        }
        if (fresh.spouse_income) {
          setSpouseIncomeData(hydrateAmounts(fresh.spouse_income, INCOME_AMOUNT_KEYS));
          setSpouseEntryRows(hydrateEntries(fresh.spouse_income.business_and_rental));
          setSpouseNoEntries(fresh.spouse_income.business_and_rental?.length === 0);
        }
        if (fresh.expense_info) setExpenseData(hydrateAmounts(fresh.expense_info, EXPENSE_FIELDS));
        // A loaded row's key is its id
        if (fresh.assets)
          setAssetsData(
            fresh.assets.map((asset) => ({
              ...hydrateAmounts(asset, ASSET_AMOUNT_FIELDS),
              _key: String(asset.id),
            }))
          );
        if (fresh.debts)
          setDebtsData(
            fresh.debts.map((debt) => ({
              ...hydrateAmounts(debt, DEBT_AMOUNT_FIELDS),
              _key: String(debt.id),
            }))
          );
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
        return { debtor_info: debtorData, household: { county } } as Partial<IntakeSession>;

      case 'income_info': {
        // The ten amounts and the marriage answer. A blank box is sent as null, so it stays
        // empty on the server and a box the filer cleared is emptied there too, never saved as
        // $0. The old six-month total is read-only.
        const income: Partial<IncomeInfo> = {};
        for (const field of INCOME_FIELDS) income[field] = incomeData[field] ?? null;
        income.marital_status = incomeData.marital_status ?? null;
        income.business_and_rental = entriesToSend(entryRows, noEntries) as IncomeEntry[] | null;
        addNowAndAssistance(income, incomeData);
        // Each household row and entry keeps its `_key` here; saveCurrentStepData leaves it out
        // of the request.
        const body: Partial<Record<keyof IntakeSession, unknown>> = {
          income_info: income,
          household: { members: membersToSend(householdRows, noOneElse) },
        };
        // The spouse's ten only while they live together, so a hidden section neither saves nor
        // blocks, and the server keeps the figures it holds (3e1 spec §5.1)
        if (incomeData.marital_status === 'married_together') {
          const spouse: SpouseIncome = {};
          for (const field of INCOME_FIELDS) spouse[field] = spouseIncomeData[field] ?? null;
          spouse.business_and_rental = entriesToSend(spouseEntryRows, spouseNoEntries) as
            | IncomeEntry[]
            | null;
          addNowAndAssistance(spouse, spouseIncomeData);
          body.spouse_income = spouse;
        }
        return body as Partial<IntakeSession>;
      }

      case 'take_home_pay': {
        // The deductions alone, so neither this step's saved copy nor the Income step's can
        // overwrite what the other saved. Lines 4, 6 and 7 are shown, never sent.
        const income: Partial<IncomeInfo> = {};
        addDeductions(income, incomeData);
        const body: Partial<Record<keyof IntakeSession, unknown>> = { income_info: income };
        if (incomeData.marital_status === 'married_together') {
          const spouse: SpouseIncome = {};
          addDeductions(spouse, spouseIncomeData);
          body.spouse_income = spouse;
        }
        return body as Partial<IntakeSession>;
      }

      case 'expense_info': {
        // The 26 amounts, the three Specify texts and line 3. The total is read-only on the
        // server: the step adds it up in floating point, so it can differ from the server's
        // decimal sum in the last digit. A blank box is sent as 0, the column's default; left
        // out, a box the filer cleared would keep its old amount on the server (DIG-55). A
        // blank Specify box is '' and an unanswered line 3 is null.
        const expenses: Partial<ExpenseInfo> = {};
        for (const field of EXPENSE_FIELDS) expenses[field] = expenseData[field] ?? 0;
        for (const field of EXPENSE_SPECIFY_FIELDS) expenses[field] = expenseData[field] ?? '';
        expenses.expenses_include_others = expenseData.expenses_include_others ?? null;
        return { expense_info: expenses } as Partial<IntakeSession>;
      }

      case 'assets':
        // Filter out empty/blank asset forms before sending. Each row keeps its `_key` here;
        // saveCurrentStepData leaves it out of the request.
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
  }, [
    currentStepKey,
    debtorData,
    county,
    incomeData,
    householdRows,
    noOneElse,
    entryRows,
    noEntries,
    spouseEntryRows,
    spouseNoEntries,
    spouseIncomeData,
    expenseData,
    assetsData,
    debtsData,
  ]);

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
    if (!session || pressInFlightRef.current) return;
    pressInFlightRef.current = true;

    try {
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
    } finally {
      pressInFlightRef.current = false;
    }
  };

  // Go Back, and the "Go to" button beside each reason Complete gave, move without update_step:
  // current_step stays where Continue last put it. Leaving Review drops its reasons.
  const moveToStep = (stepNumber: number) => {
    setCurrentStepNumber(stepNumber);
    setCompletionErrors([]);
  };

  const handlePrevious = () => {
    const prevStep = currentStepNumber - 1;
    if (prevStep >= 1) {
      moveToStep(prevStep);
      // Load data for previous step if needed
    }
  };

  const handleComplete = async () => {
    if (pressInFlightRef.current) return;
    pressInFlightRef.current = true;
    setCompletionErrors([]);

    try {
      // Save the current step immediately. If it fails, do NOT complete.
      const saved = await saveNow();
      if (!saved) return;

      try {
        await completeSession();
        trackEvent('intake_completed', {
          total_duration_ms: Date.now() - sessionStartRef.current,
          session_id: session?.id,
        });
        await calculateMeansTest();
        // Every filer answers Form 101 line 8 next; nothing routes on the means test's result
        // (3f spec §3)
        navigate('/filing-fee');
      } catch (error) {
        // The filer stays on Review, where WizardLayout shows the reason the context recorded
        // (DIG-150), and Review lists each thing Complete found missing. If only the means
        // test failed, the intake is already complete, and pressing Complete again retries
        // both calls.
        if (error instanceof APIClientError && error.errors) setCompletionErrors(error.errors);
        console.error('Error completing intake:', error);
      }
    } finally {
      pressInFlightRef.current = false;
    }
  };

  // =========================================================================
  // Data Persistence
  // =========================================================================

  const saveCurrentStepData = async (
    body: Partial<IntakeSession> | null
  ): Promise<Partial<IntakeSession> | void> => {
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

    // Assets, debts, household members and the Income step's entries carry the browser's own key,
    // which never reaches the server. A household or entry list of null (unanswered) has no rows
    // to pair, but it is still a save of the list: the server then holds no row an earlier save
    // of the list created.
    const { assets, debts, household, income_info, spouse_income } = body as {
      assets?: WizardRow<AssetInfo>[];
      debts?: WizardRow<DebtInfo>[];
      household?: { members?: WizardRow<HouseholdMember>[] | null };
      income_info?: { business_and_rental?: EntryRow[] | null };
      spouse_income?: { business_and_rental?: EntryRow[] | null };
    };
    const sendsMembers = household?.members !== undefined;
    const members = Array.isArray(household?.members) ? household.members : undefined;
    const sendsEntries = income_info?.business_and_rental !== undefined;
    const entries = Array.isArray(income_info?.business_and_rental)
      ? income_info.business_and_rental
      : undefined;
    const sendsSpouseEntries = spouse_income?.business_and_rental !== undefined;
    const spouseEntries = Array.isArray(spouse_income?.business_and_rental)
      ? spouse_income.business_and_rental
      : undefined;
    const request: Partial<Record<keyof IntakeSession, unknown>> = { ...body };
    if (assets) request.assets = assets.map(withoutKey);
    if (debts) request.debts = debts.map(withoutKey);
    if (members) request.household = { members: members.map(withoutKey) };
    if (entries) {
      request.income_info = { ...income_info, business_and_rental: entries.map(withoutKey) };
    }
    if (spouseEntries) {
      request.spouse_income = {
        ...spouse_income,
        business_and_rental: spouseEntries.map(withoutKey),
      };
    }
    const assetsSave = assets ? ++listSavesRef.current.assets : 0;
    const debtsSave = debts ? ++listSavesRef.current.debts : 0;
    const membersSave = sendsMembers ? ++listSavesRef.current.members : 0;
    const entriesSave = sendsEntries ? ++listSavesRef.current.entries : 0;
    const spouseEntriesSave = sendsSpouseEntries ? ++listSavesRef.current.spouseEntries : 0;
    const saved = await api.intake.updateSession(session.id, request as Partial<IntakeSession>);

    // A new row keeps the id its first save gave it, so the next save updates that row instead of
    // replacing it. The copy returned is what the server now holds, built by the same merge as
    // the rows, so autosave sends nothing more until the filer changes something (DIG-273).
    // An older save's reply, once a later save of the list has gone out, changes nothing and
    // keeps the copy sent.
    if (assets) {
      if (assetsSave !== listSavesRef.current.assets) return;
      const ids = savedIds(assets, saved.assets);
      setAssetsData((rows) => withSavedIds(rows, ids));
      return { ...body, assets: withSavedIds(assets, ids) } as Partial<IntakeSession>;
    }
    if (debts) {
      if (debtsSave !== listSavesRef.current.debts) return;
      const ids = savedIds(debts, saved.debts);
      setDebtsData((rows) => withSavedIds(rows, ids));
      return { ...body, debts: withSavedIds(debts, ids) } as Partial<IntakeSession>;
    }

    // One reply pairs every list the body carried: the household's members, the filer's entries
    // and the spouse's. The saved copy goes back through sentMember and sentEntry, as the next
    // body will, so the id written last into each row doesn't make that body differ. A list a
    // later save has overtaken keeps the rows sent.
    if (!members && !entries && !spouseEntries) return;
    const freshMembers = members && membersSave === listSavesRef.current.members;
    const freshEntries = entries && entriesSave === listSavesRef.current.entries;
    const freshSpouseEntries =
      spouseEntries && spouseEntriesSave === listSavesRef.current.spouseEntries;
    if (!freshMembers && !freshEntries && !freshSpouseEntries) return;

    const savedCopy: Partial<Record<keyof IntakeSession, unknown>> = { ...body };
    if (freshMembers) {
      const ids = savedIds(members, saved.household?.members as { id: number }[] | undefined);
      setHouseholdRows((rows) => withSavedIds(rows, ids));
      savedCopy.household = { members: withSavedIds(members, ids).map(sentMember) };
    }
    if (freshEntries) {
      const ids = savedIds(
        entries,
        saved.income_info?.business_and_rental as { id: number }[] | undefined
      );
      setEntryRows((rows) => withSavedIds(rows, ids));
      savedCopy.income_info = {
        ...income_info,
        business_and_rental: withSavedIds(entries, ids).map(sentEntry),
      };
    }
    if (freshSpouseEntries) {
      const ids = savedIds(
        spouseEntries,
        saved.spouse_income?.business_and_rental as { id: number }[] | undefined
      );
      setSpouseEntryRows((rows) => withSavedIds(rows, ids));
      savedCopy.spouse_income = {
        ...spouse_income,
        business_and_rental: withSavedIds(spouseEntries, ids).map(sentEntry),
      };
    }
    return savedCopy as Partial<IntakeSession>;
  };

  // =========================================================================
  // Render Step Content
  // =========================================================================

  const renderStepContent = (key: string) => {
    switch (key) {
      case 'debtor_info':
        return (
          <DebtorInfoStep
            initialData={debtorData}
            onDataChange={setDebtorData}
            onValidationChange={setCanProceed}
            county={county}
            onCountyChange={setCounty}
          />
        );

      case 'income_info':
        return (
          <IncomeInfoStep
            initialData={incomeData}
            onDataChange={setIncomeData}
            onValidationChange={setCanProceed}
            householdRows={householdRows}
            onHouseholdRowsChange={setHouseholdRows}
            noOneElse={noOneElse}
            onNoOneElseChange={setNoOneElse}
            initialSpouseIncome={spouseIncomeData}
            onSpouseIncomeChange={setSpouseIncomeData}
            // Steps are built before the read, but mount only once `session` is set
            incomeWindow={session?.income_window as IncomePeriod}
            answeredWindow={session?.income_info?.answered_window ?? null}
            entryRows={entryRows}
            onEntryRowsChange={setEntryRows}
            spouseEntryRows={spouseEntryRows}
            onSpouseEntryRowsChange={setSpouseEntryRows}
            noEntries={noEntries}
            onNoEntriesChange={setNoEntries}
            spouseNoEntries={spouseNoEntries}
            onSpouseNoEntriesChange={setSpouseNoEntries}
          />
        );

      case 'take_home_pay':
        return (
          <TakeHomePayStep
            incomeData={incomeData}
            onIncomeDataChange={setIncomeData}
            spouseIncomeData={spouseIncomeData}
            onSpouseIncomeDataChange={setSpouseIncomeData}
            maritalStatus={incomeData.marital_status}
            onValidationChange={setCanProceed}
          />
        );

      case 'expense_info':
        return (
          <ExpenseInfoStep
            initialData={expenseData}
            onDataChange={setExpenseData}
            onValidationChange={setCanProceed}
          />
        );

      case 'assets':
        return (
          <AssetsStep
            rows={assetsData}
            onRowsChange={setAssetsData}
            answers={assetAnswers}
            onAnswersChange={setAssetAnswers}
            part={1}
            onValidationChange={setCanProceed}
          />
        );

      case 'debts':
        return (
          <DebtsStep
            rows={debtsData}
            onRowsChange={setDebtsData}
            onValidationChange={setCanProceed}
          />
        );

      case 'contracts':
        return (
          <ContractsStep
            initialData={contractsData}
            onDataChange={setContractsData}
            onValidationChange={setCanProceed}
          />
        );

      case 'codebtors':
        return (
          <CodebtorsStep
            initialData={codebtorsData}
            onDataChange={setCodebtorsData}
            onValidationChange={setCanProceed}
          />
        );

      case 'review':
        return (
          <ReviewStep
            debtorData={debtorData}
            incomeData={incomeData}
            spouseIncomeData={spouseIncomeData}
            entries={entriesToSend(entryRows, noEntries) as IncomeEntry[] | null}
            spouseEntries={entriesToSend(spouseEntryRows, spouseNoEntries) as IncomeEntry[] | null}
            expenseData={expenseData}
            assetsData={assetsData}
            debtsData={debtsData}
            contractsData={contractsData}
            codebtorsData={codebtorsData}
            householdCount={session?.household?.family_size ?? null}
            county={county}
            onValidationChange={setCanProceed}
            completionReasons={completionErrors.map((reason) => ({
              message: reason.message,
              step: WIZARD_STEPS.find((step) => step.key === reason.step),
            }))}
            onGoToStep={moveToStep}
          />
        );

      default:
        return <div>Unknown step</div>;
    }
  };

  const wizardSteps = WIZARD_STEPS.map((step) => ({
    ...step,
    component: renderStepContent(step.key),
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
