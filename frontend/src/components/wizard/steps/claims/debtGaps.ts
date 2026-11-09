/**
 * What the Amounts Owed step still lacks, in Complete's words: a copy of D1 to D17 of the claim
 * gap table (claim_step_gaps in apps/intake/claims.py), in the same order (3c3 Task 6, R8, R19).
 * D0 (a draft remains) is the server's alone: the step confirms drafts on Continue.
 */
import { ASSET_LINES } from '../../../../constants/assetLines';
import {
  CLAIM_GAP_ADDRESS,
  CLAIM_GAP_KIND,
  CLAIM_GAP_STREET_CITY,
  DEBT_GAP_ADDRESS_NO_NAME,
  DEBT_GAP_AMOUNT,
  DEBT_GAP_AMOUNT_NO_NAME,
  DEBT_GAP_DESCRIBE,
  DEBT_GAP_HOME_LINE,
  DEBT_GAP_LIEN,
  DEBT_GAP_LIEN_OTHER,
  DEBT_GAP_NONE_BUT_LISTED,
  DEBT_GAP_NOTICE,
  DEBT_GAP_NOTICE_PARTY,
  DEBT_GAP_NO_ANSWER,
  DEBT_GAP_NO_NAME,
  DEBT_GAP_OFFSET,
  DEBT_GAP_PAYMENT,
  DEBT_GAP_PROPERTY,
  DEBT_GAP_STATUS,
  DEBT_GAP_STREET_CITY_NO_NAME,
  DEBT_GAP_WHO,
  NAMELESS_DEBT,
} from '../../../../constants/copy';
import { isBlankDebt, keptRows } from '../../../../utils/claimRows';
import { addressMissing, asksWho, claimRowName, fill, linkIsLive } from './claimNames';
import type { AssetInfo, DebtRow, WizardRow } from '../../../../types/api';

const blank = (value: string | undefined | null) => (value ?? '').trim() === '';

/** Every gap of one debt, in the table's order D3 to D17, each in the row's own name */
export function debtRowGaps(row: DebtRow, assets: WizardRow<AssetInfo>[]): string[] {
  const gaps: string[] = [];
  const nameless = blank(row.creditor_name);
  const words = { name: claimRowName(row.creditor_name, NAMELESS_DEBT) };

  if (nameless) gaps.push(DEBT_GAP_NO_NAME);
  if (blank(row.debt_type)) gaps.push(fill(CLAIM_GAP_KIND, words));
  if (!(typeof row.amount_owed === 'number' && row.amount_owed > 0)) {
    gaps.push(fill(nameless ? DEBT_GAP_AMOUNT_NO_NAME : DEBT_GAP_AMOUNT, words));
  }
  if (addressMissing(row)) {
    const sentence = row.outside_us
      ? nameless
        ? DEBT_GAP_STREET_CITY_NO_NAME
        : CLAIM_GAP_STREET_CITY
      : nameless
        ? DEBT_GAP_ADDRESS_NO_NAME
        : CLAIM_GAP_ADDRESS;
    gaps.push(fill(sentence, words));
  }

  if (row.is_secured) {
    const live = linkIsLive(row.secured_by, assets);
    // A link to a row removed on Assets reads as no link at all
    const linked = live ? assets.find((asset) => asset.id === row.secured_by) : undefined;
    if (!live) gaps.push(fill(DEBT_GAP_PROPERTY, words));
    if (blank(row.collateral_description)) gaps.push(fill(DEBT_GAP_DESCRIBE, words));
    const kinds = row.lien?.kinds ?? [];
    if (kinds.length === 0) gaps.push(fill(DEBT_GAP_LIEN, words));
    else if (kinds.includes('other') && blank(row.lien?.other)) {
      gaps.push(fill(DEBT_GAP_LIEN_OTHER, words));
    }
    if (row.monthly_payment === null || row.monthly_payment === undefined) {
      gaps.push(fill(DEBT_GAP_PAYMENT, words));
    }
    if (linked) {
      if (linked.details?.lives_here === 'yes' && !row.home_payment_line) {
        gaps.push(fill(DEBT_GAP_HOME_LINE, words));
      }
      const shape = ASSET_LINES.find((line) => line.key === linked.ab_line)?.shape;
      if (!asksWho(shape) && !row.collateral_who) gaps.push(fill(DEBT_GAP_WHO, words));
    }
  }

  if (row.claim_status === null || row.claim_status === undefined) {
    gaps.push(fill(DEBT_GAP_STATUS, words));
  }
  if (!row.is_secured && !row.offset_answer) gaps.push(fill(DEBT_GAP_OFFSET, words));
  if (row.notice_parties === null || row.notice_parties === undefined) {
    gaps.push(fill(DEBT_GAP_NOTICE, words));
  } else if (row.notice_parties.some((party) => blank(party.name) || addressMissing(party))) {
    gaps.push(fill(DEBT_GAP_NOTICE_PARTY, words));
  }
  return gaps;
}

/** The first thing the step lacks, or null: D1, D2, then the first row's first gap */
export function firstDebtGap(
  rows: DebtRow[],
  noDebts: boolean,
  assets: WizardRow<AssetInfo>[]
): string | null {
  const kept = keptRows(rows, isBlankDebt);
  if (kept.length === 0) return noDebts ? null : DEBT_GAP_NO_ANSWER;
  if (noDebts) return DEBT_GAP_NONE_BUT_LISTED;
  for (const row of kept) {
    const [first] = debtRowGaps(row, assets);
    if (first !== undefined) return first;
  }
  return null;
}
