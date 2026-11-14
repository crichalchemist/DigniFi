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
