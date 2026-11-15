import { describe, it, expect } from 'vitest';
import raw from '../meansProductCases.json?raw';
import { planProduct } from '../meansProduct';

interface Case {
  name: string;
  payment: string;
  multiplier: string;
  product: string;
}

// The same table apps/eligibility/tests/test_means_case_files.py runs against the server.
const cases: Case[] = JSON.parse(raw);

describe("line 36's product", () => {
  it('has the whole case file, so an emptied file cannot pass vacuously', () => {
    expect(cases.length).toBeGreaterThanOrEqual(5);
  });

  it.each(cases)('$name', (testCase) => {
    expect(planProduct(testCase.payment, testCase.multiplier)).toBe(testCase.product);
  });
});
