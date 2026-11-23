/**
 * UPL check on Schedule I's and Schedule J's sentences in the wizard (forms step 4c)
 *
 * DigniFi gives legal information, never advice. The question, the gap sentences, the pay stub
 * hint and the upload help must never tell a filer what to do about their case or what will
 * happen. The forms' own words live in formText.ts and are not checked here. The ADVICE list is
 * copied whole from upl-petition-copy.test.ts, with no carve-out.
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
  /\byou will qualify\b/i,
  /\byou will probably\b/i,
  /\byou are eligible\b/i,
  /\bthis is the best option\b/i,
  /\byou need to file\b/i,
  /\bpaid first\b/i,
  /\bis (a )?priority\b/i,
  /\bpriority claim/i,
];

const strings = copy as Record<string, unknown>;

// Every string with one of the two prefixes, found by prefix so a new one is checked too
const NAMES = Object.keys(strings).filter(
  (name) =>
    (name.startsWith('SCHEDULE_I_') || name.startsWith('PAYSTUB_')) &&
    typeof strings[name] === 'string'
);

// The sentences 4c added outside the two prefixes (W16's changed note)
const OTHER_NAMES = ['FEE_OTHER_LINES_NOTE'];

describe("Schedule I's and Schedule J's sentences are information, never advice", () => {
  it('checks every SCHEDULE_I_ and PAYSTUB_ string (16 of them, the labels record apart)', () => {
    // W1-W3 (3), W4 and W17 (2), W5-W7 (3), W8-W15 (8), so a filter that silently matched fewer
    // names can't pass the advice check below
    expect(NAMES).toHaveLength(16);
    expect(NAMES).toContain('SCHEDULE_I_DETAIL_TOO_LONG');
    expect(NAMES).toContain('PAYSTUB_EMPLOYER_HINT');
    expect(NAMES).toContain('PAYSTUB_UPLOAD_HELP');
  });

  it.each([...NAMES, ...OTHER_NAMES])('%s matches no advice pattern', (name) => {
    const text = String(strings[name]);
    for (const pattern of ADVICE) {
      expect(text, `${name} matched ${pattern}`).not.toMatch(pattern);
    }
  });

  it('checks every label too, which the server fills in as {label}', () => {
    const labels = strings.SCHEDULE_I_TEXT_LABELS as Record<string, string>;
    expect(Object.keys(labels)).toHaveLength(19);
    for (const [key, text] of Object.entries(labels)) {
      for (const pattern of ADVICE) {
        expect(text, `${key} matched ${pattern}`).not.toMatch(pattern);
      }
    }
  });

  it.each([...NAMES, ...OTHER_NAMES, 'SCHEDULE_I_TEXT_LABELS'])(
    '%s carries counsel mark C-42 on the line above',
    (name) => {
      expect(copySource).toMatch(new RegExp(`// DRAFT: counsel C-42\\nexport const ${name}\\b`));
    }
  );

  it('uses only the placeholders the server and the step fill in', () => {
    // {label} and {form} in the too-long template, {name} in the pay stub hint
    const allowed: Record<string, string[]> = {
      SCHEDULE_I_DETAIL_TOO_LONG: ['{label}', '{form}'],
      PAYSTUB_EMPLOYER_HINT: ['{name}'],
    };
    for (const name of NAMES) {
      const found = String(strings[name]).match(/\{\w+\}/g) ?? [];
      const ok = allowed[name] ?? [];
      for (const placeholder of found)
        expect(ok, `${name} has ${placeholder}`).toContain(placeholder);
    }
  });

  it("says Schedule I prints one employer, in the owner's words (W3)", () => {
    expect(copy.SCHEDULE_I_ONE_EMPLOYER).toBe(
      'DigniFi prints one employer on Schedule I. The form asks you to attach a separate page for any other job.'
    );
  });

  it('no longer says line 8 is left blank on Form 103B, which prints from line 11 now (W16)', () => {
    expect(copy.FEE_OTHER_LINES_NOTE).not.toMatch(/line 8/i);
  });
});
