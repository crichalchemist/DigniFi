/**
 * UPL check on the frame's sentences (forms step 4a)
 *
 * DigniFi gives legal information, never advice. The sentences the gaps list, the section intro,
 * the public-record notice and the definition expander print must never tell a filer what to do or
 * what will happen. The ADVICE list is copied whole from upl-claims-copy.test.ts.
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

const FRAME_NAMES = [
  'REVIEW_NOTHING_MISSING',
  'REVIEW_GAPS_UNAVAILABLE',
  'DASHBOARD_GATES_ONE',
  'DASHBOARD_GATES_MANY',
  'DASHBOARD_GAPS_ONE',
  'DASHBOARD_GAPS_MANY',
  'SECTION_INTRO_TIME',
  'SECTION_INTRO_PAUSE',
  'PUBLIC_RECORD_NOTICE',
  'WHAT_DOES_THIS_MEAN',
];

describe('the frame sentences are information, never advice', () => {
  it.each(FRAME_NAMES)('%s exists in copy', (name) => {
    expect(typeof (copy as Record<string, unknown>)[name]).toBe('string');
  });

  it.each(FRAME_NAMES)('%s matches no advice pattern', (name) => {
    const text = String((copy as Record<string, unknown>)[name]);
    for (const pattern of ADVICE) {
      expect(text, `${name} matched ${pattern}`).not.toMatch(pattern);
    }
  });

  it('PUBLIC_RECORD_NOTICE carries counsel mark C-40 on the line above', () => {
    expect(copySource).toMatch(/\/\/ DRAFT: counsel C-40\nexport const PUBLIC_RECORD_NOTICE\b/);
  });
});
