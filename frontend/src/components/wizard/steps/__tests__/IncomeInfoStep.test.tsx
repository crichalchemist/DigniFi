import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import { IncomeInfoStep } from '../IncomeInfoStep';
import type { IncomeInfo } from '../../../../types/api';

// The server stores only six months of income and reports their average. It never stores
// the per-source boxes, so a returning filer's data arrives with none of them (DIG-41).
const savedIncome: Partial<IncomeInfo> = {
  monthly_income: [3100, 3300, 3200, 3200, 3150, 3250],
  total_monthly_income: 3200,
};

const SAVED_TOTAL_NOTE =
  'Your saved total is $3,200.00 a month. We keep only the total, not the amount from each source, so the boxes below start empty. If you enter amounts below, they will replace the saved total.';

function renderStep(initialData: Partial<IncomeInfo>) {
  const onDataChange = vi.fn();
  render(
    <IncomeInfoStep
      initialData={initialData}
      onDataChange={onDataChange}
      onValidationChange={vi.fn()}
    />
  );
  const lastEmitted = () =>
    onDataChange.mock.calls[onDataChange.mock.calls.length - 1][0] as Partial<IncomeInfo>;
  return { lastEmitted };
}

describe('IncomeInfoStep', () => {
  it('shows a returning filer their saved income instead of $0', () => {
    renderStep(savedIncome);

    expect(screen.getByText(SAVED_TOTAL_NOTE)).toBeInTheDocument();
    expect(screen.getByText('$3,200.00')).toBeInTheDocument();
  });

  it('keeps each saved month exactly as stored when the filer changes nothing', () => {
    const { lastEmitted } = renderStep(savedIncome);

    expect(lastEmitted().monthly_income).toEqual([3100, 3300, 3200, 3200, 3150, 3250]);
  });

  it('replaces the saved total with the amounts the filer enters', () => {
    const { lastEmitted } = renderStep(savedIncome);

    fireEvent.change(screen.getByLabelText(/monthly wages/i), { target: { value: '2000' } });
    fireEvent.change(screen.getByLabelText(/social security/i), { target: { value: '500' } });

    expect(lastEmitted().monthly_income).toEqual([2500, 2500, 2500, 2500, 2500, 2500]);
    expect(screen.getByText('$2,500.00')).toBeInTheDocument();
    expect(screen.queryByText(SAVED_TOTAL_NOTE)).not.toBeInTheDocument();
  });

  it('lets a filer record $0 income in place of a saved total', () => {
    const { lastEmitted } = renderStep(savedIncome);

    fireEvent.change(screen.getByLabelText(/monthly wages/i), { target: { value: '0' } });

    expect(lastEmitted().monthly_income).toEqual([0, 0, 0, 0, 0, 0]);
    expect(screen.getByText('$0.00')).toBeInTheDocument();
  });

  it('records six months of $0 for a new filer who leaves every box blank', () => {
    const { lastEmitted } = renderStep({});

    expect(lastEmitted().monthly_income).toEqual([0, 0, 0, 0, 0, 0]);
    expect(screen.queryByText(/your saved total is/i)).not.toBeInTheDocument();
  });

  it('never sends back a stored income shorter than six months, which the server would reject', () => {
    const { lastEmitted } = renderStep({
      monthly_income: [3100, 3300],
      total_monthly_income: 3200,
    });

    expect(lastEmitted().monthly_income).toEqual([0, 0, 0, 0, 0, 0]);
    expect(screen.queryByText(/your saved total is/i)).not.toBeInTheDocument();
  });
});
