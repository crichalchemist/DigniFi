import { describe, it, expect } from 'vitest';
import { debtName, firstMeansGap, meansTestGaps, type GapState } from '../meansTestGaps';
import type { MeansAnswers, MeansDebtAnswers, MeansSpouseLoan } from '../../../types/api';

// The browser's copy of apps/intake/tests/test_means_test_gaps.py, case for case.

const NO_DEBT_ANSWERS: MeansDebtAnswers = {
  payments_left: null,
  payment_changes: null,
  total_60_months: null,
  taxes_or_insurance: null,
  necessary_for_support: null,
  cure: null,
};

const EMPTY_ANSWERS: MeansAnswers = {
  line_3_answer: null,
  line_3_rows: [],
  spouse_vehicles_answer: null,
  spouse_vehicles: [],
  spouse_loans_answer: null,
  spouse_loans: [],
  vehicle_claims: {},
  vehicle_choice: [null, null],
  line_15_answer: null,
  line_15_amount: null,
  line_16: null,
  line_17: null,
  line_18: null,
  line_19: null,
  line_20: null,
  line_21: null,
  line_22_answer: null,
  line_22_amount: null,
  line_23: null,
  line_25_answer: null,
  line_25_health: null,
  line_25_disability: null,
  line_25_hsa: null,
  line_25_spends: null,
  line_25_actual: null,
  line_26_answer: null,
  line_26_amount: null,
  line_27_answer: null,
  line_27_amount: null,
  line_28_answer: null,
  line_28_amount: null,
  line_29_answer: null,
  line_29_amount: null,
  line_30_answer: null,
  line_30_amount: null,
  line_31_answer: null,
  line_31_amount: null,
  line_34_answer: null,
  line_36_answer: null,
  line_36_payment: null,
  line_43_answer: null,
  line_43_circumstances: [],
};

const PRIYAS_ANSWERS: MeansAnswers = {
  ...EMPTY_ANSWERS,
  line_3_answer: 'yes',
  line_3_rows: [{ purpose: 'His payroll taxes withheld from his pay', amount: '250.00' }],
  spouse_vehicles_answer: 'no',
  spouse_loans_answer: 'no',
  vehicle_claims: { 'asset-1': 'yes' },
  line_15_answer: 'no',
  line_16: '2300.00',
  line_17: '0.00',
  line_18: '120.00',
  line_19: '0.00',
  line_20: '0.00',
  line_21: '1200.00',
  line_22_answer: 'no',
  line_23: '0.00',
  line_25_answer: 'yes',
  line_25_health: '620.00',
  line_25_disability: '180.00',
  line_25_hsa: '0.00',
  line_25_spends: 'yes',
  line_26_answer: 'no',
  line_27_answer: 'no',
  line_28_answer: 'no',
  line_29_answer: 'no',
  line_30_answer: 'no',
  line_31_answer: 'yes',
  line_31_amount: '50.00',
  line_34_answer: 'no',
  line_36_answer: 'yes',
  line_36_payment: '1400.00',
  line_43_answer: 'no',
};

const CRV = { ref: 'asset-1', name: 'Honda CR-V EX 2021', claimed: 'yes' as const };

const KESTREL = {
  ref: 'debt-1',
  creditor: 'Kestrel Auto Finance',
  answers: {
    ...NO_DEBT_ANSWERS,
    payments_left: 37,
    payment_changes: 'no' as const,
  },
  spouseIdentityGap: false,
};

const PRIYA_STATE: GapState = {
  marriedTogether: true,
  answers: PRIYAS_ANSWERS,
  vehicles: [CRV],
  debts: [KESTREL],
  lines: { 'debt-1': '13b' },
  candidates: ['asset-1'],
  lineFive: 4,
  line15Cap: '220.00',
  line30Cap: '76.00',
};

function gapsOf(state: Partial<GapState> = {}, over: Partial<MeansAnswers> = {}): string[] {
  return meansTestGaps({
    ...PRIYA_STATE,
    ...state,
    answers: { ...PRIYAS_ANSWERS, ...over },
  });
}

