// What the Form 122A-2 page holds while the filer answers, and how it reads and writes the server's
// body. A line 3 row, a spouse vehicle, a spouse loan and a circumstance carry a browser-only `_key`
// (a loaded row `loaded-<i>`, a new one `new-<n>` from the page's one counter, which is also a new
// spouse row's first `ref`), which `toPutBody` leaves out (F7). The spouse's rows are named by their
// `ref`, which the server gives a new row (`new-<n>` until it does); the `_key` never changes.
import type {
  MeansAnswers,
  MeansCircumstance,
  MeansDebt,
  MeansDebtAnswers,
  MeansLine3Row,
  MeansPage,
  MeansSpouseLoan,
  MeansSpouseVehicle,
  MeansTestUpdate,
  PaymentsLeft,
  YesNo,
} from '../../types/api';
import { MEANS_SPOUSE_LOAN_FROM } from '../../constants/copy';
import { debtLines, isSpouseRef, slotCandidates } from './meansRows';
import type { RowsDebt, RowsInput, RowsVehicle } from './meansRows';
import { readSpouseLoans, spouseIdentityGaps, type GapState } from './meansTestGaps';

export type KeyedLine3Row = MeansLine3Row & { _key: string };
export type KeyedCircumstance = MeansCircumstance & { _key: string };
export type KeyedSpouseVehicle = MeansSpouseVehicle & { _key: string };
export type KeyedSpouseLoan = MeansSpouseLoan & { _key: string };

export type PageAnswers = Omit<
  MeansAnswers,
  'line_3_rows' | 'line_43_circumstances' | 'spouse_vehicles' | 'spouse_loans'
> & {
  line_3_rows: KeyedLine3Row[];
  line_43_circumstances: KeyedCircumstance[];
  spouse_vehicles: KeyedSpouseVehicle[];
  spouse_loans: KeyedSpouseLoan[];
};

export type PageState = { answers: PageAnswers; debts: MeansDebt[] };

const PROPERTY_CHOICES = ['home', 'other'];

