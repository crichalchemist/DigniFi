import {
  MEANS_REBUTTAL_COURT,
  MEANS_REBUTTAL_IF,
  MEANS_REBUTTAL_IF_BELOW,
  MEANS_REBUTTAL_NOW,
} from '../../constants/copy';
import { cents, dollars, fromCents } from './money';

/** Line 39d as it would read with line 43's amounts taken off line 39c: (39c - sum) x 60, exact. */
export function rebuttalFigure(line39c: string, amounts: string[]): string {
  const left = amounts.reduce((rest, amount) => rest - cents(amount), cents(line39c));
  return fromCents(left * 60n);
}

/**
 * The three sentences under a presumption: line 39d now, as it would read, and who decides. A
 * figure below zero is said as "less than $0", never with a minus sign.
 */
export function rebuttalSentences(line39c: string, amounts: string[]): string[] {
  const figure = rebuttalFigure(line39c, amounts);
  const below = cents(figure) < 0n;
  const middle = below
    ? MEANS_REBUTTAL_IF_BELOW.replace('{amount}', dollars(figure.slice(1)))
    : MEANS_REBUTTAL_IF.replace('{amount}', dollars(figure));
  return [
    MEANS_REBUTTAL_NOW.replace('{amount}', dollars(rebuttalFigure(line39c, []))),
    middle,
    MEANS_REBUTTAL_COURT,
  ];
}
