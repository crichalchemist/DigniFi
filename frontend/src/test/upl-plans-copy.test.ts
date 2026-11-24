/**
 * UPL check on Your Plans' sentences (forms step 4e)
 *
 * DigniFi gives legal information, never advice. On Form 108's step that matters most: the filer
 * decides what to do with property that secures a debt, and no DigniFi sentence may tell them
 * what to choose or what a choice will bring. The form's and the statutes' own words live in
 * formText.ts and are not checked here. The ADVICE list is copied whole from
 * upl-petition-copy.test.ts, with no carve-out.
 */

import { describe, expect, it } from 'vitest';
import * as copy from '../constants/copy';
import copySource from '../constants/copy.ts?raw';

const ADVICE: RegExp[] = [
  /\bshould\b/i,
  /\brecommend/i,
  /\bwe suggest\b/i,
  /\byou must\b/i,
  /\badvise/i,
  /\bwill be discharged\b/i,
  /\byou will keep\b/i,
  /\byou qualify\b/i,
  /\$\s?(?!0(?!\d|[.,]\d))\d/, // "$0" is the form's floor, never a value to enter (R13)
  // PROHIBITED_PHRASES that the words above don't already catch
  /\byou will qualify\b/i,
  /\byou will probably\b/i,
  /\byou are eligible\b/i,
  /\bthis is the best option\b/i,
  /\byou need to file\b/i,
  // The spec's anti-goal wording (3d spec §1, §7): never call a debt priority or say it is paid first
  /\bpaid first\b/i,
  /\bis (a )?priority\b/i,
  /\bpriority claim/i,
];

const strings = copy as Record<string, unknown>;

// Every Your Plans string (E7, E8): the PLANS_ sentences found by prefix, so a new one is checked
// too, the five definitions' names, the gap sentences and the too-long labels
const PLANS_NAMES = Object.keys(strings).filter((name) => name.startsWith('PLANS_'));
const STEP_9_NAMES = [
  ...PLANS_NAMES,
  'WHAT_DOES_SURRENDER_MEAN',
  'WHAT_DOES_REDEEM_MEAN',
  'WHAT_DOES_REAFFIRM_MEAN',
  'WHAT_DOES_EXPLAIN_MEAN',
  'WHAT_DOES_ASSUME_MEAN',
  'INTENTION_GAP_NONE',
  'INTENTION_GAP_UNDECIDED',
  'INTENTION_GAP_EXPLAIN',
  'LEASE_GAP_NONE',
  'LEASE_GAP_UNDECIDED',
  'CLAIM_TEXT_LABELS',
];

/** A name's words: the string, or each label of a record */
const wordsOf = (name: string): string[] => {
  const value = strings[name];
  return typeof value === 'string' ? [value] : Object.values(value as Record<string, string>);
};

describe("Your Plans' sentences are information, never advice", () => {
  it('checks every PLANS_ string the owner approved (E7, E8; the Review heading is not shipped)', () => {
    // A filter that silently matched fewer names can't pass the checks below
    expect(PLANS_NAMES).toHaveLength(15);
    expect(PLANS_NAMES).not.toContain('PLANS_REVIEW_HEADING');
  });

  it.each(STEP_9_NAMES)('%s exists in copy', (name) => {
    expect(strings[name]).toBeDefined();
    for (const words of wordsOf(name)) expect(typeof words).toBe('string');
  });

  it('labels each of the five texts a too-long note names', () => {
    expect(Object.keys(copy.CLAIM_TEXT_LABELS)).toEqual([
      'creditor_name',
      'collateral_description',
      'counterparty_name',
      'description',
      'explain',
    ]);
  });

  it.each(STEP_9_NAMES)('%s matches no advice pattern', (name) => {
    for (const words of wordsOf(name)) {
      for (const pattern of ADVICE) {
        expect(words, `${name} matched ${pattern}`).not.toMatch(pattern);
      }
    }
  });

  it.each(STEP_9_NAMES)('%s carries counsel mark C-37 on the line above', (name) => {
    expect(copySource).toMatch(new RegExp(`// DRAFT: counsel C-37\\nexport const ${name}\\b`));
  });
});
