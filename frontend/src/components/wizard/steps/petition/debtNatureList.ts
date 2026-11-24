/**
 * The list beside Form 101 line 16 on Amounts Owed (4d-R16, counsel C-39): the step's rows, drafts
 * included, grouped by the kind the filer chose for each. Nothing here adds, counts or compares:
 * a total beside the question would adopt one reading of "primarily" (spec §6.6).
 */
import { DEBT_TYPE_WORDS } from '../../../../constants/claims';
import type { DebtInfo, DebtRow } from '../../../../types/api';
import { isBlankDebt, keptRows } from '../../../../utils/claimRows';

export type DebtType = DebtInfo['debt_type'];

/**
 * The rows a save keeps, by kind in DEBT_TYPE_WORDS' order, then the rows with no kind chosen
 * (kind null); a kind with no row is left out
 */
export function debtsByKind(rows: DebtRow[]): Array<{ kind: DebtType | null; rows: DebtRow[] }> {
  const kept = keptRows(rows, isBlankDebt);
  const kinds = Object.keys(DEBT_TYPE_WORDS) as DebtType[];
  const known = (row: DebtRow) => kinds.includes(row.debt_type as DebtType);
  const groups = [
    ...kinds.map((kind) => ({ kind, rows: kept.filter((row) => row.debt_type === kind) })),
    { kind: null, rows: kept.filter((row) => !known(row)) },
  ];
  return groups.filter((group) => group.rows.length > 0);
}
