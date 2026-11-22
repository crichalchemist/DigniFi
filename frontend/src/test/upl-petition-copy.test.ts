/**
 * UPL check on Form 101's sentences in the wizard (forms step 4b)
 *
 * DigniFi gives legal information, never advice. The gap sentences, the "why we ask" lines, the
 * credit counseling and venue information, the hidden-answer lines, the public-record notice and
 * the Form 101A and 101B notice's own sentences must never tell a filer what to do or what will
 * happen. The form's own words live in
 * formText.ts and are not checked here. The ADVICE list is copied whole from
 * upl-frame-copy.test.ts, with no carve-out.
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

// Every gap sentence the step mirrors, found by prefix so a new one is checked too
const GAP_NAMES = Object.keys(strings).filter(
  (name) => name.startsWith('PETITION_GATE_') || name.startsWith('PETITION_DETAIL_')
);

// Every step 1 string named PETITION_ (the gaps, the questions in DigniFi's words, the row
// lists' Add, row and Remove labels), found by prefix so a new label is checked too
const PREFIXED_NAMES = Object.keys(strings).filter((name) => name.startsWith('PETITION_'));

const PETITION_NAMES = [
  ...PREFIXED_NAMES,
  'WHY_OTHER_NAMES',
  'WHY_ITIN',
  'WHY_OTHER_SSN',
  'WHY_MAILING',
  'COUNSELING_REQUIREMENT_INTRO',
  'VENUE_DIVISION_EASTERN',
  'VENUE_DIVISION_WESTERN',
  'LINE_12_FEEDS_107',
  'HIDDEN_ROWS_ONE',
  'HIDDEN_ROWS_MANY',
  'HIDDEN_ANSWERS',
  'SHOW_HIDDEN',
  'DELETE_HIDDEN',
  'HOME_ZIP_ERROR',
  'SSN_SAVED',
  'ITIN_SAVED',
  'OTHER_SSN_SAVED',
  'REPLACE_SAVED',
  'PUBLIC_RECORD_NOTICE',
  'PUBLIC_RECORD_NOTICE_WITH_CLERK',
  'CLERK_PHONE_EASTERN',
  'CLERK_PHONE_WESTERN',
  // Contracts & Leases' Form 101A and 101B notice: the leads and DigniFi's own sentences (4b)
  'FORM_101_LINE_11_LEAD',
  'FORM_101A_SAYS',
  'FORM_101A_NOT_YET',
  'FORM_101A_LINK',
  'FORM_101B_NOT_PREPARED',
  'FORM_101B_LINK',
];

// The notice's sentences and its two pages, each under the counsel mark (PF2-T9-3, PF2-T9-4)
const NOTICE_NAMES = [
  'FORM_101_LINE_11_LEAD',
  'FORM_101A_SAYS',
  'FORM_101A_NOT_YET',
  'FORM_101A_LINK',
  'COURT_FORM_101A_URL',
  'FORM_101B_NOT_PREPARED',
  'FORM_101B_LINK',
  'COURT_FORM_101B_URL',
];

describe("step 1's Form 101 sentences are information, never advice", () => {
  it('mirrors every gate and detail petition.py holds today (10 and 16)', () => {
    expect(GAP_NAMES.filter((name) => name.startsWith('PETITION_GATE_'))).toHaveLength(10);
    expect(GAP_NAMES.filter((name) => name.startsWith('PETITION_DETAIL_'))).toHaveLength(16);
  });

  it("checks every PETITION_ string, the row lists' twelve labels among them", () => {
    // 26 gap sentences, 3 questions in DigniFi's words and 12 Add, row and Remove labels, so a
    // filter that silently matched fewer names can't pass the advice check below
    expect(PREFIXED_NAMES).toHaveLength(41);
    expect(PREFIXED_NAMES).toContain('PETITION_ADD_OTHER_NAME');
    expect(PREFIXED_NAMES).toContain('PETITION_REMOVE_PENDING_CASE');
  });

  it.each(PETITION_NAMES)('%s exists in copy', (name) => {
    expect(typeof strings[name]).toBe('string');
  });

  it.each(PETITION_NAMES)('%s matches no advice pattern', (name) => {
    const text = String(strings[name]);
    for (const pattern of ADVICE) {
      expect(text, `${name} matched ${pattern}`).not.toMatch(pattern);
    }
  });

  it.each([
    'COUNSELING_REQUIREMENT_INTRO',
    'PUBLIC_RECORD_NOTICE',
    'PUBLIC_RECORD_NOTICE_WITH_CLERK',
    'VENUE_DIVISION_EASTERN',
    'VENUE_DIVISION_WESTERN',
    'PETITION_DETAIL_VENUE_REASON',
    ...NOTICE_NAMES,
  ])('%s carries counsel mark C-40 on the line above', (name) => {
    expect(copySource).toMatch(new RegExp(`// DRAFT: counsel C-40\\nexport const ${name}\\b`));
  });

  it.each([
    'PETITION_ASKED_AS_ITIN',
    'PETITION_ASKED_AS_OTHER_SSN',
    'PETITION_GATE_ITIN',
    'PETITION_GATE_OTHER_SSN',
    'PETITION_DETAIL_ITIN',
    'PETITION_DETAIL_ITIN_NINE',
    'PETITION_DETAIL_OTHER_SSN',
    'WHY_ITIN',
    'WHY_OTHER_SSN',
    'ITIN_SAVED',
    'OTHER_SSN_SAVED',
  ])('%s carries counsel mark C-44 on the line above', (name) => {
    expect(copySource).toMatch(new RegExp(`// DRAFT: counsel C-44\\nexport const ${name}\\b`));
  });

  it('no copy sentence carries a clerk number inside its text (4b-R6)', () => {
    const withNumber = Object.entries(strings).filter(
      ([name, value]) =>
        typeof value === 'string' &&
        !name.startsWith('CLERK_PHONE_') &&
        /\(\d{3}\) \d{3}-\d{4}/.test(value)
    );
    expect(withNumber).toEqual([]);
  });

  it('uses only the placeholders the server and the step fill in', () => {
    // {n} and {count} anywhere, {label} in the two too-long templates, {noun} and {forms} in the
    // row one (Q5, Q10)
    const allowed: Record<string, string[]> = {
      PETITION_DETAIL_TOO_LONG: ['{label}'],
      PETITION_DETAIL_TOO_LONG_ROW: ['{label}', '{noun}', '{n}', '{forms}'],
    };
    for (const name of PETITION_NAMES) {
      const found = String(strings[name]).match(/\{\w+\}/g) ?? [];
      const ok = allowed[name] ?? ['{n}', '{count}'];
      for (const placeholder of found)
        expect(ok, `${name} has ${placeholder}`).toContain(placeholder);
    }
  });
});
