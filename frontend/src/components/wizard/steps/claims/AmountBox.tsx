/**
 * An amount box that keeps what the filer typed (3c3 R14).
 *
 * The row holds a number, and a number can't tell "0" from "0.0" or an emptied box from "-", so
 * a box that showed the row's figure would rewrite the filer's keys as they type. This one shows
 * the text typed, and falls back to the row's figure until a key is pressed. A box holding only
 * part of a number ("-") keeps the row's figure and holds Continue back.
 */
import { useState } from 'react';
import { FormField } from '../../../common';
import { AMOUNT_NOT_A_NUMBER } from '../../../../constants/copy';
import { amountError, parseAmount } from '../../../../utils/parseAmount';
import { useReportPartial } from '../assets/useReportPartial';

interface AmountBoxProps {
  name: string;
  label: string;
  help?: string;
  value: number | null | undefined;
  required?: boolean;
  /** A stored 0 shows as an empty box: the amount owed's 0 means "not given yet" (B29) */
  zeroIsBlank?: boolean;
  /** DecimalField's max_digits on the column */
  maxDigits: number;
  /** A figure the server takes, or undefined for an emptied box */
  onValue: (value: number | undefined) => void;
  onPartialBox: (change: 1 | -1) => void;
}

export function AmountBox({
  name,
  label,
  help,
  value,
  required,
  zeroIsBlank,
  maxDigits,
  onValue,
  onPartialBox,
}: AmountBoxProps) {
  // null shows the row's figure; a string is what the filer typed
  const [typed, setTyped] = useState<string | null>(null);
  const [partial, setPartial] = useState(false);
  const [refused, setRefused] = useState<string>();
  useReportPartial(partial, onPartialBox);

  const stored =
    value === null || value === undefined || (zeroIsBlank && value === 0) ? '' : String(value);
  return (
    <FormField
      label={label}
      name={name}
      type="number"
      inputMode="decimal"
      min="0"
      step="0.01"
      placeholder="0.00"
      required={required}
      // Blank while partial, so React leaves the keys typed so far in the box
      value={partial ? '' : (typed ?? stored)}
      // onInput, since onChange skips an event whose value is unchanged: "-" and an emptied box
      // both read as "", so the Backspace that empties the box would go unheard
      onInput={(e) => {
        if (e.currentTarget.validity.badInput) {
          setPartial(true);
          return;
        }
        setPartial(false);
        const text = e.currentTarget.value;
        setTyped(text);
        const parsed = parseAmount(text);
        const error = amountError(parsed, maxDigits);
        setRefused(error);
        if (error === undefined) onValue(parsed);
      }}
      error={partial ? AMOUNT_NOT_A_NUMBER : refused}
      helpText={help}
    />
  );
}