export function fromReply(page: MeansPage): PageState {
  const answers = structuredClone(page.answers);
  return {
    answers: {
      ...answers,
      line_3_rows: answers.line_3_rows.map((row, index) => ({ ...row, _key: `loaded-${index}` })),
      spouse_vehicles: answers.spouse_vehicles.map((row, index) => ({
        ...row,
        _key: `loaded-${index}`,
      })),
      spouse_loans: answers.spouse_loans.map((row, index) => ({
        ...row,
        _key: `loaded-${index}`,
      })),
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
    // Rows typed before a No stay in the page, so a mistaken No loses nothing; the server gets none
    line_3_rows:
      state.answers.line_3_answer === 'no' ? [] : state.answers.line_3_rows.map(withoutKey),
    spouse_vehicles: state.answers.spouse_vehicles.map(withoutKey),
    spouse_loans: state.answers.spouse_loans.map(withoutKey),
    // Circumstances typed before a No (or before any answer) stay in the page; the server gets none
    line_43_circumstances:
      state.answers.line_43_answer === 'yes'
        ? state.answers.line_43_circumstances.map(withoutKey)
        : [],
    debts: state.debts.map((debt) => ({ id: debt.id, ...debtAnswersOf(debt) })),
  };
}

/** The key a refused explanation is shown under */
export const explanationKey = (key: string) => `circumstance:${key}:explanation`;

/**
 * Everything the body carries above line 43, as JSON: the page compares this copy of what it last
 * read or saved with the one it holds now, to know whether line 43's arithmetic is still true of
 * what is saved. It leaves out the line 43 answer and its circumstances, so typing there changes
 * nothing here.
 */
export function aboveLine43(state: PageState): string {
  const { line_43_answer, line_43_circumstances, ...above } = toPutBody(state);
  void line_43_answer;
  void line_43_circumstances;
  return JSON.stringify(above);
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

const blankText = (text: string) => text.trim() === '';

/** The refs of the vehicles a reference may name: the filer's, and the spouse's while they count */
function liveVehicleRefs(page: MeansPage, answers: PageAnswers): Set<string> {
  const live = new Set(page.vehicles.map((vehicle) => vehicle.ref));
  if (page.married_together && answers.spouse_vehicles_answer === 'yes') {
    for (const row of answers.spouse_vehicles) live.add(row.ref);
  }
  return live;
}

/**
 * The browser's copy of `normalized_answers`' reference rules (F3, F4, F5): every `secured_by` and
 * `vehicle_choice` entry that names no live vehicle is `null`, a loan on the Amounts Owed step keeps
 * only a spouse vehicle (a filer's own `asset-` ref goes as `null`), and a spouse loan's `debt`
 * is kept only on a row answered Yes, only while that debt is still open, and only for the first
 * row naming it: a debt on any other row, a debt no longer open and a debt an earlier row names
 * all go as `null`. A typed loan (`debt` null) is never touched. Continue
 * sends this, so the server's 400 for a reference to a removed row never reaches the filer.
 */
export function withLiveRefs(page: MeansPage, state: PageState): PageState {
  const { answers } = state;
  const live = liveVehicleRefs(page, answers);
  const open = new Set(page.amounts_owed_loans.map((debt) => debt.id));
  const liveOrNull = (ref: string | null) => (ref !== null && live.has(ref) ? ref : null);
  const taken = new Set<number>();
  return {
    ...state,
    answers: {
      ...answers,
      vehicle_choice: [
        liveOrNull(answers.vehicle_choice[0]),
        liveOrNull(answers.vehicle_choice[1]),
      ],
      spouse_loans: answers.spouse_loans.map((loan) => {
        const securedBy = loan.secured_by;
        let kept: string | null = null;
        if (securedBy === 'home' || securedBy === 'other') kept = securedBy;
        else if (securedBy !== null && live.has(securedBy)) {
          kept = loan.on_amounts_owed === 'yes' && !isSpouseRef(securedBy) ? null : securedBy;
        }
        // a debt is kept only on a Yes row, only while open, and only for the first row naming it
        let debt: number | null = null;
        if (
          loan.on_amounts_owed === 'yes' &&
          loan.debt !== null &&
          open.has(loan.debt) &&
          !taken.has(loan.debt)
        ) {
          debt = loan.debt;
          taken.add(debt);
        }
        return { ...loan, secured_by: kept, debt };
      }),
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
export function rowsInputOf(page: MeansPage, shown: PageState): RowsInput {
  const state = withLiveRefs(page, shown);
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
export function gapStateOf(page: MeansPage, shown: PageState): GapState {
  const state = withLiveRefs(page, shown);
  const vehicles = vehicleRowsOf(page, state);
  const vehicleRefs = vehicles.map((vehicle) => vehicle.ref);
  const loans = readLoans(page, state, vehicleRefs);
  // The helper `meansTestGaps` reads each loan's identity with, so the two can't disagree
  const identityGaps = spouseIdentityGaps(loans, vehicleRefs);
  const named = new Map(page.amounts_owed_loans.map((debt) => [debt.id, debt.creditor]));
  const rows = rowsInputOf(page, shown);
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

/** What line 11 lists: the filer's vehicles, then the spouse's described rows while they count */
export function line11Vehicles(
  page: MeansPage,
  answers: PageAnswers
): { ref: string; name: string; spouse: boolean }[] {
  const filer = page.vehicles.map((vehicle) => ({
    ref: vehicle.ref,
    name: vehicle.name,
    spouse: false,
  }));
  if (!page.married_together || answers.spouse_vehicles_answer !== 'yes') return filer;
  const spouse = answers.spouse_vehicles
    .filter((row) => !blankText(row.description))
    .map((row) => ({ ref: row.ref, name: row.description, spouse: true }));
  return [...filer, ...spouse];
}

/**
 * Each of the spouse's loans as the server reads it (its references live), the creditor it shows
 * (the named debt's for an Amounts Owed row), what secures it in words, and whether its identity is
 * given: only such a loan gets its own questions.
 */
export function spouseLoanViews(
  page: MeansPage,
  state: PageState
): { loan: KeyedSpouseLoan; creditor: string; property: string; identityGiven: boolean }[] {
  const { answers } = withLiveRefs(page, state);
  const together = page.married_together && answers.spouse_loans_answer === 'yes';
  if (!together) return [];
  const vehicleRefs = [...liveVehicleRefs(page, answers)];
  const read = readSpouseLoans(answers.spouse_loans, vehicleRefs);
  const identity = spouseIdentityGaps(read, vehicleRefs);
  const debtNames = new Map(page.amounts_owed_loans.map((debt) => [debt.id, debt.creditor]));
  const vehicleNames = new Map(line11Vehicles(page, answers).map((v) => [v.ref, v.name]));
  return read.map((row, index) => {
    const loan: KeyedSpouseLoan = { ...row, _key: answers.spouse_loans[index]._key };
    const named = loan.secured_by !== null ? vehicleNames.get(loan.secured_by) : undefined;
    const creditor =
      loan.on_amounts_owed === 'yes' && loan.debt !== null
        ? (debtNames.get(loan.debt) ?? '')
        : loan.creditor;
    return {
      loan,
      creditor,
      property:
        named ??
        (loan.secured_by !== null && PROPERTY_CHOICES.includes(loan.secured_by)
          ? loan.property
          : ''),
      identityGiven: !identity[index],
    };
  });
}

/** The name every question of a debt takes: `means_debt_<pk>` or a spouse loan's own */
export function debtPrefix(ref: string): string {
  if (ref.startsWith('debt-')) return `means_debt_${ref.replace('debt-', '')}`;
  if (ref.startsWith('new-')) return `means_spouse_debt_new_${ref.replace('new-', '')}`;
  return `means_spouse_debt_${ref.replace('spouse-', '')}`;
}

export function spouseLoanHeading(creditor: string): string {
  return MEANS_SPOUSE_LOAN_FROM.split('{name}').join(creditor);
}
