import { describe, it, expect } from 'vitest';
import raw from '../meansRowsCases.json?raw';
import { debtLines, slotCandidates, type RowsInput } from '../meansRows';

interface Case extends RowsInput {
  name: string;
  expect: { candidates: string[] | null; lines: Record<string, string | null> };
}

// The same table apps/eligibility/tests/test_means_case_files.py runs against the server.
const cases: Case[] = JSON.parse(raw);

describe('the grouping of vehicles and secured debts', () => {
  it('has the whole case file, so an emptied file cannot pass vacuously', () => {
    expect(cases.length).toBeGreaterThanOrEqual(17);
  });

  it.each(cases)('$name', (testCase) => {
    expect(slotCandidates(testCase)).toEqual(testCase.expect.candidates);
    expect(debtLines(testCase)).toEqual(testCase.expect.lines);
  });

  it("a spouse row the page hasn't saved yet counts as the spouse's", () => {
    const input: RowsInput = {
      marital_status: 'married_together',
      spouse_vehicles_answer: 'yes',
      spouse_loans_answer: 'no',
      vehicles: [{ ref: 'new-1', leased: true, claimed: true }],
      debts: [],
      vehicle_choice: null,
    };
    expect(slotCandidates(input)).toEqual(['new-1']);
  });
});
