/**
 * UPL check on the exemptions page's sentences (3g1 spec §7)
 *
 * DigniFi gives legal information, never advice. A filer choosing a law and an amount for a claim
 * is never told which law fits, which figure to enter, or what a court will allow. The list is
 * the claim steps' (upl-claims-copy.test.ts keeps its own, which a test file mustn't import), plus
 * the words that say a law protects, covers or qualifies. UPL_EXEMPTION_DISCLAIMER lives in
 * constants/upl.ts and says "advise" on purpose, so it is not among these names.
 */

import { describe, expect, it } from 'vitest';
import * as copy from '../constants/copy';

const ADVICE: RegExp[] = [
  /\bshould\b/i,
  /\brecommend/i,
  /\bwe suggest\b/i,
  /\byou must\b/i,
  /\badvise/i,
  /\bwill be discharged\b/i,
  /\byou will keep\b/i,
  /\byou qualify\b/i,
  /\$\s?(?!0(?!\d|[.,]\d))\d/, // "$0" is the form's floor, never a value to enter
  /\byou will qualify\b/i,
  /\byou will probably\b/i,
  /\byou are eligible\b/i,
  /\bthis is the best option\b/i,
  /\byou need to file\b/i,
  /\bpaid first\b/i,
  /\bis (a )?priority\b/i,
  /\bpriority claim/i,
  // The exemptions spec's own additions (§7)
  /\bprotect/i,
  /\bcovered\b/i,
  /\byou keep\b/i,
  /\bbest set\b/i,
  /\bqualif/i,
  /\beligible\b/i,
];

const EXEMPTION_NAMES = [
  'EXEMPTION_DESCRIPTION_TOO_LONG',
  'EXEMPTION_GAP_AMOUNT',
  'EXEMPTION_GAP_AMOUNT_KIND',
  'EXEMPTION_GAP_CHOOSE_ITEM',
  'EXEMPTION_GAP_DESCRIPTION',
  'EXEMPTION_GAP_ITEM_GONE',
  'EXEMPTION_GAP_LAW',
  'EXEMPTION_GAP_LAW_CHANGED',
  'EXEMPTION_GAP_LINE_1',
  'EXEMPTION_GAP_LINE_3',
  'EXEMPTION_GAP_LINE_3_1',
  'EXEMPTION_GAP_NO_CLAIMS',
  'EXEMPTION_GAP_NO_ITEMS',
  'EXEMPTION_ITEM_GONE',
  'EXEMPTION_LAW_SUMMARIES',
  'EXEMPTION_NO_LIMIT',
  'EXEMPTION_TOTAL_DOLLARS',
  'EXEMPTION_TOTAL_FAIR_MARKET',
  'EXEMPTIONS_ADD_CLAIM',
  'EXEMPTIONS_AMOUNT_LABEL',
  'EXEMPTIONS_ANOTHER_LAW',
  'EXEMPTIONS_CHOOSE_ONE',
  'EXEMPTIONS_CLAIM_NUMBER',
  'EXEMPTIONS_CLAIMS_HEADING',
  'EXEMPTIONS_DESCRIPTION_DOESNT_FIT',
  'EXEMPTIONS_DOLLAR_AMOUNT',
  'EXEMPTIONS_FEDERAL_LAWS',
  'EXEMPTIONS_ILLINOIS_LAWS',
  'EXEMPTIONS_INTRO',
  'EXEMPTIONS_LAWS_HEADING',
  'EXEMPTIONS_LAW_LABEL',
  'EXEMPTIONS_NOTE_12_1201',
  'EXEMPTIONS_NOTE_DOMICILE',
  'EXEMPTIONS_NOT_CLAIMING_BUTTON',
  'EXEMPTIONS_NO_ITEMS',
  'EXEMPTIONS_NO_TABLE',
  'EXEMPTIONS_OTHER_LAW_DOESNT_FIT',
  'EXEMPTIONS_PROPERTY_LABEL',
  'EXEMPTIONS_READ_FAILED',
  'EXEMPTIONS_REMOVE_CLAIM',
  'EXEMPTIONS_SAVE_FAILED',
  'EXEMPTIONS_SHORT_LABEL',
  'EXEMPTIONS_TITLE',
  'EXEMPTIONS_TOTALS_HEADING',
] as const;

const held = copy as Record<string, unknown>;
const STRINGS = EXEMPTION_NAMES.filter((name) => typeof held[name] === 'string').map(
  (name) => [name, held[name] as string] as const
);

function adviceIn(sentence: string) {
  return ADVICE.filter((pattern) => pattern.test(sentence)).map(String);
}

describe('the exemptions page gives information, never advice', () => {
  it.each(EXEMPTION_NAMES)('%s is a sentence or the law summaries', (name) => {
    // A missing constant fails here by name, not inside adviceIn
    expect(held[name]).toBeDefined();
  });

  it.each(STRINGS)('%s predicts no outcome and suggests no value', (_name, sentence) => {
    expect(adviceIn(sentence)).toEqual([]);
  });

  it.each(Object.entries(copy.EXEMPTION_LAW_SUMMARIES ?? {}))(
    'the summary of %s predicts no outcome and suggests no value',
    (_key, summary) => {
      expect(adviceIn(summary)).toEqual([]);
    }
  );

  it('lists every exemptions sentence copy.ts holds', () => {
    const names = Object.keys(copy).filter((key) => /^EXEMPTIONS?_/.test(key));
    expect(names.sort()).toEqual([...EXEMPTION_NAMES].sort());
  });

  // So a list that stopped matching can't pass by saying nothing
  it.each([
    'This law will protect your car.',
    'The car is covered.',
    'You keep the house.',
    'This is the best set for you.',
    'You qualify for this law.',
    'You are eligible for this.',
    'Claim $5,000 here.',
    'You should choose this law.',
  ])('finds the advice in "%s"', (sentence) => {
    expect(adviceIn(sentence)).not.toEqual([]);
  });
});
