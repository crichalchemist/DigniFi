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
  'MEANS_HOLD_REFUSAL',
  'MEANS_OUTCOME_ABOVE',
  'MEANS_OUTCOME_BELOW',
  'MEANS_OUTCOME_NOT_YET',
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

const held = copy as Record<string, unknown>;
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

  it.each(STRINGS)('%s never says eligible, qualify, estimate or Chapter 13', (_name, sentence) => {
    expect(sentence).not.toMatch(/eligib|qualif|estimate|chapter 13|overcome|rebut/i);
  });

  it.each(STRINGS)('%s says "presumption" only where the owner ruled it may', (name, sentence) => {
    expect(/presumption/i.test(sentence)).toBe(SAYS_PRESUMPTION.includes(name));
  });

  it.each(['MEANS_HOLD_REFUSAL', 'MEANS_TABLE_MISSING'])(
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
  ['MEANS_OUTCOME_NOT_YET', "Its result can't be worked out yet."],
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
    'MEANS_HOLD_REFUSAL',
    "DigniFi can't prepare Form 122A-2 yet, because it doesn't ask all of that form's questions yet. Form 122A-1 waits for it. File the two forms together.",
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
