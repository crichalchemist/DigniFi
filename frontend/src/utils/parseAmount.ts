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
  return Number.isNaN(parsed) ? undefined : parsed;
}
