// The browser's copy of `means_test_gaps` (apps/intake/means_test.py): the same rules, order and
// sentences. test_means_test_copy.py pins the sentences to the server's. The page's order (R7) is
// the order of the pieces below. Before its rules, each spouse loan is read as the server's
// `normalized_answers` reads it, so a stale reference is an unanswered question, never a value.
import {
  MEANS_GAP_AMOUNT,
  MEANS_GAP_CURE,
  MEANS_GAP_LINE_15,
  MEANS_GAP_LINE_15_AMOUNT,
  MEANS_GAP_LINE_15_CAP,
  MEANS_GAP_LINE_25_ACTUAL,
  MEANS_GAP_LINE_25_AMOUNTS,
  MEANS_GAP_LINE_25_SPENDS,
  MEANS_GAP_LINE_3,
  MEANS_GAP_LINE_30_CAP,
  MEANS_GAP_LINE_30_CAP_ONE,
  MEANS_GAP_LINE_3_NO_ROW,
  MEANS_GAP_LINE_3_ROW,
  MEANS_GAP_LINE_34,
  MEANS_GAP_LINE_36,
  MEANS_GAP_LINE_36_PAYMENT,
  MEANS_GAP_LINE_43,
  MEANS_GAP_LINE_43_AMOUNT,
  MEANS_GAP_LINE_43_EXPLANATION,
  MEANS_GAP_LINE_43_NONE,
  MEANS_GAP_OPT_IN,
  MEANS_GAP_OPT_IN_AMOUNT,
  MEANS_GAP_PAYMENTS_LEFT,
  MEANS_GAP_PAYMENT_CHANGES,
  MEANS_GAP_SIXTY_MONTH_TOTAL,
  MEANS_GAP_SPOUSE_LOANS,
  MEANS_GAP_SPOUSE_LOANS_NO_ROW,
  MEANS_GAP_SPOUSE_LOAN_CREDITOR,
  MEANS_GAP_SPOUSE_LOAN_ON_AMOUNTS_OWED,
  MEANS_GAP_SPOUSE_LOAN_PAYMENT,
  MEANS_GAP_SPOUSE_LOAN_PROPERTY,
  MEANS_GAP_SPOUSE_LOAN_SECURED_BY,
  MEANS_GAP_SPOUSE_LOAN_WHICH,
  MEANS_GAP_SPOUSE_VEHICLES,
  MEANS_GAP_SPOUSE_VEHICLES_NO_ROW,
  MEANS_GAP_SPOUSE_VEHICLE_DESCRIBE,
  MEANS_GAP_SPOUSE_VEHICLE_LEASED,
  MEANS_GAP_SUPPORT,
  MEANS_GAP_TAXES,
  MEANS_GAP_VEHICLE,
  MEANS_GAP_VEHICLE_CHOICE,
} from '../../constants/copy';
import type { MeansAnswers, MeansDebtAnswers, MeansSpouseLoan, YesNo } from '../../types/api';
import { isSpouseRef } from './meansRows';
import { cents, dollars } from './money';

export type GapState = {
  marriedTogether: boolean;
  answers: MeansAnswers;
  /** The filer's vehicles, then, under married_together and a Yes, the spouse's rows */
  vehicles: { ref: string; name: string; claimed: YesNo | null }[];
  /** Every debt row; a spouse loan's `creditor` is already the named debt's for an Amounts Owed row */
  debts: {
    ref: string;
    creditor: string;
    answers: MeansDebtAnswers;
    spouseIdentityGap: boolean;
  }[];
  lines: Record<string, string | null>;
  candidates: string[] | null;
  lineFive: number | null;
  line15Cap: string | null;
  line30Cap: string | null;
};

const PROPERTY_CHOICES = ['home', 'other'];

const blank = (text: string | null | undefined): boolean => text == null || text.trim() === '';

function fill(sentence: string, values: Record<string, string | number>): string {
  return Object.entries(values).reduce(
    (text, [key, value]) => text.split(`{${key}}`).join(String(value)),
    sentence
  );
}