describe('the Form 122A-2 page gaps', () => {
  it("Priya's answers leave no gap", () => {
    expect(meansTestGaps(PRIYA_STATE)).toEqual([]);
    expect(firstMeansGap(PRIYA_STATE)).toBeNull();
  });

  it.each<[string, Partial<MeansAnswers>, string]>([
    ['line 3', { line_3_answer: null }, "Answer line 3, about your spouse's income."],
    [
      'line 3 rows',
      { line_3_rows: [] },
      "Add each use of your spouse's income on line 3, or change the answer to No.",
    ],
    [
      'spouse vehicles',
      { spouse_vehicles_answer: null },
      "Answer whether your spouse has a vehicle that isn't on your property list.",
    ],
    [
      'spouse vehicles with no row',
      { spouse_vehicles_answer: 'yes', spouse_vehicles: [] },
      "Add each of your spouse's vehicles, or change the answer to No.",
    ],
    [
      'spouse loans',
      { spouse_loans_answer: null },
      'Answer whether your spouse owes a loan on your home, a vehicle or other property.',
    ],
    [
      'spouse loans with no row',
      { spouse_loans_answer: 'yes', spouse_loans: [] },
      "Add each of your spouse's loans, or change the answer to No.",
    ],
    ['line 15', { line_15_answer: null }, 'Answer the question on line 15.'],
    [
      'line 15 amount',
      { line_15_answer: 'yes', line_15_amount: null },
      'Enter the amount for line 15.',
    ],
    ['line 16', { line_16: null }, 'Enter the amount for line 16. Enter 0 if you have none.'],
    ['line 17', { line_17: null }, 'Enter the amount for line 17. Enter 0 if you have none.'],
    ['line 18', { line_18: null }, 'Enter the amount for line 18. Enter 0 if you have none.'],
    ['line 19', { line_19: null }, 'Enter the amount for line 19. Enter 0 if you have none.'],
    ['line 20', { line_20: null }, 'Enter the amount for line 20. Enter 0 if you have none.'],
    ['line 21', { line_21: null }, 'Enter the amount for line 21. Enter 0 if you have none.'],
    ['line 23', { line_23: null }, 'Enter the amount for line 23. Enter 0 if you have none.'],
    ['line 22', { line_22_answer: null }, 'Answer line 22.'],
    [
      'line 22 amount',
      { line_22_answer: 'yes', line_22_amount: null },
      'Enter the amount for line 22.',
    ],
    ['line 25', { line_25_answer: null }, 'Answer line 25.'],
    ['line 25 amounts', { line_25_hsa: null }, 'Enter the three amounts on line 25.'],
    [
      'line 25 spends',
      { line_25_spends: null },
      'Answer whether you actually spend the line 25 total.',
    ],
    [
      'line 25 actual',
      { line_25_spends: 'no', line_25_actual: null },
      'Enter how much you actually spend, on line 25.',
    ],
    ['line 26', { line_26_answer: null }, 'Answer line 26.'],
    [
      'line 31 amount',
      { line_31_answer: 'yes', line_31_amount: null },
      'Enter the amount for line 31.',
    ],
    [
      'line 34',
      { line_34_answer: null },
      'Answer line 34, about debts secured by property you need for support.',
    ],
    ['line 36', { line_36_answer: null }, 'Answer line 36.'],
    [
      'line 36 payment',
      { line_36_payment: null },
      'Enter the projected monthly plan payment on line 36.',
    ],
    ['line 43', { line_43_answer: null }, 'Answer the question on line 43.'],
    [
      'line 43 with no circumstance',
      { line_43_answer: 'yes', line_43_circumstances: [] },
      'Add each special circumstance on line 43, or change the answer to No.',
    ],
  ])('a missing %s is one gap in the pages words', (_name, over, sentence) => {
    expect(gapsOf({}, over)).toEqual([sentence]);
  });

  it.each([
    [[{ purpose: '  ', amount: '5.00' }]],
    [[{ purpose: 'Tax debt', amount: null }]],
    [
      [
        { purpose: '', amount: null },
        { purpose: 'x', amount: null },
      ],
    ],
  ])('a line 3 row with no purpose or amount is one gap', (rows) => {
    expect(gapsOf({}, { line_3_rows: rows })).toEqual([
      "Enter what your spouse's income was used for, and the amount, on each row of line 3.",
    ]);
  });

  it('line 15 above its cap is a gap and at it is not', () => {
    expect(gapsOf({}, { line_15_answer: 'yes', line_15_amount: '220.01' })).toEqual([
      "Line 15 can't be more than $220.00, the IRS amount for public transportation.",
    ]);
    expect(gapsOf({}, { line_15_answer: 'yes', line_15_amount: '220.00' })).toEqual([]);
  });

  it('line 15 is asked only while a vehicle is claimed', () => {
    const unclaimed = { vehicles: [{ ...CRV, claimed: 'no' as const }], debts: [] };
    expect(gapsOf(unclaimed, { line_15_answer: null })).toEqual([]);
  });

  it('an unanswered vehicle claim names the vehicle', () => {
    const unanswered = { vehicles: [{ ...CRV, claimed: null }] };
    expect(gapsOf(unanswered, { line_15_answer: null })).toEqual([
      'Answer whether you claim an expense for Honda CR-V EX 2021.',
    ]);
  });

  it('line 30 above its cap is a gap and at it is not', () => {
    const cap =
      "Line 30 can't be more than $76.00, which is 5% of the IRS food and clothing amounts for 4 people.";
    expect(gapsOf({}, { line_30_answer: 'yes', line_30_amount: '76.01' })).toEqual([cap]);
    expect(gapsOf({}, { line_30_answer: 'yes', line_30_amount: '76.00' })).toEqual([]);
  });

  it('a household of one reads 1 person in the line 30 cap gap', () => {
    const gaps = gapsOf(
      { lineFive: 1, line30Cap: '30.00' },
      { line_30_answer: 'yes', line_30_amount: '30.01' }
    );
    expect(gaps).toEqual([
      "Line 30 can't be more than $30.00, which is 5% of the IRS food and clothing amounts for 1 person.",
    ]);
    expect(gaps.join(' ')).not.toContain('1 people');
  });

  it('a household of two reads 2 people and its own cap in the line 30 cap gap', () => {
    const gaps = gapsOf(
      { lineFive: 2, line30Cap: '53.00' },
      { line_30_answer: 'yes', line_30_amount: '53.01' }
    );
    expect(gaps).toEqual([
      "Line 30 can't be more than $53.00, which is 5% of the IRS food and clothing amounts for 2 people.",
    ]);
  });

  it('line 30 waits for the household before it has a cap', () => {
    const unknown = { lineFive: null, line30Cap: null };
    expect(gapsOf(unknown, { line_30_answer: 'yes', line_30_amount: '9999.00' })).toEqual([]);
  });

  it('under line 34s Yes a debt answered No asks no cure and an unanswered one is a gap', () => {
    const under = (changes: Partial<MeansDebtAnswers>) =>
      gapsOf(
        { debts: [{ ...KESTREL, answers: { ...KESTREL.answers, ...changes } }] },
        { line_34_answer: 'yes' }
      );
    expect(under({ necessary_for_support: 'no' })).toEqual([]);
    expect(under({ necessary_for_support: null })).toEqual([
      'Say if your debt to Kestrel Auto Finance is secured by property you need for support.',
    ]);
    expect(under({ necessary_for_support: 'yes', cure: null })).toEqual([
      'Enter the cure amount for Kestrel Auto Finance. Enter 0 if there is none.',
    ]);
    expect(under({ necessary_for_support: 'yes', cure: '0.00' })).toEqual([]);
  });

  it("each debt's own questions are gaps named by creditor", () => {
    const debtGaps = (changes: Partial<MeansDebtAnswers>) =>
      gapsOf({ debts: [{ ...KESTREL, answers: { ...KESTREL.answers, ...changes } }] });
    expect(debtGaps({ payments_left: null })).toEqual([
      'Enter how many payments you have left to Kestrel Auto Finance.',
    ]);
    expect(debtGaps({ payment_changes: null })).toEqual([
      'Answer whether your payment to Kestrel Auto Finance will change.',
    ]);
    expect(debtGaps({ payment_changes: 'yes', total_60_months: null })).toEqual([
      'Enter the total you will owe Kestrel Auto Finance in the 60 months after you file.',
    ]);
  });

  it('a gap names a debt with no creditor as one amount owed', () => {
    const gaps = gapsOf({
      debts: [{ ...KESTREL, creditor: '', answers: { ...KESTREL.answers, payments_left: null } }],
    });
    // the same words the server's claim_row_name gives (an empty name is never a sentence's)
    expect(gaps).toEqual([`Enter how many payments you have left to ${debtName('')}.`]);
    expect(gaps[0]).toBe('Enter how many payments you have left to one amount owed.');
  });

  it('a creditor typed with replacement patterns reads as typed in its gap sentence', () => {
    const creditor = "Demo $& $' Credit";
    const gaps = gapsOf({
      debts: [{ ...KESTREL, creditor, answers: { ...KESTREL.answers, payments_left: null } }],
    });
    expect(gaps).toEqual([`Enter how many payments you have left to ${creditor}.`]);
  });

  it('the taxes question is asked only of a line 33d debt', () => {
    const unlinked = {
      ref: 'debt-2',
      creditor: 'Demo Furniture Lender',
      answers: { ...NO_DEBT_ANSWERS, payments_left: 12, payment_changes: 'no' as const },
      spouseIdentityGap: false,
    };
    expect(
      gapsOf({ debts: [KESTREL, unlinked], lines: { 'debt-1': '13b', 'debt-2': '33d' } })
    ).toEqual(['Say if the payment to Demo Furniture Lender pays for taxes or insurance too.']);
    // Kestrel is on a vehicle that takes line 13b, so its taxes answer is never asked
    expect(gapsOf({ debts: [KESTREL] })).toEqual([]);
  });

  it.each(['', '   ', ' \n  \n'])('an explanation of spaces and line breaks is a gap', (text) => {
    const rows = [
      { happened: '', change: '', choices: '', papers: '', explanation: text, amount: '10.00' },
    ];
    expect(gapsOf({}, { line_43_answer: 'yes', line_43_circumstances: rows })).toEqual([
      'Give the explanation for circumstance 1 on line 43.',
    ]);
  });

  it('a missing circumstance amount names its number', () => {
    const base = { happened: '', change: '', choices: '', papers: '' };
    const rows = [
      { ...base, explanation: 'A', amount: '10.00' },
      { ...base, explanation: 'B', amount: null },
    ];
    expect(gapsOf({}, { line_43_answer: 'yes', line_43_circumstances: rows })).toEqual([
      'Enter the average monthly amount for circumstance 2 on line 43. Enter 0 if there is none.',
    ]);
  });
});

