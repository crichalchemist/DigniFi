/**
 * What the Contracts step still lacks, in Complete's words: a copy of C1 to C13 of the claim gap
 * table (claim_step_gaps in apps/intake/claims.py), in the same order (3c3 Task 6, R8).
 */
import {
  CLAIM_GAP_ADDRESS,
  CLAIM_GAP_KIND,
  CLAIM_GAP_STREET_CITY,
  CONTRACT_GAP_LEASE_KIND,
  CONTRACT_GAP_NO_ANSWER,
  CONTRACT_GAP_NO_BUT_LISTED,
  CONTRACT_GAP_NO_NAME,
  CONTRACT_GAP_OWED_DEBT,
  CONTRACT_GAP_OWES_NOW,
  CONTRACT_GAP_PAYMENT,
  CONTRACT_GAP_PURPOSE,
  CONTRACT_GAP_SAME_VEHICLE,
  CONTRACT_GAP_VEHICLE,
  CONTRACT_GAP_YES_BUT_NONE,
  NAMELESS_CONTRACT,
  NAMELESS_DEBT,
} from '../../../../constants/copy';
import { isBlankContract, keptRows } from '../../../../utils/claimRows';
import { addressMissing, claimRowName, fill, inIdOrder, linkIsLive } from './claimNames';
import type { AssetInfo, ContractRow, DebtRow, WizardRow, YesNo } from '../../../../types/api';

const blank = (value: string | undefined | null) => (value ?? '').trim() === '';

/** Every gap of one contract, in the table's order C4 to C13, each in the row's own name */
export function contractRowGaps(
  row: ContractRow,
  debts: DebtRow[],
  assets: WizardRow<AssetInfo>[]
): string[] {
  const gaps: string[] = [];
  const words = { name: claimRowName(row.counterparty_name, NAMELESS_CONTRACT) };

  if (blank(row.counterparty_name)) gaps.push(CONTRACT_GAP_NO_NAME);
  if (addressMissing(row)) {
    gaps.push(fill(row.outside_us ? CLAIM_GAP_STREET_CITY : CLAIM_GAP_ADDRESS, words));
  }
  if (blank(row.contract_type)) gaps.push(fill(CLAIM_GAP_KIND, words));
  if (blank(row.description)) gaps.push(fill(CONTRACT_GAP_PURPOSE, words));

  const isLease = row.contract_type === 'lease';
  if (isLease && (row.lease_kind === null || row.lease_kind === undefined)) {
    gaps.push(fill(CONTRACT_GAP_LEASE_KIND, words));
  }
  const isVehicle = isLease && row.lease_kind === 'vehicle';
  const vehicleLive = linkIsLive(row.vehicle_asset, assets);
  if (isVehicle && !vehicleLive) gaps.push(fill(CONTRACT_GAP_VEHICLE, words));
  if (isVehicle && (row.monthly_payment === null || row.monthly_payment === undefined)) {
    gaps.push(fill(CONTRACT_GAP_PAYMENT, words));
  }
  if (row.owes_now === null || row.owes_now === undefined) {
    gaps.push(fill(CONTRACT_GAP_OWES_NOW, words));
  }
  const debtLive = linkIsLive(row.owed_debt, debts);
  if (row.owes_now === 'yes' && !debtLive) gaps.push(fill(CONTRACT_GAP_OWED_DEBT, words));

  if (isVehicle && vehicleLive && debtLive) {
    const debt = debts.find((d) => d.id === row.owed_debt);
    if (
      debt?.is_secured === true &&
      debt.secured_by === row.vehicle_asset &&
      (row.monthly_payment ?? 0) > 0 &&
      (debt.monthly_payment ?? 0) > 0
    ) {
      gaps.push(
        fill(CONTRACT_GAP_SAME_VEHICLE, {
          ...words,
          debt: claimRowName(debt.creditor_name, NAMELESS_DEBT),
        })
      );
    }
  }
  return gaps;
}

/** The first thing the step lacks, or null: C1, C2, C3, then the first row's first gap */
export function firstContractGap(
  rows: ContractRow[],
  answer: YesNo | null,
  debts: DebtRow[],
  assets: WizardRow<AssetInfo>[]
): string | null {
  const kept = inIdOrder(keptRows(rows, isBlankContract));
  if (answer === null) return CONTRACT_GAP_NO_ANSWER;
  if (answer === 'yes' && kept.length === 0) return CONTRACT_GAP_YES_BUT_NONE;
  if (answer === 'no' && kept.length > 0) return CONTRACT_GAP_NO_BUT_LISTED;
  for (const row of kept) {
    const [first] = contractRowGaps(row, debts, assets);
    if (first !== undefined) return first;
  }
  return null;
}
