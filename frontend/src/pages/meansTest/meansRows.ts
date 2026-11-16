// The browser's copy of `slot_candidates` and `debt_lines` (apps/eligibility/means_lines.py), the
// server's rules to the letter. `null` stands for the server's MISSING. A case file runs on both
// sides (meansRowsCases.json). One difference: a spouse row the page hasn't saved yet (`new-<n>`)
// counts as the spouse's, as `spouse-<id>` does, since the server never sees a `new-` ref.
import type { YesNo } from '../../types/api';
import { cents } from './money';

export type RowsVehicle = { ref: string; leased: boolean | null; claimed: boolean | null };

export type RowsDebt = {
  ref: string;
  secured_by: string | null;
  on_home: boolean;
  placed: boolean;
  monthly_payment: string | null;
  payments_left: number | null;
  payment_changes: YesNo | null;
  total_60_months: string | null;
};

export type RowsInput = {
  marital_status: string | null;
  spouse_vehicles_answer: YesNo | null;
  spouse_loans_answer: YesNo | null;
  vehicles: RowsVehicle[];
  debts: RowsDebt[];
  vehicle_choice: [string, string] | null;
};

export function isSpouseRef(ref: string): boolean {
  return ref.startsWith('spouse-') || ref.startsWith('new-');
}

/** What the debt takes in the 60 months after filing, in cents; null while its inputs are missing. */
export function sixtyMonthTotalCents(debt: RowsDebt): bigint | null {
  if (debt.payment_changes === 'yes' && debt.total_60_months !== null) {
    return cents(debt.total_60_months);
  }
  if (
    debt.payment_changes === 'no' &&
    debt.payments_left !== null &&
    debt.monthly_payment !== null
  ) {
    return BigInt(Math.min(debt.payments_left, 60)) * cents(debt.monthly_payment);
  }
  return null;
}

// Under married_together, the spouse's rows are unknown with no answer, or Yes with no spouse row.
function spouseUnknown(input: RowsInput, answer: YesNo | null, refs: string[]): boolean {
  if (input.marital_status !== 'married_together') return false;
  return answer === null || (answer === 'yes' && !refs.some(isSpouseRef));
}

function slotsAreWaiting(input: RowsInput): boolean {
  const vehiclesUnknown = spouseUnknown(
    input,
    input.spouse_vehicles_answer,
    input.vehicles.map((vehicle) => vehicle.ref)
  );
  const loansUnknown =
    spouseUnknown(
      input,
      input.spouse_loans_answer,
      input.debts.map((debt) => debt.ref)
    ) || input.debts.some((debt) => !debt.placed);
  return vehiclesUnknown || loansUnknown;
}

/** The claimed vehicles that can take Vehicle 1 or 2, in order, or null while the slots wait. */
export function slotCandidates(input: RowsInput): string[] | null {
  if (slotsAreWaiting(input)) return null;
  if (input.vehicles.some((vehicle) => vehicle.claimed === null)) return null;
  const claimed = input.vehicles.filter((vehicle) => vehicle.claimed);
  if (claimed.some((vehicle) => vehicle.leased === null)) return null;
  return claimed
    .filter((vehicle) => {
      // A loan with 0 payments left and no larger final payment takes no slot (H57)
      const somethingDue = input.debts
        .filter((debt) => debt.secured_by === vehicle.ref)
        .some((debt) => {
          const total = sixtyMonthTotalCents(debt);
          return total === null || total > 0n;
        });
      return vehicle.leased || somethingDue;
    })
    .map((vehicle) => vehicle.ref);
}

// Vehicle 1 and Vehicle 2 as refs (null for an empty slot), or null while they are unknown.
function vehicleSlots(input: RowsInput): [string | null, string | null] | null {
  const candidates = slotCandidates(input);
  if (candidates === null) return null;
  if (candidates.length <= 2) return [candidates[0] ?? null, candidates[1] ?? null];
  if (input.vehicle_choice === null) return null;
  const [first, second] = input.vehicle_choice.map((ref) =>
    candidates.includes(ref) ? ref : null
  );
  if (first === null || second === null || first === second) return null;
  return [first, second];
}

/** Each secured debt's line by ref: 9b, 13b, 13e or 33d, or null while it waits. */
export function debtLines(input: RowsInput): Record<string, string | null> {
  const slots = vehicleSlots(input);
  const vehicleRefs = new Set(input.vehicles.map((vehicle) => vehicle.ref));
  const lines: Record<string, string | null> = {};
  for (const debt of input.debts) {
    const named = debt.secured_by;
    if (!debt.placed) lines[debt.ref] = null;
    else if (debt.on_home) lines[debt.ref] = '9b';
    else if (slots === null && named !== null && vehicleRefs.has(named)) lines[debt.ref] = null;
    else if (slots !== null && named !== null && named === slots[0]) lines[debt.ref] = '13b';
    else if (slots !== null && named !== null && named === slots[1]) lines[debt.ref] = '13e';
    else lines[debt.ref] = '33d';
  }
  return lines;
}
