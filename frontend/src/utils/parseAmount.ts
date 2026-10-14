import { AMOUNT_DECIMALS, AMOUNT_NEGATIVE, AMOUNT_TOO_LARGE } from '../constants/copy';

/**
 * Parse a currency/amount text input into a number.
 *
 * Returns `undefined` for blank or unparseable input so an untouched field
 * stays empty, while an explicit "0" is preserved as the number 0. This lets a
 * user either leave a money field blank or deliberately enter 0 — both are
 * valid answers on the intake (e.g. "no income from this source").
 *
 * Pairs with a `value={field ?? ''}` binding: `undefined` renders empty, `0`
 * renders "0". A falsy `field || ''` binding would wrongly blank a typed 0.
 */
export function parseAmount(value: string): number | undefined {
  const trimmed = value.trim();
  if (trimmed === '') return undefined;
  const parsed = Number.parseFloat(trimmed);
  // Not finite covers NaN and a number too large to hold ("1e400" is Infinity)
  return Number.isFinite(parsed) ? parsed : undefined;
}

/**
 * Convert a decimal from the API into a number for wizard state.
 *
 * DRF sends decimals as strings ("2500.00"), and the steps add and compare
 * amounts, so a string would join as text instead of adding. Anything that is not
 * a finite number becomes `undefined` (an empty field), never `NaN`.
 */
export function decimalToNumber(value: unknown): number | undefined {
  if (typeof value === 'number') return Number.isFinite(value) ? value : undefined;
  if (typeof value !== 'string') return undefined;
  const parsed = parseAmount(value);
  return parsed !== undefined && Number.isFinite(parsed) ? parsed : undefined;
}

/**
 * Return a copy of `row` with each listed amount converted by `decimalToNumber`.
 * Keys the row does not have stay absent, so a partial save never sends them.
 */
export function hydrateAmounts<T extends object>(row: T, keys: readonly string[]): T {
  const hydrated = { ...row } as Record<string, unknown>;
  for (const key of keys) {
    if (key in hydrated) hydrated[key] = decimalToNumber(hydrated[key]);
  }
  return hydrated as T;
}

/**
 * What is wrong with an amount the server would refuse, in the words shown beside its box, or
 * `undefined` when the server takes it (a blank box included). One problem at a time: negative,
 * then more than 2 decimal places, then too large.
 *
 * Every page sends its amounts to a DRF DecimalField with 2 decimal places and `maxDigits` digits
 * in all, so the largest it stores is 10 ** (maxDigits - 2) less one cent:
 * - Income (the ten INCOME_FIELDS) and Expenses (the thirteen EXPENSE_FIELDS): the IncomeInfo and
 *   ExpenseInfo models' DecimalField(max_digits=10, decimal_places=2), 99,999,999.99
 * - Fee waiver take-home pay: the serializer's DecimalField(max_digits=10, decimal_places=2,
 *   min_value=0), 99,999,999.99
 * - SOFA Gross Amount and Total Amount Paid: the serializers' DecimalField(max_digits=12,
 *   decimal_places=2, min_value=0), 9,999,999,999.99
 */
export function amountError(value: number | undefined, maxDigits: number): string | undefined {
  if (value === undefined) return undefined;
  if (value < 0) return AMOUNT_NEGATIVE;
  if (Number(value.toFixed(2)) !== value) return AMOUNT_DECIMALS;
  if (value >= 10 ** (maxDigits - 2)) return AMOUNT_TOO_LARGE;
  return undefined;
}
