// What the Form 122A-2 page holds while the filer answers, and how it reads and writes the server's
// body. A line 3 row and a circumstance carry a browser-only `_key` (a loaded row `loaded-<i>`, a
// new one `new-<n>` from the page's one counter), which `toPutBody` leaves out (F7). The spouse's
// rows are named by their `ref`, which the server gives a new row (`new-<n>` until it does).
import type {
  MeansAnswers,
  MeansCircumstance,
  MeansDebt,
  MeansDebtAnswers,
  MeansLine3Row,
  MeansPage,
  MeansSpouseLoan,
  MeansTestUpdate,
  PaymentsLeft,
  YesNo,
} from '../../types/api';
import { debtLines, slotCandidates } from './meansRows';
import type { RowsDebt, RowsInput, RowsVehicle } from './meansRows';
import { readSpouseLoans, spouseIdentityGaps, type GapState } from './meansTestGaps';

export type KeyedLine3Row = MeansLine3Row & { _key: string };
export type KeyedCircumstance = MeansCircumstance & { _key: string };

export type PageAnswers = Omit<MeansAnswers, 'line_3_rows' | 'line_43_circumstances'> & {
  line_3_rows: KeyedLine3Row[];
  line_43_circumstances: KeyedCircumstance[];
};

export type PageState = { answers: PageAnswers; debts: MeansDebt[] };

const PROPERTY_CHOICES = ['home', 'other'];

export function fromReply(page: MeansPage): PageState {
  const answers = structuredClone(page.answers);
  return {
    answers: {
      ...answers,
      line_3_rows: answers.line_3_rows.map((row, index) => ({ ...row, _key: `loaded-${index}` })),
      line_43_circumstances: answers.line_43_circumstances.map((row, index) => ({
        ...row,
        _key: `loaded-${index}`,
      })),
    },
    debts: structuredClone(page.debts),
  };
}

const withoutKey = <T extends { _key: string }>({ _key, ...row }: T): Omit<T, '_key'> => {
  void _key;
  return row;
};

const debtAnswersOf = (source: MeansDebtAnswers): MeansDebtAnswers => ({
  payments_left: source.payments_left,
  payment_changes: source.payment_changes,
  total_60_months: source.total_60_months,
  taxes_or_insurance: source.taxes_or_insurance,
  necessary_for_support: source.necessary_for_support,
  cure: source.cure,
});

/**
 * Every answer key (the server replaces `vehicle_claims` whole, so every claim goes, never only the
 * one just changed) and each filer debt's six answers under its id. No `_key`.
 */
export function toPutBody(state: PageState): MeansTestUpdate {
  return {
    ...state.answers,
    line_3_rows: state.answers.line_3_rows.map(withoutKey),
    line_43_circumstances: state.answers.line_43_circumstances.map(withoutKey),
    debts: state.debts.map((debt) => ({ id: debt.id, ...debtAnswersOf(debt) })),
  };
}

/**
 * The reply's spouse row refs, written by position into the rows sent (the reply lists each list's
 * rows in the order sent), and every `new-<n>` a loan's `secured_by` or the Vehicle 1 and 2 choice
 * named rewritten. A row's `ref` changes, never its `_key`; nothing else is taken from the reply,
 * so typed amounts stay as typed.
 */
export function adoptRefs(state: PageState, sent: PageState, reply: MeansPage): PageState {
  const renamed = new Map<string, string>();
  const pair = (sentRows: { ref: string }[], replyRows: { ref: string }[]) => {
    sentRows.forEach((row, index) => {
      const given = replyRows[index]?.ref;
      if (given !== undefined && given !== row.ref) renamed.set(row.ref, given);
    });
  };
  pair(sent.answers.spouse_vehicles, reply.answers.spouse_vehicles);
  pair(sent.answers.spouse_loans, reply.answers.spouse_loans);
  const rename = (ref: string) => renamed.get(ref) ?? ref;
  const renameOrNull = (ref: string | null) => (ref === null ? null : rename(ref));
  const { answers } = state;
  return {
    ...state,
    answers: {
      ...answers,
      spouse_vehicles: answers.spouse_vehicles.map((row) => ({ ...row, ref: rename(row.ref) })),
      spouse_loans: answers.spouse_loans.map((row) => ({
        ...row,
        ref: rename(row.ref),
        secured_by: renameOrNull(row.secured_by),
      })),
      vehicle_choice: [
        renameOrNull(answers.vehicle_choice[0]),
        renameOrNull(answers.vehicle_choice[1]),
      ],
    },
  };
}

const flag = (answer: YesNo | null | undefined): boolean | null =>
  answer === null || answer === undefined ? null : answer === 'yes';

const paymentsLeftNumber = (answer: PaymentsLeft | null): number | null =>
  answer === null ? null : answer === '60_or_more' ? 60 : answer;

/** The spouse's rows count only under married_together (R4), and a list only under its Yes */
function spouseRows(page: MeansPage, state: PageState) {
  const together = page.married_together;
  const { answers } = state;
  return {
    vehicles: together && answers.spouse_vehicles_answer === 'yes' ? answers.spouse_vehicles : [],
    loans: together && answers.spouse_loans_answer === 'yes' ? answers.spouse_loans : [],
  };
}