// `normalized_answers`' reading of the spouse loans (F3, F4): `secured_by` stays "home" or "other",
// a vehicle ref stays only while it names a vehicle of `vehicles` and, on a row that is on the
// Amounts Owed step, only a live spouse vehicle; a debt an earlier row already names reads null.
export function readSpouseLoans(
  loans: MeansSpouseLoan[],
  vehicleRefs: string[]
): MeansSpouseLoan[] {
  const live = new Set(vehicleRefs);
  const taken = new Set<number>();
  return loans.map((row) => {
    const loan = { ...row };
    const onList = loan.on_amounts_owed === 'yes';
    if (onList && loan.debt !== null && !taken.has(loan.debt)) taken.add(loan.debt);
    else loan.debt = null;
    const securedBy = loan.secured_by;
    if (securedBy !== null && !PROPERTY_CHOICES.includes(securedBy)) {
      let keeps = live.has(securedBy);
      if (onList && !isSpouseRef(securedBy)) keeps = false;
      if (!keeps) loan.secured_by = null;
    }
    return loan;
  });
}

function identityGiven(loan: MeansSpouseLoan): boolean {
  if (loan.on_amounts_owed === 'yes') return loan.debt !== null;
  if (loan.on_amounts_owed === 'no') return !blank(loan.creditor);
  return false;
}

function normalizedLoans(state: GapState): MeansSpouseLoan[] {
  return readSpouseLoans(
    state.answers.spouse_loans,
    state.vehicles.map((vehicle) => vehicle.ref)
  );
}

/**
 * Whether each spouse loan's identity is still unsaid once read as `normalized_answers` reads it
 * (a Yes naming a debt no earlier row took, a No with a creditor given). `meansTestGaps` names the
 * loan's later gaps by this same reading, so the page's grouping and the gaps agree (C10.1).
 */
export function spouseIdentityGaps(loans: MeansSpouseLoan[], vehicleRefs: string[]): boolean[] {
  return readSpouseLoans(loans, vehicleRefs).map((loan) => !identityGiven(loan));
}

function optInGaps(answers: MeansAnswers, line: number): string[] {
  const answer = answers[`line_${line}_answer` as keyof MeansAnswers] as YesNo | null;
  const amount = answers[`line_${line}_amount` as keyof MeansAnswers] as string | null;
  if (answer === null) return [fill(MEANS_GAP_OPT_IN, { n: line })];
  if (answer === 'yes' && amount === null) return [fill(MEANS_GAP_OPT_IN_AMOUNT, { n: line })];
  return [];
}

function spouseVehicleGaps(answers: MeansAnswers): string[] {
  const answer = answers.spouse_vehicles_answer;
  if (answer === null) return [MEANS_GAP_SPOUSE_VEHICLES];
  const rows = answers.spouse_vehicles;
  if (answer !== 'yes') return [];
  if (rows.length === 0) return [MEANS_GAP_SPOUSE_VEHICLES_NO_ROW];
  const gaps: string[] = [];
  if (rows.some((row) => blank(row.description))) gaps.push(MEANS_GAP_SPOUSE_VEHICLE_DESCRIBE);
  for (const row of rows) {
    if (!blank(row.description) && row.leased === null) {
      gaps.push(fill(MEANS_GAP_SPOUSE_VEHICLE_LEASED, { name: row.description }));
    }
  }
  return gaps;
}

