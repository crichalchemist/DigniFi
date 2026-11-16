import { describe, it, expect } from 'vitest';
import { cents, dollars, fromCents } from '../money';

describe('amounts as the filer reads them', () => {
  it('reads cents exactly from the digits', () => {
    expect(cents('-100.00')).toBe(-10000n);
    expect(cents('1234.5')).toBe(123450n);
    expect(cents('90071992547409.93')).toBe(9007199254740993n);
    expect(fromCents(-50n)).toBe('-0.50');
    expect(fromCents(123450n)).toBe('1234.50');
  });

  it('refuses an amount with more than two places or an exponent', () => {
    for (const text of ['100.000', '1e3', '.5']) {
      expect(() => cents(text)).toThrow(RangeError);
    }
  });

  it('says a figure as the filer reads it', () => {
    expect(dollars('1234.5')).toBe('$1,234.50');
    expect(dollars('0')).toBe('$0.00');
  });
});
