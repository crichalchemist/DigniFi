import { describe, it, expect } from 'vitest';
import { AMOUNT_DECIMALS, AMOUNT_NEGATIVE, AMOUNT_TOO_LARGE } from '../../constants/copy';
import { amountError, decimalToNumber, hydrateAmounts, parseAmount } from '../parseAmount';

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

  it('returns undefined for a number too large to hold, as for junk, so Infinity is never saved', () => {
    // Income sent Infinity as null, stored as empty; Expenses got a 400
    expect(parseAmount('1e400')).toBeUndefined();
    expect(parseAmount('-1e400')).toBeUndefined();
    expect(parseAmount('Infinity')).toBeUndefined();
  });
});

describe('decimalToNumber', () => {
  it('turns the decimal strings the API sends into numbers the steps can add', () => {
    expect(decimalToNumber('2500.00')).toBe(2500);
    expect(decimalToNumber('100.50')).toBe(100.5);
  });

  it('keeps a saved 0 as 0, so it does not show as blank', () => {
    expect(decimalToNumber('0.00')).toBe(0);
    expect(decimalToNumber(0)).toBe(0);
  });

  it('passes through a number the filer typed', () => {
    expect(decimalToNumber(12.5)).toBe(12.5);
  });

  it('never yields NaN: a value it cannot read becomes an empty field', () => {
    for (const value of ['abc', '', null, undefined, Number.NaN, Number.POSITIVE_INFINITY, {}]) {
      expect(decimalToNumber(value)).toBeUndefined();
    }
  });
});

describe('hydrateAmounts', () => {
  it('converts only the listed amount fields and leaves the rest of the row alone', () => {
    const row = { id: 7, creditor_name: 'Chase', amount_owed: '2500.00', notes: '42' };
    expect(hydrateAmounts(row, ['amount_owed', 'monthly_payment'])).toEqual({
      id: 7,
      creditor_name: 'Chase',
      amount_owed: 2500,
      notes: '42',
    });
  });

  it('does not add amount fields the server did not send', () => {
    const hydrated = hydrateAmounts({ amount_owed: '1.00' }, ['amount_owed', 'monthly_payment']);
    expect('monthly_payment' in hydrated).toBe(false);
  });

  it('leaves the session data it was given untouched', () => {
    const row = { amount_owed: '2500.00' };
    hydrateAmounts(row, ['amount_owed']);
    expect(row.amount_owed).toBe('2500.00');
  });
});

describe('amountError', () => {
  it('accepts dollars and cents, and $0', () => {
    expect(amountError(12.34, 10)).toBeUndefined();
    expect(amountError(0, 10)).toBeUndefined();
  });

  it('says nothing about a blank box', () => {
    expect(amountError(undefined, 10)).toBeUndefined();
  });

  it('refuses a negative amount, as the server does', () => {
    expect(amountError(-1, 10)).toBe(AMOUNT_NEGATIVE);
  });

  it('asks for dollars and cents when an amount has more than 2 decimal places', () => {
    expect(amountError(12.345, 10)).toBe(AMOUNT_DECIMALS);
  });

  it('takes the largest amount a 10-digit box stores and refuses one cent more', () => {
    expect(amountError(99999999.99, 10)).toBeUndefined();
    expect(amountError(100000000, 10)).toBe(AMOUNT_TOO_LARGE);
  });

  it('takes the largest amount a 12-digit box stores and refuses one cent more', () => {
    expect(amountError(9999999999.99, 12)).toBeUndefined();
    expect(amountError(10000000000, 12)).toBe(AMOUNT_TOO_LARGE);
  });

  it('names one problem at a time: negative first, then decimals, then size', () => {
    expect(amountError(-100000000.123, 10)).toBe(AMOUNT_NEGATIVE);
    expect(amountError(100000000.123, 10)).toBe(AMOUNT_DECIMALS);
  });
});
