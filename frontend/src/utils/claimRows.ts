/**
 * The claim rows (amounts owed, contracts and codebtors) as the wizard holds and sends them (3c3
 * spec §7.2, plan R15, R17, R18). A row has the server's shape plus the browser's own `_`-keys,
 * which never reach the server.
 */
import type { CodebtorRow, ContractRow, DebtRow } from '../types/api';

/** A text box holding something once trimmed */
function hasText(value: unknown): boolean {
  return typeof value === 'string' && value.trim() !== '';
}

/** A pick or a stored answer: anything but null, undefined and '' */
function isPicked(value: unknown): boolean {
  return value !== null && value !== undefined && value !== '';
}

/** A list the filer answered: [] is an answer ("None of these", "No"); null is not */
function isAnsweredList(value: unknown): boolean {
  return Array.isArray(value);
}

/**
 * Whether every answer on the debt is empty. The row's id isn't an answer, and neither is the
 * pressed mark (it is no stored answer). A stored amount of 0 means "not given yet" (B29), and
 * a payment of 0 is an answer (B18).
 */
export function isBlankDebt(row: DebtRow): boolean {
  return !(
    [
      row.creditor_name,
      row.account_number,
      row.collateral_description,
      row.street_address,
      row.street_2,
      row.city,
      row.state,
      row.zip_code,
      row.date_incurred,
    ].some(hasText) ||
    [
      row.debt_type,
      row.secured_by,
      row.home_payment_line,
      row.collateral_who,
      row.offset_answer,
      row.community_debt,
    ].some(isPicked) ||
    (row.amount_owed !== undefined && row.amount_owed !== 0) ||
    typeof row.monthly_payment === 'number' ||
    isAnsweredList(row.claim_status) ||
    isAnsweredList(row.notice_parties) ||
    (row.lien?.kinds.length ?? 0) > 0 ||
    row.is_secured === true ||
    row.outside_us === true
  );
}

/** Whether every answer on the contract is empty */
export function isBlankContract(row: ContractRow): boolean {
  return !(
    [
      row.counterparty_name,
      row.description,
      row.street_address,
      row.street_2,
      row.city,
      row.state,
      row.zip_code,
    ].some(hasText) ||
    [
      row.contract_type,
      row.lease_kind,
      row.owes_now,
      row.vehicle_asset,
      row.owed_debt,
      row.monthly_payment,
    ].some(isPicked) ||
    row.outside_us === true
  );
}

/** Whether every answer on the codebtor is empty */
export function isBlankCodebtor(row: CodebtorRow): boolean {
  return !(
    [row.name, row.street_address, row.street_2, row.city, row.state, row.zip_code].some(hasText) ||
    isPicked(row.relationship) ||
    (row.links?.length ?? 0) > 0 ||
    row.outside_us === true
  );
}

/**
 * The rows a save carries: a row with an id (a save that left it out would delete it) or one that
 * isn't blank. The steps' gap functions filter with it too, so a gap never names a row the server
 * never gets.
 */
export function keptRows<T extends { id?: number }>(rows: T[], isBlank: (row: T) => boolean): T[] {
  return rows.filter((row) => row.id !== undefined || !isBlank(row));
}

/** A debt as the server takes it: a blank payment is null, since a key left out keeps the old figure */
export type SentDebt = Omit<DebtRow, 'monthly_payment' | 'debt_type'> & {
  monthly_payment: number | null;
  debt_type: DebtRow['debt_type'] | '';
};

/**
 * The debt a save carries: the browser-only mark gone, a blank amount as 0 (B29), a blank
 * payment as null and a blank type as '' (undefined would drop out of the JSON and the server
 * would keep the old type). Deleted by key, as `withoutKey` does, not destructured away.
 */
export function sentDebt(row: DebtRow): SentDebt {
  const sent: Partial<DebtRow> = { ...row };
  delete sent._securedPressed;
  return {
    ...(sent as DebtRow),
    amount_owed: row.amount_owed ?? 0,
    monthly_payment: row.monthly_payment ?? null,
    debt_type: row.debt_type ?? '',
  };
}

/**
 * Step 6's `no_debts`: true only while "I have no amounts owed" is pressed and no row is kept,
 * and null otherwise (never false, which the server refuses).
 */
export function noDebtsToSend(kept: unknown[], pressed: boolean): true | null {
  return pressed && kept.length === 0 ? true : null;
}
