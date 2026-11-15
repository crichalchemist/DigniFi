import { useState } from 'react';
import { FormField } from '../../components/common';
import { AMOUNT_NOT_A_NUMBER } from '../../constants/copy';
import { amountError, parseAmount } from '../../utils/parseAmount';

interface AmountBoxProps {
  name: string;
  label: string;
  /** The page's figure: a two-place decimal string, or null while unanswered or unreadable */
  value: string | null;
  /** The figure to the cent, or null for an empty, part-typed or refused box (R25) */
  onChange: (value: string | null) => void;
  /** Shown only while the box has no reason of its own */
  error?: string;
}

/**
 * An amount box that keeps the typed text itself, starting from `value` when it mounts. The page
 * holds null for a box it can't read or a figure the server would refuse, and a box drawn from that
 * null would lose the keys typed so far, and the reason with it. Key a row's boxes by the row.
 */
export function AmountBox({ name, label, value, onChange, error }: AmountBoxProps) {
  const [text, setText] = useState(value ?? '');
  const [partial, setPartial] = useState(false);

  const read = (box: HTMLInputElement) => {
    const badInput = box.validity.badInput;
    setText(box.value);
    setPartial(badInput);
    if (badInput) {
      onChange(null);
      return;
    }
    const amount = parseAmount(box.value);
    onChange(
      amount === undefined || amountError(amount, 12) !== undefined ? null : amount.toFixed(2)
    );
  };

  const reason = partial ? AMOUNT_NOT_A_NUMBER : amountError(parseAmount(text), 12);

  return (
    <FormField
      label={label}
      name={name}
      type="number"
      min="0"
      step="0.01"
      value={text}
      // onInput too: onChange skips the Backspace that empties a part-typed box ('' to '')
      onInput={(event) => read(event.currentTarget)}
      onChange={(event) => read(event.target)}
      error={reason ?? error}
    />
  );
}
