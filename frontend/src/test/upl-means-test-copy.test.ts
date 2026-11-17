/**
 * UPL check on the means test's sentences (3h1 spec §11)
 *
 * DigniFi gives legal information, never advice. The result is the form's arithmetic, never a
 * verdict, and nothing here tells a filer whether to file, which chapter fits, or what a court
 * will find. The list is the claim steps' and the exemptions page's (each test file keeps its own,
 * which a test file mustn't import), plus the words the owner ruled out for this page.
 * UPL_MEANS_TEST_DISCLAIMER lives in constants/upl.ts and is pinned below.
 */

import { describe, expect, it } from 'vitest';
import * as copy from '../constants/copy';
import copySource from '../constants/copy.ts?raw';
import { PRESUMPTION_INSTRUCTIONS } from '../constants/formText';
import { UPL_MEANS_TEST_DISCLAIMER } from '../constants/upl';

const ADVICE: RegExp[] = [
  /\bshould\b/i,
  /\brecommend/i,
  /\bwe suggest\b/i,
  /\byou must\b/i,
  /\badvise/i,
  /\bwill be discharged\b/i,
  /\byou will keep\b/i,
  /\byou qualify\b/i,
  /\byou will qualify\b/i,
  /\byou will probably\b/i,
  /\byou are eligible\b/i,
  /\bthis is the best option\b/i,
  /\byou need to file\b/i,
  /\bpaid first\b/i,
  /\bis (a )?priority\b/i,
  /\bpriority claim/i,
  /\bprotect/i,
  /\bcovered\b/i,
  /\byou keep\b/i,
  /\bqualif/i,
  /\beligible\b/i,
  // This page's own additions
  /\byou (?:cannot|can't|won't|will not) file\b/i,
  /\byou (?:pass|fail|passed|failed)\b/i,
  /\bdenied\b/i,
  /\brejected\b/i,
];

