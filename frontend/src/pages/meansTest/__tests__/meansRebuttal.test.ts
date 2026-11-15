import { describe, it, expect } from 'vitest';
import raw from '../meansRebuttalCases.json?raw';
import { rebuttalFigure, rebuttalSentences } from '../meansRebuttal';

interface Case {
  name: string;
  line_39c: string;
  amounts: string[];
  figure: string;
}

// The same table apps/eligibility/tests/test_means_case_files.py runs against the server.
const cases: Case[] = JSON.parse(raw);

describe('the line 39d figure with line 43 allowed', () => {
  it('has the whole case file, so an emptied file cannot pass vacuously', () => {
    expect(cases.length).toBeGreaterThanOrEqual(5);
  });

  it.each(cases)('$name', (testCase) => {
    expect(rebuttalFigure(testCase.line_39c, testCase.amounts)).toBe(testCase.figure);
  });

  it('says less than $0, never a minus sign, when the figure is below zero', () => {
    const sentences = rebuttalSentences('2188.40', ['3000.00']);
    expect(sentences[1]).toBe(
      'If the court allowed the amounts on line 43, line 39d would be $48,696.00 less than $0.'
    );
    expect(sentences.join(' ')).not.toContain('-');
  });

  it('says line 39d is now 39c times 60', () => {
    expect(rebuttalSentences('2188.40', ['400.00'])[0]).toBe('Your line 39d is now $131,304.00.');
  });

  it('says $0.00, not less than $0, when the amounts bring 39d to exactly zero', () => {
    expect(rebuttalSentences('400.00', ['400.00'])[1]).toBe(
      'If the court allowed the amounts on line 43, line 39d would be $0.00.'
    );
  });
});
