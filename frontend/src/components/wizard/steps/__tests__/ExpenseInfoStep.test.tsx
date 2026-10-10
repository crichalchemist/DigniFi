import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import { ExpenseInfoStep } from '../ExpenseInfoStep';

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

function renderStep() {
  const onDataChange = vi.fn();
  const { container } = render(
    <ExpenseInfoStep initialData={{}} onDataChange={onDataChange} onValidationChange={vi.fn()} />
  );
  const inputNamed = (name: string) =>
    container.querySelector(`input[name="${name}"]`) as HTMLInputElement | null;
  const lastEmitted = () =>
    onDataChange.mock.calls[onDataChange.mock.calls.length - 1][0] as Record<string, unknown>;
  return { inputNamed, lastEmitted };
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
});
