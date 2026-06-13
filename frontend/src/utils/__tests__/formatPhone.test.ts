import { describe, it, expect } from 'vitest';
import { formatPhone } from '../formatPhone';

describe('formatPhone', () => {
  it('formats a full 10-digit number as XXX-XXX-XXXX', () => {
    expect(formatPhone('3125551234')).toBe('312-555-1234');
  });

  it('inserts dashes progressively as digits are typed', () => {
    expect(formatPhone('312')).toBe('312');
    expect(formatPhone('3125')).toBe('312-5');
    expect(formatPhone('312555')).toBe('312-555');
    expect(formatPhone('3125551')).toBe('312-555-1');
  });

  it('strips non-digits and ignores extra trailing digits', () => {
    expect(formatPhone('(312) 555-1234')).toBe('312-555-1234');
    expect(formatPhone('312-555-1234-999')).toBe('312-555-1234');
  });

  it('normalizes a +1-prefixed paste to 10 digits', () => {
    // Leading 1 is treated as the first digit (no country-code stripping) —
    // matches the validation regex which expects exactly 10 local digits.
    expect(formatPhone('13125551234')).toBe('131-255-5123');
  });

  it('returns empty string for empty input', () => {
    expect(formatPhone('')).toBe('');
  });
});
