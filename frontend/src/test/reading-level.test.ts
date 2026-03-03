/**
 * Reading Level Validation Tests
 *
 * Validates that all user-facing copy meets the 6th-8th grade
 * Flesch-Kincaid reading level target. Uses a 2-grade buffer
 * because legal terms (bankruptcy, eligibility) inflate scores.
 */

import * as copy from '../constants/copy';
import * as upl from '../constants/upl';

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

  return (
    0.39 * (words.length / sentences.length) +
    11.8 * (totalSyllables / words.length) -
    15.59
  );
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

function collectCopyStrings(): TextEntry[] {
  const entries: TextEntry[] = [];

  for (const [key, value] of Object.entries(copy)) {
    if (typeof value === 'string') {
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
  const scorableTexts = allTexts.filter(
    ({ text }) => extractWords(text).length >= 5,
  );

  it('has strings to validate', () => {
    expect(scorableTexts.length).toBeGreaterThan(0);
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
          failures.map((f) => `  - ${f}`).join('\n'),
      );
    }
  });
});
