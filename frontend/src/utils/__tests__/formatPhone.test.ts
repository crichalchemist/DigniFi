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

  it('strips a leading +1 country code from an 11-digit paste', () => {
    // Pasting from phone contacts (e.g. "+1 (312) 555-1234") must keep the 10
    // local digits, not drop the last one.
    expect(formatPhone('+1 (312) 555-1234')).toBe('312-555-1234');
    expect(formatPhone('13125551234')).toBe('312-555-1234');
  });

  it('keeps a leading 1 that is part of a 10-digit local number', () => {
    // A genuine area code starting with 1 is not a country code (only an
    // 11-digit "1XXXXXXXXXX" is treated as +1).
    expect(formatPhone('1235551234')).toBe('123-555-1234');
  });

  it('returns empty string for empty input', () => {
    expect(formatPhone('')).toBe('');
  });
});