const NAMES = [
  'MEANS_FILED_BEFORE_122A1',
  'MEANS_FILED_BEFORE_122A2',
  'MEANS_FILED_MISMATCH',
  'MEANS_LINE_MISSING',
  'MEANS_TOO_LONG',
  'MEANS_LETTER',
  'MEANS_EXPLANATION_TOO_LONG',
  'MEANS_EXPLANATION_LETTER',
  'MEANS_GAP_LINE_3',
  'MEANS_GAP_LINE_3_CAP',
  'MEANS_GAP_LINE_3_NO_ROW',
  'MEANS_GAP_LINE_3_ROW',
  'MEANS_GAP_SPOUSE_VEHICLES',
  'MEANS_GAP_SPOUSE_VEHICLES_NO_ROW',
  'MEANS_GAP_SPOUSE_VEHICLE_DESCRIBE',
  'MEANS_GAP_SPOUSE_VEHICLE_LEASED',
  'MEANS_GAP_SPOUSE_LOANS',
  'MEANS_GAP_SPOUSE_LOANS_NO_ROW',
  'MEANS_GAP_SPOUSE_LOAN_ON_AMOUNTS_OWED',
  'MEANS_GAP_SPOUSE_LOAN_WHICH',
  'MEANS_GAP_SPOUSE_LOAN_CREDITOR',
  'MEANS_GAP_SPOUSE_LOAN_SECURED_BY',
  'MEANS_GAP_SPOUSE_LOAN_PROPERTY',
  'MEANS_GAP_SPOUSE_LOAN_PAYMENT',
  'MEANS_GAP_VEHICLE',
  'MEANS_GAP_VEHICLE_CHOICE',
  'MEANS_GAP_LINE_15',
  'MEANS_GAP_LINE_15_AMOUNT',
  'MEANS_GAP_LINE_15_CAP',
  'MEANS_GAP_AMOUNT',
  'MEANS_GAP_OPT_IN',
  'MEANS_GAP_OPT_IN_AMOUNT',
  'MEANS_GAP_LINE_25_AMOUNTS',
  'MEANS_GAP_LINE_25_SPENDS',
  'MEANS_GAP_LINE_25_ACTUAL',
  'MEANS_GAP_LINE_30_CAP',
  'MEANS_GAP_LINE_30_CAP_ONE',
  'MEANS_GAP_PAYMENTS_LEFT',
  'MEANS_GAP_PAYMENT_CHANGES',
  'MEANS_GAP_SIXTY_MONTH_TOTAL',
  'MEANS_GAP_TAXES',
  'MEANS_GAP_LINE_34',
  'MEANS_GAP_SUPPORT',
  'MEANS_GAP_CURE',
  'MEANS_GAP_LINE_36',
  'MEANS_GAP_LINE_36_PAYMENT',
  'MEANS_GAP_LINE_43',
  'MEANS_GAP_LINE_43_NONE',
  'MEANS_GAP_LINE_43_EXPLANATION',
  'MEANS_GAP_LINE_43_AMOUNT',
  'MEANS_NOT_A_COUNTED_DEBT',
  'MEANS_NOT_A_LINE_11_VEHICLE',
  'MEANS_NOT_AN_OPEN_DEBT',
  'MEANS_OUTCOME_ANSWER_SIDEBAR',
  'MEANS_OUTCOME_ANSWER_PAGE',
  'MEANS_PAGE_PHRASE',
  'MEANS_LINE_43_LINK',
  'MEANS_STALE_ANSWERS',
  'MEANS_RESULT_CHANGED',
  'MEANS_PAGE_INTRO',
  'MEANS_PAGE_AGES',
  'MEANS_PAGE_LOADING',
  'MEANS_PAGE_READ_FAILED',
  'MEANS_PAGE_SAVE_FAILED',
  'MEANS_PAGE_UPDATED',
  'MEANS_BESIDE_YOU',
  'MEANS_BESIDE_SPOUSE',
  'MEANS_LINE_7G',
  'MEANS_LINE_8',
  'MEANS_LINE_15_CAP',
  'MEANS_LINE_27_NOTE',
  'MEANS_LINE_29_NOTE',
  'MEANS_LINE_30_CAP',
  'MEANS_LINE_30_CAP_ONE',
  'MEANS_LINE_35',
  'MEANS_ADD_ROW',
  'MEANS_REMOVE_ROW',
  'MEANS_ROW_LEGEND',
  'MEANS_DEBT_PROPERTY',
  'MEANS_DEBT_GOES_ON',
  'MEANS_DEBT_WAITS',
  'MEANS_DEBT_PAYMENT',
  'MEANS_PAYMENTS_LEFT',
  'MEANS_SIXTY_OR_MORE',
  'MEANS_PAYMENT_CHANGES',
  'MEANS_SIXTY_MONTH_TOTAL',
  'MEANS_LINE_36_LINK',
  'MEANS_LINE_36_LIMITS',
  'MEANS_LINE_36_TOTALS',
  'MEANS_LINE_36_OTHER_RULES',
  'MEANS_LINE_36_MULTIPLIER',
  'MEANS_LINE_36_PRODUCT',
  'MEANS_SPOUSE_TITLE',
  'MEANS_SPOUSE_INTRO',
  'MEANS_SPOUSE_VEHICLES_QUESTION',
  'MEANS_SPOUSE_VEHICLE_DESCRIBE',
  'MEANS_SPOUSE_VEHICLE_LEASED',
  'MEANS_SPOUSE_VEHICLE_LEGEND',
  'MEANS_SPOUSE_ADD_VEHICLE',
  'MEANS_SPOUSE_REMOVE_VEHICLE',
  'MEANS_SPOUSE_LOANS_QUESTION',
  'MEANS_SPOUSE_LOANS_HINT',
  'MEANS_SPOUSE_LOAN_LEGEND',
  'MEANS_SPOUSE_ADD_LOAN',
  'MEANS_SPOUSE_REMOVE_LOAN',
  'MEANS_SPOUSE_LOAN_ON_AMOUNTS_OWED',
  'MEANS_SPOUSE_LOAN_WHICH',
  'MEANS_SPOUSE_LOAN_WHICH_NOTE',
  'MEANS_SPOUSE_LOAN_CREDITOR',
  'MEANS_SPOUSE_LOAN_SECURED_BY',
  'MEANS_SPOUSE_LOAN_HOME',
  'MEANS_SPOUSE_LOAN_OTHER',
  'MEANS_SPOUSE_LOAN_PROPERTY',
  'MEANS_SPOUSE_LOAN_PAYMENT',
  'MEANS_SPOUSE_LOAN_FROM',
  'MEANS_LINE_43_EXAMPLES',
  'MEANS_LINE_43_OWN_WORDS',
  'MEANS_LINE_43_NO_SUGGESTION',
  'MEANS_LINE_43_LAWYER',
  'MEANS_LINE_43_LEGEND',
  'MEANS_LINE_43_ADD',
  'MEANS_LINE_43_REMOVE',
  'MEANS_LINE_43_HAPPENED',
  'MEANS_LINE_43_HAPPENED_HINT',
  'MEANS_LINE_43_CHANGE',
  'MEANS_LINE_43_CHOICES',
  'MEANS_LINE_43_PAPERS',
  'MEANS_LINE_43_BOX_NOTE',
  'MEANS_LINE_43_ASSEMBLE',
  'MEANS_LINE_43_ASSEMBLE_NOTE',
  'MEANS_LINE_43_LABEL_HAPPENED',
  'MEANS_LINE_43_LABEL_CHANGE',
  'MEANS_LINE_43_LABEL_CHOICES',
  'MEANS_LINE_43_LABEL_PAPERS',
  'MEANS_LINE_43_SKIPPED',
  'MEANS_LINE_43_POINTER',
  'MEANS_REBUTTAL_NOW',
  'MEANS_REBUTTAL_IF',
  'MEANS_REBUTTAL_IF_BELOW',
  'MEANS_REBUTTAL_COURT',
  'MEANS_OUTCOME_ABOVE',
  'MEANS_OUTCOME_BELOW',
  'MEANS_OUTCOME_NO_PRESUMPTION',
  'MEANS_OUTCOME_PRESUMPTION',
  'MEANS_OUTCOME_REASSURANCE',
  'MEANS_PAIR_NOTICE',
  'MEANS_TABLE_MISSING',
  'MEANS_TEST_CALCULATING',
  'MEANS_TEST_INCOME_LABEL',
  'MEANS_TEST_PREVIEW_TITLE',
  'MEANS_TEST_UNAVAILABLE',
  'MEANS_TEST_UPDATING',
  'MEANS_TEST_WAITING',
  'TABLE_NOTICE_MEDIAN',
  'TABLE_NOTICE_NEW_FIGURES',
  'TABLE_NOTICE_SECTION_104',
  'TABLE_NOTICE_STANDARDS',
] as const;

