import { formatFigure } from '../../components/wizard/steps/claims/linkedPayments';

const AMOUNT = /^(-?)(\d+)(?:\.(\d{1,2}))?$/;

/**
 * An amount's cents, read exactly from its digits, never through a float. Takes only a decimal
 * string with at most two places: the page's boxes hand their parent `parseAmount(text).toFixed(2)`.
 */
export function cents(amount: string): bigint {
  const match = AMOUNT.exec(amount);
  if (!match) throw new RangeError('An amount must be digits with at most two places.');
  const [, sign, whole, fraction = ''] = match;
  const total = BigInt(whole) * 100n + BigInt(fraction.padEnd(2, '0'));
  return sign === '-' ? -total : total;
}

/** Cents back to a two-place decimal string ("-0.50" keeps its sign). */
export function fromCents(value: bigint): string {
  const negative = value < 0n;
  const magnitude = negative ? -value : value;
  const text = `${magnitude / 100n}.${(magnitude % 100n).toString().padStart(2, '0')}`;
  return negative ? `-${text}` : text;
}

/** A figure as the filer reads it: "1234.5" is "$1,234.50". */
export function dollars(amount: string): string {
  const value = cents(amount);
  const negative = value < 0n;
  const magnitude = negative ? -value : value;
  return `${negative ? '-' : ''}$${formatFigure(Number(magnitude) / 100)}`;
}
