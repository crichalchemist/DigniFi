import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import { IncomeInfoStep } from '../IncomeInfoStep';
import { INCOME_FIELDS } from '../../../../types/api';
import type { IncomeInfo } from '../../../../types/api';

// The server stores the ten amounts by source and drops any other name without an error, so
// each box must carry the name the court forms read (forms step 2 §5.5).
const BOXES: [RegExp, (typeof INCOME_FIELDS)[number]][] = [
  [/monthly wages/i, 'monthly_gross_wages'],
  [/monthly overtime/i, 'monthly_overtime'],
  [/monthly tips/i, 'monthly_tips'],
  [/rental income after the property's costs/i, 'monthly_rental_income'],
  [/pension/i, 'monthly_pension'],
  [/social security/i, 'monthly_social_security'],
  [/unemployment/i, 'monthly_unemployment'],
  [/child support received/i, 'monthly_child_support'],
  [/alimony received/i, 'monthly_alimony'],
  [/other monthly income/i, 'monthly_other_income'],
];

// A filer who saved income before it was stored by source: the API returns the old six months
// (read-only) and none of the ten amounts.
const legacyIncome: Partial<IncomeInfo> = {
  monthly_income: [3100, 3300, 3200, 3200, 3150, 3250],
  total_monthly_income: null,
};

const SPLIT_IT = 'You entered $3,200.00 a month in total. Please split it by source.';

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
  it.each(BOXES)('keeps the amount typed in the %s box under %s', (label, name) => {
    const { lastEmitted } = renderStep({});

    fireEvent.change(screen.getByLabelText(label), { target: { value: '850' } });

    expect(lastEmitted()[name]).toBe(850);
    for (const other of INCOME_FIELDS) {
      if (other !== name) expect(lastEmitted()[other]).toBeUndefined();
    }
  });

  it('leaves every box empty for a new filer, so nothing is saved as $0 unless typed', () => {
    const { lastEmitted } = renderStep({});

    for (const field of INCOME_FIELDS) expect(lastEmitted()[field]).toBeUndefined();
    for (const [label] of BOXES) expect(screen.getByLabelText(label)).toHaveValue(null);
  });

  // Ten blank boxes mean no income was given at all, and the means test refuses that. A filer with
  // no income needs to know a typed $0 is how to say so (owner ruling O-1).
  it('tells a filer with no income to enter $0 in a box, since a blank box only means none of that kind', () => {
    renderStep({});

    const help = screen.getByText(/enter your average monthly income before taxes\./i);
    expect(help).toHaveTextContent('Enter your average monthly income before taxes.');
    expect(help).toHaveTextContent(
      "Leave a box blank if you don't get that kind of income. If you have no income at all, enter $0 in any box."
    );
    expect(help).not.toHaveTextContent(/leave it blank or enter \$0/i);
  });

  it('keeps a $0 the filer typed', () => {
    const { lastEmitted } = renderStep({});

    fireEvent.change(screen.getByLabelText(/social security/i), { target: { value: '0' } });

    expect(lastEmitted().monthly_social_security).toBe(0);
  });

  it("shows a returning filer's saved amounts, and empty boxes stay empty", () => {
    renderStep({ monthly_gross_wages: 3200, monthly_tips: 0, total_monthly_income: 3200 });

    expect(screen.getByLabelText(/monthly wages/i)).toHaveValue(3200);
    expect(screen.getByLabelText(/monthly tips/i)).toHaveValue(0);
    expect(screen.getByLabelText(/monthly overtime/i)).toHaveValue(null);
    expect(screen.getByText('$3,200.00')).toBeInTheDocument();
  });

  it('asks a filer who saved only a total to split it by source', () => {
    renderStep(legacyIncome);

    expect(screen.getByText(SPLIT_IT)).toBeInTheDocument();
    expect(screen.queryByText(/we keep only the total/i)).not.toBeInTheDocument();
    // The old total isn't an amount from any source, so no box starts with it.
    for (const [label] of BOXES) expect(screen.getByLabelText(label)).toHaveValue(null);
  });

  it('stops asking once the filer enters an amount by source', () => {
    const { lastEmitted } = renderStep(legacyIncome);

    fireEvent.change(screen.getByLabelText(/monthly wages/i), { target: { value: '3200' } });

    expect(screen.queryByText(SPLIT_IT)).not.toBeInTheDocument();
    expect(lastEmitted().monthly_gross_wages).toBe(3200);
  });

  it('never asks a filer whose income is already stored by source', () => {
    renderStep({ ...legacyIncome, monthly_gross_wages: 3200 });

    expect(screen.queryByText(/please split it by source/i)).not.toBeInTheDocument();
  });

  it('never asks a filer whose saved total was $0, which nothing needs to split', () => {
    renderStep({ monthly_income: [0, 0, 0, 0, 0, 0], total_monthly_income: null });

    expect(screen.queryByText(/please split it by source/i)).not.toBeInTheDocument();
  });
});