const SAYS_PRESUMPTION = [
  'MEANS_OUTCOME_PRESUMPTION',
  'MEANS_OUTCOME_NO_PRESUMPTION',
  'MEANS_OUTCOME_REASSURANCE',
];

// Line 36 is the only place DigniFi names Chapter 13 (C-6)
const SAYS_CHAPTER_13 = ['MEANS_LINE_36_LIMITS', 'MEANS_LINE_36_OTHER_RULES'];

const held = copy as Record<string, unknown>;

// Every sentence of line 43's writing aid, its gaps, its figure and its explanation's limits:
// none says rebut, overcome or abuse (3h2 spec section 8.9)
const LINE_43_COPY = NAMES.filter((name) =>
  /^(MEANS_LINE_43_|MEANS_REBUTTAL_|MEANS_GAP_LINE_43|MEANS_EXPLANATION_)/.test(name)
);
const STRINGS = NAMES.filter((name) => typeof held[name] === 'string').map(
  (name) => [name, held[name] as string] as const
);

function adviceIn(sentence: string) {
  return ADVICE.filter((pattern) => pattern.test(sentence)).map(String);
}

describe('the means test gives information, never advice', () => {
  it.each(NAMES)('%s is defined', (name) => {
    // A missing constant fails here by name, not inside adviceIn
    expect(held[name]).toBeDefined();
  });

  it.each(STRINGS)('%s gives no advice and predicts no outcome', (_name, sentence) => {
    expect(adviceIn(sentence)).toEqual([]);
  });

  it.each(STRINGS)('%s never says eligible, qualify, estimate or Chapter 13', (name, sentence) => {
    const words = SAYS_CHAPTER_13.includes(name)
      ? /eligib|qualif|estimate|overcome|rebut/i
      : /eligib|qualif|estimate|chapter 13|overcome|rebut/i;
    expect(sentence).not.toMatch(words);
  });

  it.each(SAYS_CHAPTER_13)('%s is where line 36 says Chapter 13', (name) => {
    expect(held[name]).toMatch(/chapter 13/i);
  });

  it.each(LINE_43_COPY)('%s says neither rebut, overcome nor abuse', (name) => {
    expect(held[name]).not.toMatch(/rebut|overcome|abuse/i);
  });

  it.each(STRINGS)('%s says "presumption" only where the owner ruled it may', (name, sentence) => {
    expect(/presumption/i.test(sentence)).toBe(SAYS_PRESUMPTION.includes(name));
  });

  it.each(['MEANS_LINE_MISSING', 'MEANS_TABLE_MISSING'])(
    '%s says neither presumption nor abuse',
    (name) => {
      expect(held[name]).not.toMatch(/presumption|abuse/i);
    }
  );

  it('ends every outcome with the court’s decision, in the one closing sentence', () => {
    expect(UPL_MEANS_TEST_DISCLAIMER).toBe('A court makes the final decision.');
  });

  it('puts no word of overcoming or rebutting in copy.ts', () => {
    for (const [key, value] of Object.entries(copy)) {
      if (typeof value === 'string') {
        expect(value, key).not.toMatch(/overcome|rebut/i);
      }
    }
  });

  it('lists every means test sentence copy.ts holds', () => {
    const names = Object.keys(copy).filter((key) => /^(MEANS_|TABLE_NOTICE_)/.test(key));
    expect(names.sort()).toEqual([...NAMES].sort());
  });

  it('keeps the two sentences that were already there, unchanged', () => {
    expect(copy.MEANS_TEST_CALCULATING).toBe('Calculating...');
    expect(copy.MEANS_TEST_INCOME_LABEL).toBe('Monthly income for the means test');
  });

  // So a list that stopped matching can't pass by saying nothing
  it.each([
    'You should file for Chapter 7.',
    'We recommend you wait.',
    'You qualify for Chapter 7.',
    'You are eligible.',
    'You will probably pass.',
    'Your case was denied.',
    'You cannot file.',
    'This is the best option.',
  ])('finds the advice in "%s"', (sentence) => {
    expect(adviceIn(sentence)).not.toEqual([]);
  });
});

