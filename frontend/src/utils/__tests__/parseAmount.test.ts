import { describe, it, expect } from 'vitest';
import { parseAmount } from '../parseAmount';

describe('parseAmount', () => {
  it('preserves an explicit 0 (the bug: 0 must not blank out)', () => {
    // Regression: `value || ''` blanked a typed 0 because 0 is falsy.
    expect(parseAmount('0')).toBe(0);
    expect(parseAmount('0.00')).toBe(0);
  });

  it('returns undefined for blank input so an untouched field stays empty', () => {
    expect(parseAmount('')).toBeUndefined();
    expect(parseAmount('   ')).toBeUndefined();
  });

  it('parses positive and decimal amounts', () => {
    expect(parseAmount('1250')).toBe(1250);
    expect(parseAmount('12.5')).toBe(12.5);
  });

  it('returns undefined for non-numeric junk rather than 0', () => {
    // Must be undefined, not 0 — otherwise junk would read as a real $0 answer.
    expect(parseAmount('abc')).toBeUndefined();
  });

  it('keeps a negative value so downstream validation can flag it', () => {
    expect(parseAmount('-5')).toBe(-5);
  });
});
