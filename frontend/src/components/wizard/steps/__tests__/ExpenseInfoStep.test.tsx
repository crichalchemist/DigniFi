import { render, screen, fireEvent, within } from '@testing-library/react';
import { vi } from 'vitest';
import { ExpenseInfoStep } from '../ExpenseInfoStep';
import type { ExpenseInfo } from '../../../../types/api';
import { EXPENSE_FIELDS } from '../../../../types/api';
import {
  EXPENSE_LINE_WORDS,
  EXPENSE_SPECIFY_WORDS,
  LINE_3_QUESTION,
  LINE_4_GROUP_HEADING,
  LINE_15_GROUP_HEADING,
  LINE_20_GROUP_HEADING,
  NONCASH_EXPENSES_SENTENCE,
} from '../../../../constants/formText';
import { DOUBLE_COUNT_EXPENSES_NOTE, LINE_3_INFO } from '../../../../constants/copy';

// Every Schedule J amount ExpenseInfo stores and the forms and the means test read. DRF
// drops any other name without an error, which is how car, food and other costs once
// saved as $0 (DIG-45).

function renderStep(initialData: Partial<ExpenseInfo> = {}) {
  const onDataChange = vi.fn();
  const onValidationChange = vi.fn();
  const { container } = render(
    <ExpenseInfoStep
      initialData={initialData}
      onDataChange={onDataChange}
      onValidationChange={onValidationChange}
    />
  );
  const inputNamed = (name: string) =>
    container.querySelector(`input[name="${name}"]`) as HTMLInputElement | null;
  const lastEmitted = () =>
    onDataChange.mock.calls[onDataChange.mock.calls.length - 1][0] as Record<string, unknown>;
  // Whether the wizard lets the filer press Continue
  const canContinue = () =>
    onValidationChange.mock.calls[onValidationChange.mock.calls.length - 1][0] as boolean;
  return { container, inputNamed, lastEmitted, canContinue };
}