// Each sentence as the plan's Global Constraints give it (C-24 counsel drafts), so a change to a
// filer's words fails here and goes back to counsel; the tests above import the constants, so they
// can't see a change that keeps within the patterns
const EXACT_WORDS: [string, string][] = [
  ['MEANS_TEST_PREVIEW_TITLE', 'Income test'],
  ['MEANS_TEST_UPDATING', 'Updating your result...'],
  ['MEANS_TEST_WAITING', "We'll show your result once you enter your income."],
  [
    'MEANS_TEST_UNAVAILABLE',
    "DigniFi can't show your result right now. This is not an error with your information.",
  ],
  [
    'MEANS_OUTCOME_BELOW',
    "Your income is at or below the median for a household of {n} in Illinois. Form 122A-2 doesn't apply to you.",
  ],
  [
    'MEANS_OUTCOME_ABOVE',
    'Your income is above the median for a household of {n}, so Form 122A-2 applies.',
  ],
  [
    'MEANS_OUTCOME_REASSURANCE',
    "Being above the median doesn't mean a presumption of abuse applies.",
  ],
  [
    'MEANS_OUTCOME_NO_PRESUMPTION',
    "The form's arithmetic gives: There is no presumption of abuse.",
  ],
  ['MEANS_OUTCOME_PRESUMPTION', "The form's arithmetic gives: There is a presumption of abuse."],
  [
    'MEANS_TABLE_MISSING',
    "DigniFi doesn't have the means test figures for today's date yet, so it can't work out Form 122A-2.",
  ],
  [
    'MEANS_LINE_MISSING',
    "DigniFi can't work out every line of Form 122A-2, so it can't print that form. Form 122A-1 waits for it. File the two forms together.",
  ],
  [
    'MEANS_PAIR_NOTICE',
    'Form 122A-1 says your result is worked out on Form 122A-2. File them together.',
  ],
  [
    'MEANS_FILED_BEFORE_122A2',
    'This copy was marked filed before DigniFi could fill in all of Form 122A-2. It shows what was stored then.',
  ],
  [
    'MEANS_FILED_BEFORE_122A1',
    'This copy was marked filed before DigniFi could fill in Form 122A-2, which this form points to. It shows what was stored then.',
  ],
  [
    'MEANS_FILED_MISMATCH',
    "This copy doesn't say its result is worked out on Form 122A-2. Form 122A-2 now applies to you.",
  ],
  [
    'TABLE_NOTICE_MEDIAN',
    'These forms use the median income figures the U.S. Trustee applies to cases filed on or after {date}.',
  ],
  [
    'TABLE_NOTICE_STANDARDS',
    'These forms use the IRS expense standards the U.S. Trustee applies to cases filed on or after {date}.',
  ],
  [
    'TABLE_NOTICE_SECTION_104',
    "These forms use the Bankruptcy Code's dollar amounts for cases filed on or after {date}.",
  ],
  [
    'TABLE_NOTICE_NEW_FIGURES',
    'New figures are expected after {date}. If you file after that date, download your forms again.',
  ],
  // The Form 122A-2 page (3h2): the sentences the server and the page share, and the page's gaps
  ['MEANS_TOO_LONG', 'This is too long for the box on Form 122A-2. Shorten it.'],
  ['MEANS_LETTER', "This has a letter Form 122A-2 can't print. Change it."],
  ['MEANS_EXPLANATION_TOO_LONG', 'This explanation is too long to print with line 43. Shorten it.'],
  ['MEANS_EXPLANATION_LETTER', "This explanation has a letter Form 122A-2 can't print. Change it."],
  ['MEANS_GAP_LINE_3', "Answer line 3, about your spouse's income."],
  [
    'MEANS_GAP_LINE_3_CAP',
    "Line 3 can't be more than {amount}, your spouse's income on Form 122A-1, Column B.",
  ],
  [
    'MEANS_GAP_LINE_3_NO_ROW',
    "Add each use of your spouse's income on line 3, or change the answer to No.",
  ],
  [
    'MEANS_GAP_LINE_3_ROW',
    "Enter what your spouse's income was used for, and the amount, on each row of line 3.",
  ],
  [
    'MEANS_GAP_SPOUSE_VEHICLES',
    "Answer whether your spouse has a vehicle that isn't on your property list.",
  ],
  [
    'MEANS_GAP_SPOUSE_VEHICLES_NO_ROW',
    "Add each of your spouse's vehicles, or change the answer to No.",
  ],
  ['MEANS_GAP_SPOUSE_VEHICLE_DESCRIBE', "Describe each of your spouse's vehicles."],
  ['MEANS_GAP_SPOUSE_VEHICLE_LEASED', 'Answer whether {name} is leased.'],
  [
    'MEANS_GAP_SPOUSE_LOANS',
    'Answer whether your spouse owes a loan on your home, a vehicle or other property.',
  ],
  ['MEANS_GAP_SPOUSE_LOANS_NO_ROW', "Add each of your spouse's loans, or change the answer to No."],
  [
    'MEANS_GAP_SPOUSE_LOAN_ON_AMOUNTS_OWED',
    "Answer whether each of your spouse's loans is on your Amounts Owed step.",
  ],
  [
    'MEANS_GAP_SPOUSE_LOAN_WHICH',
    "For each of your spouse's loans that is on your Amounts Owed step, choose which one it is.",
  ],
  ['MEANS_GAP_SPOUSE_LOAN_CREDITOR', 'Enter who your spouse owes on each of their loans.'],
  ['MEANS_GAP_SPOUSE_LOAN_SECURED_BY', "Say what secures your spouse's loan from {name}."],
  [
    'MEANS_GAP_SPOUSE_LOAN_PROPERTY',
    "Describe the property that secures your spouse's loan from {name}.",
  ],
  ['MEANS_GAP_SPOUSE_LOAN_PAYMENT', "Enter the monthly payment on your spouse's loan from {name}."],
  ['MEANS_GAP_VEHICLE', 'Answer whether you claim an expense for {name}.'],
  ['MEANS_GAP_VEHICLE_CHOICE', 'Choose your Vehicle 1 and your Vehicle 2.'],
  ['MEANS_GAP_LINE_15', 'Answer the question on line 15.'],
  ['MEANS_GAP_LINE_15_AMOUNT', 'Enter the amount for line 15.'],
  [
    'MEANS_GAP_LINE_15_CAP',
    "Line 15 can't be more than {amount}, the IRS amount for public transportation.",
  ],
  ['MEANS_GAP_AMOUNT', 'Enter the amount for line {n}. Enter 0 if you have none.'],
  ['MEANS_GAP_OPT_IN', 'Answer line {n}.'],
  ['MEANS_GAP_OPT_IN_AMOUNT', 'Enter the amount for line {n}.'],
  ['MEANS_GAP_LINE_25_AMOUNTS', 'Enter the three amounts on line 25.'],
  ['MEANS_GAP_LINE_25_SPENDS', 'Answer whether you actually spend the line 25 total.'],
  ['MEANS_GAP_LINE_25_ACTUAL', 'Enter how much you actually spend, on line 25.'],
  [
    'MEANS_GAP_LINE_30_CAP',
    "Line 30 can't be more than {amount}, which is 5% of the IRS food and clothing amounts for {n} people.",
  ],
  [
    'MEANS_GAP_LINE_30_CAP_ONE',
    "Line 30 can't be more than {amount}, which is 5% of the IRS food and clothing amounts for 1 person.",
  ],
  ['MEANS_GAP_PAYMENTS_LEFT', 'Enter how many payments you have left to {name}.'],
  ['MEANS_GAP_PAYMENT_CHANGES', 'Answer whether your payment to {name} will change.'],
  [
    'MEANS_GAP_SIXTY_MONTH_TOTAL',
    'Enter the total you will owe {name} in the 60 months after you file.',
  ],
  ['MEANS_GAP_TAXES', 'Say if the payment to {name} pays for taxes or insurance too.'],
  ['MEANS_GAP_LINE_34', 'Answer line 34, about debts secured by property you need for support.'],
  ['MEANS_GAP_SUPPORT', 'Say if your debt to {name} is secured by property you need for support.'],
  ['MEANS_GAP_CURE', 'Enter the cure amount for {name}. Enter 0 if there is none.'],
  ['MEANS_GAP_LINE_36', 'Answer line 36.'],
  ['MEANS_GAP_LINE_36_PAYMENT', 'Enter the projected monthly plan payment on line 36.'],
  ['MEANS_GAP_LINE_43', 'Answer the question on line 43.'],
  [
    'MEANS_GAP_LINE_43_NONE',
    'Add each special circumstance on line 43, or change the answer to No.',
  ],
  ['MEANS_GAP_LINE_43_EXPLANATION', 'Give the explanation for circumstance {n} on line 43.'],
  [
    'MEANS_GAP_LINE_43_AMOUNT',
    'Enter the average monthly amount for circumstance {n} on line 43. Enter 0 if there is none.',
  ],
  // The server's sentences for a row that has gone; the page reads a 400 by these words (DIG-513)
  ['MEANS_NOT_A_COUNTED_DEBT', "This isn't one of your secured debts."],
  ['MEANS_NOT_A_LINE_11_VEHICLE', "This isn't one of the vehicles on line 11."],
  [
    'MEANS_NOT_AN_OPEN_DEBT',
    "This isn't one of the debts on your Amounts Owed step not listed as secured.",
  ],
  // The page's own words (3h2)
  [
    'MEANS_OUTCOME_ANSWER_SIDEBAR',
    "Its result can't be worked out until you answer the questions on the Form 122A-2 page, once you finish your intake.",
  ],
  [
    'MEANS_OUTCOME_ANSWER_PAGE',
    "Its result can't be worked out until you answer the questions on the Form 122A-2 page.",
  ],
  ['MEANS_PAGE_PHRASE', 'the Form 122A-2 page'],
  ['MEANS_LINE_43_LINK', 'Go to line 43, special circumstances'],
  [
    'MEANS_STALE_ANSWERS',
    "You answered the questions about your secured debts in {month}. If you've made payments since, check your answers on the Form 122A-2 page.",
  ],
  [
    'MEANS_RESULT_CHANGED',
    'Your result has changed. It is at the top of the page. Press Continue again when you are ready.',
  ],
  [
    'MEANS_PAGE_INTRO',
    "Form 122A-2 is the Chapter 7 means test calculation. Its questions use the form's own words, which can differ from the words on Schedules I and J. Beside some questions, DigniFi shows what you entered on those schedules, for you to compare. No answer is filled in for you.",
  ],
  [
    'MEANS_PAGE_AGES',
    'Line 7 counts people under 65 and people 65 or older. DigniFi uses your date of birth and the ages on your household list, as you entered them.',
  ],
  ['MEANS_PAGE_LOADING', 'Loading your answers...'],
  [
    'MEANS_PAGE_READ_FAILED',
    "We couldn't get your answers just now. Please try again in a moment.",
  ],
  ['MEANS_PAGE_SAVE_FAILED', "We couldn't save your answers just now. Please try again."],
  [
    'MEANS_PAGE_UPDATED',
    'Your intake changed after this page opened. The page now shows your latest answers. Check them, then press Continue again.',
  ],
  ['MEANS_BESIDE_YOU', 'You entered {amount} on Schedule {form} line {line}.'],
  ['MEANS_BESIDE_SPOUSE', 'You entered {amount} for your spouse on Schedule {form} line {line}.'],
  ['MEANS_LINE_7G', 'Your line 7 total is {amount}.'],
  ['MEANS_LINE_8', 'Your line 8 amount is {amount}.'],
  [
    'MEANS_LINE_15_CAP',
    "The IRS amount for public transportation is {amount}. Line 15 can't be more than that.",
  ],
  [
    'MEANS_LINE_27_NOTE',
    'The form says the court must keep the nature of these expenses confidential. DigniFi asks only for the amount.',
  ],
  ['MEANS_LINE_29_NOTE', 'The form allows up to {amount} a month for each child.'],
  [
    'MEANS_LINE_30_CAP',
    "For {n} people, 5% of the IRS food and clothing amounts is {amount}. Line 30 can't be more than that.",
  ],
  [
    'MEANS_LINE_30_CAP_ONE',
    "For 1 person, 5% of the IRS food and clothing amounts is {amount}. Line 30 can't be more than that.",
  ],
  [
    'MEANS_LINE_35',
    'Line 35 comes from what you entered as past due for priority debts on the Amounts Owed step: {amount}.',
  ],
  ['MEANS_ADD_ROW', 'Add a row'],
  ['MEANS_REMOVE_ROW', 'Remove row {n}'],
  ['MEANS_ROW_LEGEND', 'Row {n}'],
  ['MEANS_DEBT_PROPERTY', 'Secured by {property}'],
  ['MEANS_DEBT_GOES_ON', 'On Form 122A-2, this debt goes on line {line}.'],
  ['MEANS_DEBT_WAITS', 'Its line depends on your answers about your vehicles above.'],
  ['MEANS_DEBT_PAYMENT', 'You entered a monthly payment of {amount} on the Amounts Owed step.'],
  ['MEANS_PAYMENTS_LEFT', 'How many payments are left?'],
  ['MEANS_SIXTY_OR_MORE', '60 or more'],
  ['MEANS_PAYMENT_CHANGES', 'Will the payment change, or end with a larger payment?'],
  ['MEANS_SIXTY_MONTH_TOTAL', 'The total due in the 60 months after you file'],
  ['MEANS_LINE_36_LINK', 'Bankruptcy Basics, from the U.S. Courts'],
  [
    'MEANS_LINE_36_LIMITS',
    'Chapter 13 has debt limits (11 U.S.C. section 109(e)). For cases filed on or after {date}, the limits are {unsecured} in unsecured debts and {secured} in secured debts.',
  ],
  [
    'MEANS_LINE_36_TOTALS',
    'You listed {ef} in unsecured debts on Schedule E/F. You listed {d} in secured debts on Schedule D.',
  ],
  [
    'MEANS_LINE_36_OTHER_RULES',
    "Other rules also apply. DigniFi can't tell you whether you can file under chapter 13.",
  ],
  [
    'MEANS_LINE_36_MULTIPLIER',
    "The U.S. Trustee's multiplier for the Northern District of Illinois is {m}%.",
  ],
  [
    'MEANS_LINE_36_PRODUCT',
    'The average monthly administrative expense is {m}% of {payment}. That is {product}.',
  ],
  ['MEANS_SPOUSE_TITLE', "Your spouse's vehicles and loans"],
  [
    'MEANS_SPOUSE_INTRO',
    "These questions are about your spouse's vehicles and loans. Leave out a vehicle on your property list and a loan your Amounts Owed step lists as secured.",
  ],
  [
    'MEANS_SPOUSE_VEHICLES_QUESTION',
    "Does your spouse have a vehicle that isn't on your property list?",
  ],
  ['MEANS_SPOUSE_VEHICLE_DESCRIBE', 'Describe the vehicle, such as its year, make and model.'],
  ['MEANS_SPOUSE_VEHICLE_LEASED', 'Is this vehicle leased?'],
  ['MEANS_SPOUSE_VEHICLE_LEGEND', "Your spouse's vehicle {n}"],
  ['MEANS_SPOUSE_ADD_VEHICLE', 'Add a vehicle'],
  ['MEANS_SPOUSE_REMOVE_VEHICLE', "Remove your spouse's vehicle {n}"],
  [
    'MEANS_SPOUSE_LOANS_QUESTION',
    'Does your spouse owe a loan on your home, a vehicle or other property?',
  ],
  [
    'MEANS_SPOUSE_LOANS_HINT',
    'Leave out a loan your Amounts Owed step lists as secured. Count a loan you both owe on property only your spouse owns.',
  ],
  ['MEANS_SPOUSE_LOAN_LEGEND', "Your spouse's loan {n}"],
  ['MEANS_SPOUSE_ADD_LOAN', 'Add a loan'],
  ['MEANS_SPOUSE_REMOVE_LOAN', "Remove your spouse's loan {n}"],
  ['MEANS_SPOUSE_LOAN_ON_AMOUNTS_OWED', 'Is this loan on your Amounts Owed step?'],
  ['MEANS_SPOUSE_LOAN_WHICH', 'Which loan is it?'],
  [
    'MEANS_SPOUSE_LOAN_WHICH_NOTE',
    "This list shows the loans on your Amounts Owed step that aren't listed as secured.",
  ],
  ['MEANS_SPOUSE_LOAN_CREDITOR', 'Who does your spouse owe?'],
  ['MEANS_SPOUSE_LOAN_SECURED_BY', 'What secures the loan?'],
  ['MEANS_SPOUSE_LOAN_HOME', 'Your home'],
  ['MEANS_SPOUSE_LOAN_OTHER', 'Other property'],
  ['MEANS_SPOUSE_LOAN_PROPERTY', 'Describe the property.'],
  ['MEANS_SPOUSE_LOAN_PAYMENT', 'The monthly payment'],
  ['MEANS_SPOUSE_LOAN_FROM', "Your spouse's loan from {name}"],
  [
    'MEANS_LINE_43_EXAMPLES',
    'The law gives two examples of special circumstances. One is a serious medical condition. The other is a call or order to active duty in the Armed Forces.',
  ],
  [
    'MEANS_LINE_43_OWN_WORDS',
    'Line 43 is about your monthly expenses and income now. You can explain your situation in your own words.',
  ],
  [
    'MEANS_LINE_43_NO_SUGGESTION',
    "DigniFi doesn't say which circumstances apply to you, or whether a court will allow them.",
  ],
  ['MEANS_LINE_43_LAWYER', 'A lawyer can tell you how the law applies to your facts.'],
  ['MEANS_LINE_43_LEGEND', 'Circumstance {n}'],
  ['MEANS_LINE_43_ADD', 'Add a circumstance'],
  ['MEANS_LINE_43_REMOVE', 'Remove circumstance {n}'],
  ['MEANS_LINE_43_HAPPENED', 'What happened, and when?'],
  ['MEANS_LINE_43_HAPPENED_HINT', 'Use your own words.'],
  ['MEANS_LINE_43_CHANGE', 'How does it change your monthly expenses or income?'],
  ['MEANS_LINE_43_CHOICES', 'What other choices did you look at, and why did they not work?'],
  ['MEANS_LINE_43_PAPERS', 'What papers will you give your case trustee to show this?'],
  [
    'MEANS_LINE_43_BOX_NOTE',
    'Write only what you want the court to read. This box prints with line 43 on Form 122A-2. Edit it until it says what you mean.',
  ],
  ['MEANS_LINE_43_ASSEMBLE', 'Put my answers together'],
  [
    'MEANS_LINE_43_ASSEMBLE_NOTE',
    'This puts your answers in the box below, under short headings. Nothing else is added.',
  ],
  ['MEANS_LINE_43_LABEL_HAPPENED', 'What happened:'],
  ['MEANS_LINE_43_LABEL_CHANGE', 'How it changes my monthly expenses or income:'],
  ['MEANS_LINE_43_LABEL_CHOICES', 'Other choices I looked at:'],
  ['MEANS_LINE_43_LABEL_PAPERS', 'Papers I will give my case trustee:'],
  [
    'MEANS_LINE_43_SKIPPED',
    "With your current answers, the form skips line 43, so this answer won't print.",
  ],
  ['MEANS_LINE_43_POINTER', 'See line 43.{n} on the attached sheet.'],
  ['MEANS_REBUTTAL_NOW', 'Your line 39d is now {amount}.'],
  ['MEANS_REBUTTAL_IF', 'If the court allowed the amounts on line 43, line 39d would be {amount}.'],
  [
    'MEANS_REBUTTAL_IF_BELOW',
    'If the court allowed the amounts on line 43, line 39d would be {amount} less than $0.',
  ],
  ['MEANS_REBUTTAL_COURT', 'The court decides whether to allow them.'],
  // Not a means test sentence, but 3h1 made its old words false (final review F11)
  [
    'REVIEW_INTRO',
    'Please review the information below carefully. DigniFi uses it to fill in your court forms.',
  ],
];