function spouseLoanGaps(state: GapState, loans: MeansSpouseLoan[]): string[] {
  const answer = state.answers.spouse_loans_answer;
  if (answer === null) return [MEANS_GAP_SPOUSE_LOANS];
  if (answer !== 'yes') return [];
  if (loans.length === 0) return [MEANS_GAP_SPOUSE_LOANS_NO_ROW];
  const gaps: string[] = [];
  if (loans.some((row) => row.on_amounts_owed === null)) {
    gaps.push(MEANS_GAP_SPOUSE_LOAN_ON_AMOUNTS_OWED);
  }
  if (loans.some((row) => row.on_amounts_owed === 'yes' && row.debt === null)) {
    gaps.push(MEANS_GAP_SPOUSE_LOAN_WHICH);
  }
  if (loans.some((row) => row.on_amounts_owed === 'no' && blank(row.creditor))) {
    gaps.push(MEANS_GAP_SPOUSE_LOAN_CREDITOR);
  }
  for (const row of loans) {
    if (!identityGiven(row)) continue;
    const entry = state.debts.find((debt) => debt.ref === row.ref);
    const name = (entry?.creditor ?? row.creditor ?? '').trim();
    if (row.secured_by === null) {
      gaps.push(fill(MEANS_GAP_SPOUSE_LOAN_SECURED_BY, { name }));
    } else if (PROPERTY_CHOICES.includes(row.secured_by) && blank(row.property)) {
      gaps.push(fill(MEANS_GAP_SPOUSE_LOAN_PROPERTY, { name }));
    }
    if (row.payment === null) gaps.push(fill(MEANS_GAP_SPOUSE_LOAN_PAYMENT, { name }));
  }
  return gaps;
}

function vehicleGaps(state: GapState): string[] {
  const { answers } = state;
  const gaps: string[] = [];
  for (const vehicle of state.vehicles) {
    if (isSpouseRef(vehicle.ref) && blank(vehicle.name)) continue;
    if (vehicle.claimed === null) gaps.push(fill(MEANS_GAP_VEHICLE, { name: vehicle.name }));
  }
  const { candidates } = state;
  if (candidates !== null && candidates.length > 2) {
    const [first, second] = answers.vehicle_choice;
    if (
      first === null ||
      second === null ||
      !candidates.includes(first) ||
      !candidates.includes(second) ||
      first === second
    ) {
      gaps.push(MEANS_GAP_VEHICLE_CHOICE);
    }
  }
  if (state.vehicles.some((vehicle) => vehicle.claimed === 'yes')) {
    const answer = answers.line_15_answer;
    const amount = answers.line_15_amount;
    if (answer === null) gaps.push(MEANS_GAP_LINE_15);
    else if (answer === 'yes' && amount === null) gaps.push(MEANS_GAP_LINE_15_AMOUNT);
    else if (
      answer === 'yes' &&
      amount !== null &&
      state.line15Cap !== null &&
      cents(amount) > cents(state.line15Cap)
    ) {
      gaps.push(fill(MEANS_GAP_LINE_15_CAP, { amount: dollars(state.line15Cap) }));
    }
  }
  return gaps;
}

function line25Gaps(answers: MeansAnswers): string[] {
  const answer = answers.line_25_answer;
  if (answer === null) return [fill(MEANS_GAP_OPT_IN, { n: 25 })];
  if (answer !== 'yes') return [];
  const gaps: string[] = [];
  if (
    answers.line_25_health === null ||
    answers.line_25_disability === null ||
    answers.line_25_hsa === null
  ) {
    gaps.push(MEANS_GAP_LINE_25_AMOUNTS);
  }
  if (answers.line_25_spends === null) gaps.push(MEANS_GAP_LINE_25_SPENDS);
  else if (answers.line_25_spends === 'no' && answers.line_25_actual === null) {
    gaps.push(MEANS_GAP_LINE_25_ACTUAL);
  }
  return gaps;
}

function line30CapGap(state: GapState): string[] {
  const { answers, lineFive, line30Cap } = state;
  const amount = answers.line_30_amount;
  if (answers.line_30_answer !== 'yes' || amount === null || !lineFive || line30Cap === null) {
    return [];
  }
  if (cents(amount) <= cents(line30Cap)) return [];
  if (lineFive === 1) return [fill(MEANS_GAP_LINE_30_CAP_ONE, { amount: dollars(line30Cap) })];
  return [fill(MEANS_GAP_LINE_30_CAP, { amount: dollars(line30Cap), n: lineFive })];
}