describe('ExpenseInfoStep', () => {
  it('saves every expense under the name the court forms read', () => {
    const { inputNamed, lastEmitted } = renderStep();

    EXPENSE_FIELDS.forEach((name, index) => {
      const input = inputNamed(name);
      expect(input, `a box named ${name}`).not.toBeNull();
      fireEvent.change(input!, { target: { value: String((index + 1) * 10) } });
    });

    const emitted = lastEmitted();
    EXPENSE_FIELDS.forEach((name, index) => {
      expect(emitted[name], name).toBe((index + 1) * 10);
    });
    for (const unknownName of [
      'car_payment',
      'car_insurance',
      'gas_transportation',
      'food_groceries',
      'other_necessary_expenses',
    ]) {
      expect(emitted).not.toHaveProperty(unknownName);
    }
  });

  it('asks every Schedule J line in its order and in its words', () => {
    const { container, inputNamed } = renderStep();
    const amounts = Array.from(
      container.querySelectorAll<HTMLInputElement>('input[type="number"]')
    );
    expect(amounts.map((box) => box.name)).toEqual([...EXPENSE_FIELDS]);
    for (const field of EXPENSE_FIELDS) {
      expect(inputNamed(field)).toHaveAccessibleName(EXPENSE_LINE_WORDS[field]);
    }
    for (const words of [
      LINE_4_GROUP_HEADING,
      LINE_15_GROUP_HEADING,
      LINE_20_GROUP_HEADING,
      NONCASH_EXPENSES_SENTENCE,
      DOUBLE_COUNT_EXPENSES_NOTE,
      LINE_3_INFO,
    ]) {
      expect(screen.getByText(words)).toBeInTheDocument();
    }
  });

  it('never answers Schedule J line 3 for the filer, and asks it before every amount', () => {
    const { inputNamed, lastEmitted } = renderStep();
    const line3 = screen.getByRole('group', { name: LINE_3_QUESTION });
    const [no, yes] = within(line3).getAllByRole('radio') as HTMLInputElement[]; // No first, then Yes (§5.2)
    expect([no.checked, yes.checked]).toEqual([false, false]);
    expect(lastEmitted().expenses_include_others ?? null).toBeNull();
    expect(
      line3.compareDocumentPosition(inputNamed('rent_or_mortgage')!) &
        Node.DOCUMENT_POSITION_FOLLOWING
    ).toBeTruthy();
    fireEvent.click(yes);
    expect(lastEmitted().expenses_include_others).toBe('yes');
  });

  it('adds all 26 amounts into the monthly total', () => {
    const { inputNamed, lastEmitted } = renderStep();
    for (const field of EXPENSE_FIELDS) {
      fireEvent.change(inputNamed(field)!, { target: { value: '1' } });
    }
    expect(screen.getByText('$26.00')).toBeInTheDocument();
    expect(lastEmitted().total_monthly_expenses).toBe(26);
  });

  it.each([
    ['taxes_not_deducted', 'taxes_specify'],
    ['support_others', 'support_others_specify'],
    ['other_expenses', 'other_expenses_specify'],
  ] as const)(
    'puts the Specify box for %s right after its amount, taking 100 characters',
    (amount, specify) => {
      const { container, inputNamed, lastEmitted } = renderStep();
      const names = Array.from(container.querySelectorAll<HTMLInputElement>('input')).map(
        (i) => i.name
      );
      expect(names.indexOf(specify)).toBe(names.indexOf(amount) + 1);
      expect(inputNamed(specify)).toHaveAccessibleName(EXPENSE_SPECIFY_WORDS[specify]);
      expect(inputNamed(specify)).toHaveAttribute('maxlength', '100');
      fireEvent.change(inputNamed(specify)!, {
        target: { value: 'IRS installment agreement, 2025 tax' },
      });
      expect(lastEmitted()[specify]).toBe('IRS installment agreement, 2025 tax');
    }
  );

  it('counts clothing and child support paid in the monthly total', () => {
    const { inputNamed, lastEmitted } = renderStep();

    fireEvent.change(inputNamed('rent_or_mortgage')!, { target: { value: '1000' } });
    fireEvent.change(screen.getByLabelText(EXPENSE_LINE_WORDS.clothing), {
      target: { value: '60' },
    });
    fireEvent.change(screen.getByLabelText(EXPENSE_LINE_WORDS.child_support_paid), {
      target: { value: '200' },
    });

    expect(screen.getByText('$1,260.00')).toBeInTheDocument();
    expect(lastEmitted().total_monthly_expenses).toBe(1260);
  });

  // The server stores each amount as DecimalField(max_digits=10, decimal_places=2) and refuses
  // anything else, so the box says what is wrong before Continue saves it (W-9)
  it('asks for dollars and cents beside a box with a third decimal place, and blocks Continue', () => {
    const { canContinue } = renderStep();

    fireEvent.change(screen.getByLabelText(EXPENSE_LINE_WORDS.clothing), {
      target: { value: '12.345' },
    });

    expect(screen.getByLabelText(EXPENSE_LINE_WORDS.clothing)).toHaveAccessibleDescription(
      /^Please enter dollars and cents, like 1250\.50 /
    );
    expect(canContinue()).toBe(false);
  });

  it('says beside the box that an amount over $99,999,999.99 is too large, and blocks Continue', () => {
    const { canContinue } = renderStep();

    fireEvent.change(screen.getByLabelText(EXPENSE_LINE_WORDS.clothing), {
      target: { value: '100000000' },
    });

    expect(screen.getByLabelText(EXPENSE_LINE_WORDS.clothing)).toHaveAccessibleDescription(
      /^This amount is too large\. Please check it /
    );
    expect(canContinue()).toBe(false);
  });

  it('takes the largest amount the server stores, $99,999,999.99', () => {
    const { lastEmitted, canContinue } = renderStep();

    fireEvent.change(screen.getByLabelText(EXPENSE_LINE_WORDS.clothing), {
      target: { value: '99999999.99' },
    });

    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(canContinue()).toBe(true);
    expect(lastEmitted().clothing).toBe(99999999.99);
  });

  // Coming back to the step, the wizard hands it the total it last added up, which no box shows
  it('lets a returning filer continue when the total their amounts add up to is not a whole cent', () => {
    const { canContinue } = renderStep({
      clothing: 10.1,
      utilities: 20.2,
      total_monthly_expenses: 10.1 + 20.2,
    });

    expect(canContinue()).toBe(true);
  });
});