describe('the means test sentences keep their words exactly', () => {
  it.each(EXACT_WORDS)('%s keeps its words', (name, words) => {
    expect(held[name]).toBe(words);
  });

  it('keeps the instructions’ words on a presumption, from the instructions PDF p. 35', () => {
    expect(PRESUMPTION_INSTRUCTIONS).toBe(
      'A presumption of abuse does not mean you are actually trying to abuse the bankruptcy system. Rather, the presumption simply means that you are presumed to have enough income that you should not be granted relief under chapter 7. You may overcome the presumption by showing special circumstances that reduce your income or increase your expenses.'
    );
  });

  it('pins every means test sentence copy.ts holds, so a new one is added here too', () => {
    // The two sentences that were already there are pinned above, in their own test
    const added = NAMES.filter(
      (name) => name !== 'MEANS_TEST_CALCULATING' && name !== 'MEANS_TEST_INCOME_LABEL'
    );
    const pinned = EXACT_WORDS.map(([name]) => name).filter((name) => name !== 'REVIEW_INTRO');
    expect(pinned.sort()).toEqual([...added].sort());
  });

  it('the Review step’s opening words give no advice and never say eligible', () => {
    expect(adviceIn(copy.REVIEW_INTRO)).toEqual([]);
    expect(copy.REVIEW_INTRO).not.toMatch(/eligib|qualif|estimate|chapter 13|overcome|rebut/i);
  });
});