/**
 * The spouse's loans as the server reads them: a loan names an Amounts Owed debt only while that
 * debt is one of `amounts_owed_loans` (the open ones, C10.1), and the rest as `normalized_answers`
 * reads them (`readSpouseLoans`).
 */
function readLoans(page: MeansPage, state: PageState, vehicleRefs: string[]): MeansSpouseLoan[] {
  const open = new Set(page.amounts_owed_loans.map((debt) => debt.id));
  const live = spouseRows(page, state).loans.map((loan) =>
    loan.debt !== null && !open.has(loan.debt) ? { ...loan, debt: null } : loan
  );
  return readSpouseLoans(live, vehicleRefs);
}

function vehicleRowsOf(page: MeansPage, state: PageState) {
  const { answers } = state;
  const filer = page.vehicles.map((vehicle) => ({
    ref: vehicle.ref,
    name: vehicle.name,
    leased: vehicle.leased as boolean | null,
    claimed: answers.vehicle_claims[vehicle.ref] ?? null,
  }));
  const spouse = spouseRows(page, state).vehicles.map((row) => ({
    ref: row.ref,
    name: row.description,
    leased: flag(row.leased),
    claimed: row.claimed,
  }));
  return [...filer, ...spouse];
}

/** The browser's copy of Task 3's reader: the input the grouping (`debtLines`) reads */
export function rowsInputOf(page: MeansPage, state: PageState): RowsInput {
  const vehicles = vehicleRowsOf(page, state);
  const loans = readLoans(
    page,
    state,
    vehicles.map((vehicle) => vehicle.ref)
  );
  const filerDebts: RowsDebt[] = state.debts.map((debt) => ({
    ref: debt.ref,
    secured_by: debt.secured_by,
    on_home: debt.on_home,
    placed: true,
    monthly_payment: debt.monthly_payment,
    payments_left: paymentsLeftNumber(debt.payments_left),
    payment_changes: debt.payment_changes,
    total_60_months: debt.total_60_months,
  }));
  const spouseDebts: RowsDebt[] = loans.map((loan) => {
    const named = loan.secured_by !== null && !PROPERTY_CHOICES.includes(loan.secured_by);
    const onList = loan.on_amounts_owed;
    return {
      ref: loan.ref,
      secured_by: named ? loan.secured_by : null,
      on_home: loan.secured_by === 'home',
      placed:
        loan.secured_by !== null && (onList === 'no' || (onList === 'yes' && loan.debt !== null)),
      monthly_payment: loan.payment,
      payments_left: paymentsLeftNumber(loan.payments_left),
      payment_changes: loan.payment_changes,
      total_60_months: loan.total_60_months,
    };
  });
  const rows: RowsVehicle[] = vehicles.map((vehicle) => ({
    ref: vehicle.ref,
    leased: vehicle.leased,
    claimed: flag(vehicle.claimed),
  }));
  const [first, second] = state.answers.vehicle_choice;
  return {
    marital_status: page.married_together ? 'married_together' : null,
    spouse_vehicles_answer: state.answers.spouse_vehicles_answer,
    spouse_loans_answer: state.answers.spouse_loans_answer,
    vehicles: rows,
    debts: [...filerDebts, ...spouseDebts],
    vehicle_choice: first !== null && second !== null ? [first, second] : null,
  };
}

/** The browser's copy of Task 3's reader for the gaps (`meansTestGaps`) */
export function gapStateOf(page: MeansPage, state: PageState): GapState {
  const vehicles = vehicleRowsOf(page, state);
  const vehicleRefs = vehicles.map((vehicle) => vehicle.ref);
  const loans = readLoans(page, state, vehicleRefs);
  // The helper `meansTestGaps` reads each loan's identity with, so the two can't disagree
  const identityGaps = spouseIdentityGaps(loans, vehicleRefs);
  const named = new Map(page.amounts_owed_loans.map((debt) => [debt.id, debt.creditor]));
  const rows = rowsInputOf(page, state);
  const info = page.information;
  return {
    marriedTogether: page.married_together,
    answers: { ...state.answers, spouse_loans: loans },
    vehicles: vehicles.map((vehicle) => ({
      ref: vehicle.ref,
      name: vehicle.name,
      claimed: vehicle.claimed,
    })),
    debts: [
      ...state.debts.map((debt) => ({
        ref: debt.ref,
        creditor: debt.creditor,
        answers: debtAnswersOf(debt),
        spouseIdentityGap: false,
      })),
      ...loans.map((loan, index) => ({
        ref: loan.ref,
        creditor:
          loan.on_amounts_owed === 'yes' && loan.debt !== null
            ? (named.get(loan.debt) ?? '')
            : loan.creditor,
        answers: debtAnswersOf(loan),
        spouseIdentityGap: identityGaps[index],
      })),
    ],
    lines: debtLines(rows),
    candidates: slotCandidates(rows),
    lineFive: info?.line_30_people ?? null,
    line15Cap: info?.line_15_cap ?? null,
    line30Cap: info?.line_30_cap ?? null,
  };
}
