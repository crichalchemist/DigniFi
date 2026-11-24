/**
 * Which rows Your Plans asks about, the body its save sends, and the rows it still leaves open
 * (forms step 4e). Each copies the server: the rows its save keeps (R-PRUNE, 4e-R2, 4e-R23), the
 * entries IntentionAnswers takes (4e-R3, T2-H1), and intention_row_gap and lease_row_gap in
 * apps/intake/intentions.py, pinned by intentionGapCases.json.
 */
import { rowList } from '../../../../constants/claimTextLimits';
import {
  INTENTION_GAP_EXPLAIN,
  INTENTION_GAP_NONE,
  INTENTION_GAP_UNDECIDED,
  LEASE_GAP_NONE,
  LEASE_GAP_UNDECIDED,
  NAMELESS_CONTRACT,
  NAMELESS_DEBT,
} from '../../../../constants/copy';
import { claimRowName, fill } from '../claims/claimNames';
import type {
  Assumed,
  ContractRow,
  DebtRow,
  Intention,
  IntentionAnswers,
} from '../../../../types/api';

type SecuredEntry = { intention?: Intention; explain?: string };
type LeaseEntry = { assumed?: Assumed };

// Form 108 Part 1's four choices and Part 2's two answers: a row with one of them is chosen
const CHOSEN_INTENTIONS: readonly string[] = [
  'surrender',
  'retain_redeem',
  'retain_reaffirm',
  'retain_explain',
];
const CHOSEN_ASSUMED: readonly string[] = ['no', 'yes'];

/** Part 1's rows: each confirmed secured debt the server holds (a saved, non-draft row) */
export function securedPlanRows(debts: DebtRow[]): DebtRow[] {
  return debts.filter((debt) => debt.id != null && debt.is_secured === true && !debt.is_draft);
}

/** Part 2's rows: each saved lease of personal property (any lease but residential) */
export function leasePlanRows(contracts: ContractRow[]): ContractRow[] {
  return contracts.filter((contract) => contract.id != null && rowList(contract) === 'leases');
}

/**
 * The step's save: an entry for each shown row holding an answer, keyed by its id, with only the
 * keys that hold one (words not blank, as typed), so the body built from loaded answers is the one
 * built from the same answers typed and a visit sends nothing. Ids no longer shown are left out,
 * so the server drops them. With no row shown nothing is sent (null).
 */
export function plansBody(
  answers: IntentionAnswers,
  secured: DebtRow[],
  leases: ContractRow[]
): { secured: Record<string, SecuredEntry>; leases: Record<string, LeaseEntry> } | null {
  if (secured.length === 0 && leases.length === 0) return null;
  const body = {
    secured: {} as Record<string, SecuredEntry>,
    leases: {} as Record<string, LeaseEntry>,
  };
  for (const row of secured) {
    const id = String(row.id);
    const stored = answers.secured?.[id] ?? {};
    const entry: SecuredEntry = {};
    if (stored.intention) entry.intention = stored.intention;
    if (typeof stored.explain === 'string' && stored.explain.trim() !== '') {
      entry.explain = stored.explain;
    }
    if (Object.keys(entry).length > 0) body.secured[id] = entry;
  }
  for (const row of leases) {
    const id = String(row.id);
    const assumed = answers.leases?.[id]?.assumed;
    if (assumed) body.leases[id] = { assumed };
  }
  return body;
}

/** A secured row's open choice in the server's words, or null (intention_row_gap) */
export function intentionRowGap(name: string, entry: SecuredEntry): string | null {
  const intention = entry.intention;
  if (intention === 'undecided') return fill(INTENTION_GAP_UNDECIDED, { name });
  if (intention === 'retain_explain' && (entry.explain ?? '').trim() === '') {
    return fill(INTENTION_GAP_EXPLAIN, { name });
  }
  if (intention !== undefined && CHOSEN_INTENTIONS.includes(intention)) return null;
  return fill(INTENTION_GAP_NONE, { name });
}

/** A lease's open answer in the server's words, or null (lease_row_gap) */
export function leaseRowGap(name: string, entry: LeaseEntry): string | null {
  const assumed = entry.assumed;
  if (assumed === 'undecided') return fill(LEASE_GAP_UNDECIDED, { name });
  if (assumed !== undefined && CHOSEN_ASSUMED.includes(assumed)) return null;
  return fill(LEASE_GAP_NONE, { name });
}

/** Each open row's sentence, in the step's order: Part 1's rows, then Part 2's */
export function openPlanRows(
  answers: IntentionAnswers,
  secured: DebtRow[],
  leases: ContractRow[]
): string[] {
  const sentences = [
    ...secured.map((row) =>
      intentionRowGap(
        claimRowName(row.creditor_name, NAMELESS_DEBT),
        answers.secured?.[String(row.id)] ?? {}
      )
    ),
    ...leases.map((row) =>
      leaseRowGap(
        claimRowName(row.counterparty_name, NAMELESS_CONTRACT),
        answers.leases?.[String(row.id)] ?? {}
      )
    ),
  ];
  return sentences.filter((sentence): sentence is string => sentence !== null);
}
