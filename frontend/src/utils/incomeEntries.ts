/**
 * The Income step's businesses and rental properties as the wizard holds and sends them (3e2 spec
 * §4.2, §7.4). An entry has the server's shape plus the browser's own `_key`, which never reaches
 * the server.
 */
import { ENTRY_AMOUNT_KEYS } from '../types/api';
import type { EntryKind, IncomeEntry, WizardRow } from '../types/api';
import { hydrateAmounts } from './parseAmount';

export type EntryRow = WizardRow<IncomeEntry>;

/** The server takes at most this many entries per person */
export const MAX_ENTRIES = 10;

/** An entry the filer adds, every question unanswered */
export function newIncomeEntry(key: string): EntryRow {
  return {
    _key: key,
    kind: null,
    description: null,
    gross: null,
    expenses: null,
    current_gross: null,
    current_expenses: null,
  };
}

/** Whether the entry is saved, or the filer has answered anything on it */
export function isEntryTouched(row: EntryRow): boolean {
  return (
    row.id !== undefined ||
    [
      row.kind,
      row.description,
      row.gross,
      row.expenses,
      row.current_gross,
      row.current_expenses,
    ].some((answer) => answer != null)
  );
}

/**
 * The entry in the server's order, with null for a missing answer. Bodies and saved copies both
 * pass through it, so an id a save writes into a row doesn't make the next body differ.
 */
export function sentEntry(row: EntryRow): EntryRow {
  const sent: EntryRow = { _key: row._key };
  if (row.id !== undefined) sent.id = row.id;
  sent.kind = row.kind ?? null;
  sent.description = row.description ?? null;
  sent.gross = row.gross ?? null;
  sent.expenses = row.expenses ?? null;
  sent.current_gross = row.current_gross ?? null;
  sent.current_expenses = row.current_expenses ?? null;
  return sent;
}

/**
 * The list a save sends: every touched entry, in order. With none, `[]` only when the filer said
 * they have none, and null (unanswered) otherwise, so a save never empties a list the filer didn't.
 */
export function entriesToSend(rows: EntryRow[], noEntries: boolean): EntryRow[] | null {
  const touched = rows.filter(isEntryTouched).map(sentEntry);
  if (touched.length > 0) return touched;
  return noEntries ? [] : null;
}

/** The entries a session read carries, as rows keyed by id, their amounts as numbers */
export function hydrateEntries(entries: IncomeEntry[] | null | undefined): EntryRow[] {
  return (entries ?? []).map((entry) => ({
    _key: String(entry.id),
    ...hydrateAmounts(entry, ENTRY_AMOUNT_KEYS),
  }));
}

/** One kind's gross receipts less its operating expenses, summed over the entries. A blank is 0. */
export function kindNet(rows: EntryRow[], kind: EntryKind, current: boolean): number {
  return rows
    .filter((row) => row.kind === kind)
    .reduce((sum, row) => {
      const gross = current ? row.current_gross : row.gross;
      const expenses = current ? row.current_expenses : row.expenses;
      return sum + (gross ?? 0) - (expenses ?? 0);
    }, 0);
}

/** The net DigniFi counts: a kind's summed net, or $0.00 when it is below $0 */
export function flooredNet(rows: EntryRow[], kind: EntryKind, current: boolean): number {
  return Math.max(0, kindNet(rows, kind, current));
}