function loan(number: number, over: Partial<MeansSpouseLoan> = {}): MeansSpouseLoan {
  return {
    ref: `spouse-${number}`,
    on_amounts_owed: 'no',
    debt: null,
    creditor: `Demo Lender ${number}`,
    secured_by: 'home',
    property: 'A Demo house',
    payment: '100.00',
    ...NO_DEBT_ANSWERS,
    payments_left: 10,
    payment_changes: 'no',
    ...over,
  };
}

function loanDebt(
  number: number,
  creditor: string,
  identityGap: boolean
): GapState['debts'][number] {
  return {
    ref: `spouse-${number}`,
    creditor,
    answers: { ...NO_DEBT_ANSWERS, payments_left: 10, payment_changes: 'no' },
    spouseIdentityGap: identityGap,
  };
}

describe('the spouse block and the vehicle choice', () => {
  it('a spouse loan with no creditor names no later gap', () => {
    const row = loan(1, { creditor: '', property: '', payment: null });
    const debt = {
      ...loanDebt(1, '', true),
      answers: { ...NO_DEBT_ANSWERS },
    };
    const answered = {
      ...KESTREL,
      answers: { ...KESTREL.answers, necessary_for_support: 'no' as const },
    };
    expect(
      gapsOf(
        { debts: [answered, debt] },
        { spouse_loans_answer: 'yes', spouse_loans: [row], line_34_answer: 'yes' }
      )
    ).toEqual(['Enter who your spouse owes on each of their loans.']);
  });

  it('a loan naming a vehicle that is no longer on line 11 reads as unanswered', () => {
    const row = loan(1, { secured_by: 'asset-9' });
    expect(
      gapsOf(
        { debts: [KESTREL, loanDebt(1, 'Demo Lender 1', false)] },
        { spouse_loans_answer: 'yes', spouse_loans: [row] }
      )
    ).toEqual(["Say what secures your spouse's loan from Demo Lender 1."]);
  });

  it("an Amounts Owed loan can't name the filer's own car", () => {
    const row = loan(1, { on_amounts_owed: 'yes', debt: 1, secured_by: 'asset-1' });
    expect(
      gapsOf(
        { debts: [KESTREL, loanDebt(1, 'Demo Lender 1', false)] },
        { spouse_loans_answer: 'yes', spouse_loans: [row] }
      )
    ).toEqual(["Say what secures your spouse's loan from Demo Lender 1."]);
  });

  it('two loans naming one Amounts Owed debt keep it on the first', () => {
    const first = loan(1, { on_amounts_owed: 'yes', debt: 5, creditor: '' });
    const second = loan(2, { on_amounts_owed: 'yes', debt: 5, creditor: '' });
    expect(
      gapsOf(
        { debts: [KESTREL, loanDebt(1, 'Demo Lender 1', false), loanDebt(2, '', true)] },
        { spouse_loans_answer: 'yes', spouse_loans: [first, second] }
      )
    ).toEqual([
      "For each of your spouse's loans that is on your Amounts Owed step, choose which one it is.",
    ]);
  });

  it('two Vehicle choices naming one car are a gap', () => {
    const cars = ['asset-1', 'asset-2', 'asset-3'];
    const state: Partial<GapState> = {
      vehicles: cars.map((ref, index) => ({ ref, name: `Demo car ${index + 1}`, claimed: 'yes' })),
      debts: [],
      candidates: cars,
    };
    const choose = 'Choose your Vehicle 1 and your Vehicle 2.';
    const pick = (pair: [string | null, string | null]) => gapsOf(state, { vehicle_choice: pair });
    expect(pick(['asset-1', 'asset-2'])).toEqual([]);
    expect(pick(['asset-1', 'asset-1'])).toEqual([choose]);
    expect(pick(['asset-1', null])).toEqual([choose]);
    expect(pick([null, null])).toEqual([choose]);
    expect(pick(['asset-1', 'asset-4'])).toEqual([choose]);
  });

  it('the spouse block raises no gap unless married and living together', () => {
    const rows = [{ ref: 'spouse-1', description: '', leased: null, claimed: null }];
    expect(
      gapsOf(
        { marriedTogether: false },
        {
          line_3_answer: null,
          spouse_vehicles_answer: 'yes',
          spouse_vehicles: rows,
          spouse_loans_answer: null,
        }
      )
    ).toEqual([]);
  });

  it('line 43 is a gap for every filer the form applies to', () => {
    for (const marriedTogether of [false, true]) {
      expect(gapsOf({ marriedTogether }, { line_43_answer: null })).toEqual([
        'Answer the question on line 43.',
      ]);
    }
  });
});

