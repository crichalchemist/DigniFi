import { cents, fromCents } from './money';

const MULTIPLIER = /^\d+(?:\.(\d+))?$/;

/**
 * Line 36's product, the browser's copy of `plan_product`: the payment times the U.S. Trustee's
 * percentage, in integer cents, a half cent rounded to the even cent. No float.
 */
export function planProduct(payment: string, multiplier: string): string {
  const match = MULTIPLIER.exec(multiplier);
  if (!match) throw new RangeError('A multiplier must be digits with a decimal point at most.');
  const places = (match[1] ?? '').length;
  const scaled = BigInt(multiplier.replace('.', ''));
  const numerator = cents(payment) * scaled;
  const denominator = 100n * 10n ** BigInt(places);
  const negative = numerator < 0n;
  const magnitude = negative ? -numerator : numerator;
  let quotient = magnitude / denominator;
  const twice = (magnitude % denominator) * 2n;
  if (twice > denominator || (twice === denominator && quotient % 2n === 1n)) quotient += 1n;
  return fromCents(negative ? -quotient : quotient);
}
