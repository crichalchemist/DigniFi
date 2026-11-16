import { describe, expect, it } from 'vitest';
import { formatMonthYear } from '../formatMonthYear';

describe('formatMonthYear', () => {
  it('names the month and year of an ISO date, as the string says it', () => {
    expect(formatMonthYear('2026-10-16')).toBe('October 2026');
  });

  it('keeps the first of a month in that month, whatever the time zone', () => {
    expect(formatMonthYear('2027-01-01')).toBe('January 2027');
  });
});