describe('the gaps come in the pages order', () => {
  const unanswered: Partial<GapState> = {
    vehicles: [{ ...CRV, claimed: null }],
    debts: [
      {
        ...KESTREL,
        answers: { ...KESTREL.answers, payments_left: null, payment_changes: null },
      },
    ],
    lines: { 'debt-1': null },
    candidates: null,
  };
  const everything = (over: Partial<MeansAnswers> = {}, state: Partial<GapState> = {}) =>
    meansTestGaps({
      ...PRIYA_STATE,
      ...unanswered,
      ...state,
      answers: { ...EMPTY_ANSWERS, ...over },
    });

  it('names every gap in the order of the page', () => {
    expect(everything()).toEqual([
      "Answer line 3, about your spouse's income.",
      "Answer whether your spouse has a vehicle that isn't on your property list.",
      'Answer whether your spouse owes a loan on your home, a vehicle or other property.',
      'Answer whether you claim an expense for Honda CR-V EX 2021.',
      'Enter the amount for line 16. Enter 0 if you have none.',
      'Enter the amount for line 17. Enter 0 if you have none.',
      'Enter the amount for line 18. Enter 0 if you have none.',
      'Enter the amount for line 19. Enter 0 if you have none.',
      'Enter the amount for line 20. Enter 0 if you have none.',
      'Enter the amount for line 21. Enter 0 if you have none.',
      'Answer line 22.',
      'Enter the amount for line 23. Enter 0 if you have none.',
      'Answer line 25.',
      'Answer line 26.',
      'Answer line 27.',
      'Answer line 28.',
      'Answer line 29.',
      'Answer line 30.',
      'Answer line 31.',
      'Enter how many payments you have left to Kestrel Auto Finance.',
      'Answer whether your payment to Kestrel Auto Finance will change.',
      'Answer line 34, about debts secured by property you need for support.',
      'Answer line 36.',
      'Answer the question on line 43.',
    ]);
  });

  it("with the spouse's vehicles answered Yes, names the blank row by no gap", () => {
    const rows = [
      { ref: 'spouse-1', description: 'Demo Sedan', leased: null, claimed: null },
      { ref: 'spouse-2', description: '', leased: null, claimed: null },
    ];
    const gaps = everything(
      { spouse_vehicles_answer: 'yes', spouse_vehicles: rows },
      {
        vehicles: [
          { ...CRV, claimed: null },
          { ref: 'spouse-1', name: 'Demo Sedan', claimed: null },
          { ref: 'spouse-2', name: '', claimed: null },
        ],
      }
    );
    expect(gaps.slice(0, 6)).toEqual([
      "Answer line 3, about your spouse's income.",
      "Describe each of your spouse's vehicles.",
      'Answer whether Demo Sedan is leased.',
      'Answer whether your spouse owes a loan on your home, a vehicle or other property.',
      'Answer whether you claim an expense for Honda CR-V EX 2021.',
      'Answer whether you claim an expense for Demo Sedan.',
    ]);
    expect(gaps).toHaveLength(26);
    expect(gaps.join(' ')).not.toContain('spouse-2');
  });

  it("puts line 30's cap right after line 30, before line 31", () => {
    const gaps = everything({
      line_27_answer: 'no',
      line_28_answer: 'no',
      line_30_answer: 'yes',
      line_30_amount: '76.01',
    });
    expect(gaps.slice(12, 17)).toEqual([
      'Answer line 25.',
      'Answer line 26.',
      'Answer line 29.',
      "Line 30 can't be more than $76.00, which is 5% of the IRS food and clothing amounts for 4 people.",
      'Answer line 31.',
    ]);
  });

  it("names the spouse loans' identity sentences once each, in kind order", () => {
    const rows = [
      loan(1, { creditor: '', on_amounts_owed: 'no' }),
      loan(2, { on_amounts_owed: null }),
      loan(3, { on_amounts_owed: 'yes', debt: null, creditor: '' }),
      loan(4, { creditor: 'Demo Lender A', secured_by: null, payment: '300.00' }),
      loan(5, { creditor: 'Demo Lender B', property: '', payment: null }),
      loan(6, { creditor: '', on_amounts_owed: 'no' }),
    ];
    const debts = [
      loanDebt(1, '', true),
      loanDebt(2, '', true),
      loanDebt(3, '', true),
      loanDebt(4, 'Demo Lender A', false),
      loanDebt(5, 'Demo Lender B', false),
      loanDebt(6, '', true),
    ];
    const gaps = meansTestGaps({
      ...PRIYA_STATE,
      answers: { ...PRIYAS_ANSWERS, spouse_loans_answer: 'yes', spouse_loans: rows },
      debts: [KESTREL, ...debts],
      lines: { 'debt-1': '13b' },
    });
    expect(gaps).toEqual([
      "Answer whether each of your spouse's loans is on your Amounts Owed step.",
      "For each of your spouse's loans that is on your Amounts Owed step, choose which one it is.",
      'Enter who your spouse owes on each of their loans.',
      "Say what secures your spouse's loan from Demo Lender A.",
      "Describe the property that secures your spouse's loan from Demo Lender B.",
      "Enter the monthly payment on your spouse's loan from Demo Lender B.",
    ]);
  });
});