function debtGaps(state: GapState): string[] {
  const { answers } = state;
  const named = state.debts.filter((debt) => !debt.spouseIdentityGap);
  const gaps: string[] = [];
  for (const debt of named) {
    const name = debt.creditor;
    const given = debt.answers;
    if (given.payments_left === null) gaps.push(fill(MEANS_GAP_PAYMENTS_LEFT, { name }));
    if (given.payment_changes === null) {
      gaps.push(fill(MEANS_GAP_PAYMENT_CHANGES, { name }));
    } else if (given.payment_changes === 'yes' && given.total_60_months === null) {
      gaps.push(fill(MEANS_GAP_SIXTY_MONTH_TOTAL, { name }));
    }
    if (state.lines[debt.ref] === '33d' && given.taxes_or_insurance === null) {
      gaps.push(fill(MEANS_GAP_TAXES, { name }));
    }
  }
  if (answers.line_34_answer === null) {
    gaps.push(MEANS_GAP_LINE_34);
  } else if (answers.line_34_answer === 'yes') {
    for (const debt of named) {
      if ((state.lines[debt.ref] ?? null) === null) continue;
      const name = debt.creditor;
      if (debt.answers.necessary_for_support === null) {
        gaps.push(fill(MEANS_GAP_SUPPORT, { name }));
      } else if (debt.answers.necessary_for_support === 'yes' && debt.answers.cure === null) {
        gaps.push(fill(MEANS_GAP_CURE, { name }));
      }
    }
  }
  return gaps;
}

function line43Gaps(answers: MeansAnswers): string[] {
  const answer = answers.line_43_answer;
  if (answer === null) return [MEANS_GAP_LINE_43];
  if (answer !== 'yes') return [];
  const rows = answers.line_43_circumstances;
  if (rows.length === 0) return [MEANS_GAP_LINE_43_NONE];
  const gaps: string[] = [];
  rows.forEach((row, index) => {
    const n = index + 1;
    if (blank(row.explanation)) gaps.push(fill(MEANS_GAP_LINE_43_EXPLANATION, { n }));
    if (row.amount === null) gaps.push(fill(MEANS_GAP_LINE_43_AMOUNT, { n }));
  });
  return gaps;
}

/** Every answer Form 122A-2 still needs, as the page's sentences, in the page's order. */
export function meansTestGaps(state: GapState): string[] {
  const { answers } = state;
  const gaps: string[] = [];
  if (state.marriedTogether) {
    const three = answers.line_3_answer;
    if (three === null) {
      gaps.push(MEANS_GAP_LINE_3);
    } else if (three === 'yes') {
      const rows = answers.line_3_rows;
      if (rows.length === 0) gaps.push(MEANS_GAP_LINE_3_NO_ROW);
      else if (rows.some((row) => blank(row.purpose) || row.amount === null)) {
        gaps.push(MEANS_GAP_LINE_3_ROW);
      }
    }
    gaps.push(...spouseVehicleGaps(answers));
    gaps.push(...spouseLoanGaps(state, normalizedLoans(state)));
  }
  gaps.push(...vehicleGaps(state));
  for (const line of [16, 17, 18, 19, 20, 21] as const) {
    if (answers[`line_${line}`] === null) gaps.push(fill(MEANS_GAP_AMOUNT, { n: line }));
  }
  gaps.push(...optInGaps(answers, 22));
  if (answers.line_23 === null) gaps.push(fill(MEANS_GAP_AMOUNT, { n: 23 }));
  gaps.push(...line25Gaps(answers));
  for (let line = 26; line <= 31; line += 1) {
    gaps.push(...optInGaps(answers, line));
    if (line === 30) gaps.push(...line30CapGap(state));
  }
  gaps.push(...debtGaps(state));
  if (answers.line_36_answer === null) gaps.push(MEANS_GAP_LINE_36);
  else if (answers.line_36_answer === 'yes' && answers.line_36_payment === null) {
    gaps.push(MEANS_GAP_LINE_36_PAYMENT);
  }
  gaps.push(...line43Gaps(answers));
  return gaps;
}

export function firstMeansGap(state: GapState): string | null {
  return meansTestGaps(state)[0] ?? null;
}