// The counsel draft each sentence waits on (the plan's Global Constraints), read from the source
function counselMark(name: string): string {
  if (name === 'MEANS_LINE_43_LINK') return 'C-24';
  if (name === 'MEANS_LINE_43_OWN_WORDS') return 'C-30';
  if (/^(MEANS_LINE_43_|MEANS_EXPLANATION_)/.test(name)) return 'C-31';
  if (name.startsWith('MEANS_LINE_36_')) return 'C-6';
  if (name === 'MEANS_LINE_27_NOTE') return 'C-27';
  if (/^(MEANS_SPOUSE_|MEANS_GAP_SPOUSE_)/.test(name)) return 'C-34';
  if (name.startsWith('MEANS_REBUTTAL_')) return 'C-32';
  return 'C-24';
}

describe('every means test sentence carries its counsel mark', () => {
  const marked = NAMES.filter(
    (name) => name !== 'MEANS_TEST_CALCULATING' && name !== 'MEANS_TEST_INCOME_LABEL'
  );

  it.each(marked)('%s has its mark on the line above', (name) => {
    const found = copySource.match(
      new RegExp(`// DRAFT: counsel (C-\\d+)\\nexport const ${name}\\b`)
    );
    expect(found?.[1]).toBe(counselMark(name));
  });
});
