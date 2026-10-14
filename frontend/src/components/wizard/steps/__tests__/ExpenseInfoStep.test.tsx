import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import { ExpenseInfoStep } from '../ExpenseInfoStep';
import type { ExpenseInfo } from '../../../../types/api';

// The names ExpenseInfo stores and Schedule J, Form 122A-2 and the means test read. DRF
// drops any other name without an error, which is how car, food and other costs once
// saved as $0 (DIG-45).
const COURT_FORM_EXPENSE_NAMES = [
  'rent_or_mortgage',
  'utilities',
  'home_maintenance',
  'vehicle_payment',
  'vehicle_insurance',
  'vehicle_maintenance',
  'food_and_groceries',
  'clothing',
  'medical_expenses',
  'childcare',
  'child_support_paid',
  'insurance_not_deducted',
  'other_expenses',
];

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
  return { inputNamed, lastEmitted, canContinue };
}

describe('ExpenseInfoStep', () => {
  it('saves every expense under the name the court forms read', () => {
    const { inputNamed, lastEmitted } = renderStep();

    COURT_FORM_EXPENSE_NAMES.forEach((name, index) => {
      const input = inputNamed(name);
      expect(input, `a box named ${name}`).not.toBeNull();
      fireEvent.change(input!, { target: { value: String((index + 1) * 10) } });
    });

    const emitted = lastEmitted();
    COURT_FORM_EXPENSE_NAMES.forEach((name, index) => {
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

  it('counts clothing and child support paid in the monthly total', () => {
    const { inputNamed, lastEmitted } = renderStep();

    fireEvent.change(inputNamed('rent_or_mortgage')!, { target: { value: '1000' } });
    fireEvent.change(screen.getByLabelText('Clothing'), { target: { value: '60' } });
    fireEvent.change(screen.getByLabelText('Child Support Paid'), { target: { value: '200' } });

    expect(screen.getByText('$1,260.00')).toBeInTheDocument();
    expect(lastEmitted().total_monthly_expenses).toBe(1260);
  });

  // The server stores each amount as DecimalField(max_digits=10, decimal_places=2) and refuses
  // anything else, so the box says what is wrong before Continue saves it (W-9)
  it('asks for dollars and cents beside a box with a third decimal place, and blocks Continue', () => {
    const { canContinue } = renderStep();

    fireEvent.change(screen.getByLabelText('Clothing'), { target: { value: '12.345' } });

    expect(screen.getByLabelText('Clothing')).toHaveAccessibleDescription(
      /^Please enter dollars and cents, like 1250\.50 /
    );
    expect(canContinue()).toBe(false);
  });

  it('says beside the box that an amount over $99,999,999.99 is too large, and blocks Continue', () => {
    const { canContinue } = renderStep();

    fireEvent.change(screen.getByLabelText('Clothing'), { target: { value: '100000000' } });

    expect(screen.getByLabelText('Clothing')).toHaveAccessibleDescription(
      /^This amount is too large\. Please check it /
    );
    expect(canContinue()).toBe(false);
  });

  it('takes the largest amount the server stores, $99,999,999.99', () => {
    const { lastEmitted, canContinue } = renderStep();

    fireEvent.change(screen.getByLabelText('Clothing'), { target: { value: '99999999.99' } });

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
