/**
 * Reading Level Validation Tests
 *
 * Validates that all user-facing copy meets the 6th-8th grade
 * Flesch-Kincaid reading level target. Uses a 2-grade buffer
 * because legal terms (bankruptcy, eligibility) inflate scores.
 */

import * as copy from '../constants/copy';
import * as upl from '../constants/upl';
import rawCases from './readingLevelCases.json?raw';

// ============================================================================
// Flesch-Kincaid Grade Level implementation (mirrors backend)
// ============================================================================

function countSyllables(word: string): number {
  const w = word.toLowerCase().trim();
  if (!w) return 0;
  if (w.length <= 3) return 1;

  let processed = w;
  // Remove trailing silent 'e' (but not 'le' endings like "candle")
  if (processed.endsWith('e') && !processed.endsWith('le')) {
    processed = processed.slice(0, -1);
  }

  const vowelGroups = processed.match(/[aeiouy]+/g);
  return Math.max(vowelGroups?.length ?? 0, 1);
}

function splitSentences(text: string): string[] {
  return text.split(/[.!?]+/).filter((s) => s.trim().length > 0);
}

function extractWords(text: string): string[] {
  return text.match(/[a-zA-Z]+/g) ?? [];
}

function fleschKincaidGrade(text: string): number {
  const sentences = splitSentences(text);
  const words = extractWords(text);

  if (words.length === 0 || sentences.length === 0) return 0;

  const totalSyllables = words.reduce((sum, w) => sum + countSyllables(w), 0);

  return 0.39 * (words.length / sentences.length) + 11.8 * (totalSyllables / words.length) - 15.59;
}

// ============================================================================
// Test configuration
// ============================================================================

const TARGET_GRADE = 7;
const BUFFER = 2; // Legal terms inflate scores
const MAX_GRADE = TARGET_GRADE + BUFFER; // Grade 9

// ============================================================================
// Collect all user-facing strings
// ============================================================================

type TextEntry = { label: string; text: string };

// A value that is one whole link: the page shows its link text, which is scored, never the address
// itself, whose words are the court's and only split into syllables (4b, PF2-T9-3)
const WHOLE_URL = /^https:\/\/\S+$/;
const UNSCORED_URLS = Object.entries(copy)
  .filter(([, value]) => typeof value === 'string' && WHOLE_URL.test(value))
  .map(([key]) => key);

function collectCopyStrings(): TextEntry[] {
  const entries: TextEntry[] = [];

  for (const [key, value] of Object.entries(copy)) {
    if (typeof value === 'string') {
      if (UNSCORED_URLS.includes(key)) continue;
      entries.push({ label: `copy.${key}`, text: value });
    } else if (typeof value === 'object' && value !== null) {
      // Handle STEP_LABELS-style objects
      for (const [subKey, subValue] of Object.entries(value)) {
        if (typeof subValue === 'string') {
          entries.push({ label: `copy.${key}.${subKey}`, text: subValue });
        }
      }
    }
  }

  return entries;
}

function collectUPLStrings(): TextEntry[] {
  const entries: TextEntry[] = [];

  for (const [key, value] of Object.entries(upl)) {
    if (typeof value === 'string' && key.startsWith('UPL_') && !key.includes('ARIA')) {
      entries.push({ label: `upl.${key}`, text: value });
    }
  }

  return entries;
}

// ============================================================================
// Tests
// ============================================================================

describe('Reading Level Validation', () => {
  const allTexts = [...collectCopyStrings(), ...collectUPLStrings()];

  // Filter to only strings long enough to score meaningfully (>= 5 words)
  const scorableTexts = allTexts.filter(({ text }) => extractWords(text).length >= 5);

  it('has strings to validate', () => {
    expect(scorableTexts.length).toBeGreaterThan(0);
  });

  it('leaves unscored only the three court pages linked by name', () => {
    // A new address is a deliberate edit here, so no sentence can slip past the score as a link
    expect(UNSCORED_URLS.sort()).toEqual([
      'COURT_FORM_101A_URL',
      'COURT_FORM_101B_URL',
      'FORM_103A_URL',
    ]);
  });

  describe.each(scorableTexts)('$label', ({ text }) => {
    it(`is at or below grade ${MAX_GRADE}`, () => {
      const grade = fleschKincaidGrade(text);
      expect(grade).toBeLessThanOrEqual(MAX_GRADE);
    });
  });

  it('summary: all user-facing text meets reading level target', () => {
    const failures: string[] = [];

    for (const { label, text } of scorableTexts) {
      const grade = fleschKincaidGrade(text);
      if (grade > MAX_GRADE) {
        failures.push(`${label}: grade ${grade.toFixed(1)}`);
      }
    }

    if (failures.length > 0) {
      throw new Error(
        `${failures.length} text(s) exceed grade ${MAX_GRADE}:\n` +
          failures.map((f) => `  - ${f}`).join('\n')
      );
    }
  });
});

describe('Exemptions page gap sentences', () => {
  // 3g1 spec 5.5: a gap sentence scores grade 8.4 or below, under the page's general 9
  const GAP_MAX_GRADE = 8.4;
  const gaps = Object.entries(copy).filter(
    (entry): entry is [string, string] =>
      entry[0].startsWith('EXEMPTION_GAP_') && typeof entry[1] === 'string'
  );

  it('finds every gap sentence', () => {
    expect(gaps).toHaveLength(12);
  });

  it.each(gaps)(`%s is at or below grade ${GAP_MAX_GRADE}`, (_name, text) => {
    expect(fleschKincaidGrade(text)).toBeLessThanOrEqual(GAP_MAX_GRADE);
  });
});

describe('Your Plans sentences as the filer reads them, a name filled in', () => {
  // E7 approved INTENTION_GAP_NONE at 8.6 and LEASE_GAP_NONE at 8.5 "with a real name": scored
  // above with the literal {name}, so here with the personas' own Demo creditors and lessor
  const names = [
    'Crestway Auto Credit',
    'Kestrel Auto Finance',
    'Harrowgate Home Loans',
    'Northlight Auto Leasing',
  ];
  const gaps = Object.entries(copy).filter(
    (entry): entry is [string, string] =>
      /^(INTENTION|LEASE)_GAP_/.test(entry[0]) && typeof entry[1] === 'string'
  );

  it('finds every gap sentence', () => {
    expect(gaps).toHaveLength(5);
  });

  describe.each(gaps)('%s', (_gap, sentence) => {
    it.each(names)(`with %s is at or below grade ${MAX_GRADE}`, (name) => {
      expect(fleschKincaidGrade(sentence.replace('{name}', name))).toBeLessThanOrEqual(MAX_GRADE);
    });
  });

  // The too-long sentence (E4, E8) with each label and two forms named, its longest shape
  it.each(Object.entries(copy.CLAIM_TEXT_LABELS))(
    `the too-long sentence for %s is at or below grade ${MAX_GRADE}`,
    (_key, label) => {
      const sentence = copy.SCHEDULE_I_DETAIL_TOO_LONG.replace('{label}', label).replace(
        '{form}',
        'Form 108 and Schedule D'
      );
      expect(fleschKincaidGrade(sentence)).toBeLessThanOrEqual(MAX_GRADE);
    }
  );
});

describe('Shared cases with the backend scorer', () => {
  // test_exemption_catalog.py scores the same file with the backend's formula (P9).
  const cases = JSON.parse(rawCases) as { text: string; grade: number }[];

  it.each(cases)('scores "$text" as the backend does', ({ text, grade }) => {
    expect(Number(fleschKincaidGrade(text).toFixed(1))).toBe(grade);
  });
});
