import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';
import { ReviewStep } from '../ReviewStep';

// ReviewStep summarizes whatever the earlier steps captured. Assets and debts
// can arrive partially filled (a row the user started but never named), so the
// component must never render the raw `undefined`/`NaN` that an unguarded
// template literal would produce. These tests pin those null-guards.
const baseProps = {
  debtorData: {},
  incomeData: {},
  expenseData: {},
  assetsData: [],
  debtsData: [],
  contractsData: [],
  codebtorsData: [],
};

describe('ReviewStep null-safe rendering', () => {
  it('falls back to placeholders for assets and debts missing a name or type', () => {
    render(
      <ReviewStep
        {...baseProps}
        assetsData={[
          { id: 1, description: 'My House', asset_type: 'real_property', current_value: 250000 },
          { id: 2 }, // bare entry — no description, no type, no value (id only for the React key)
        ]}
        debtsData={[
          { id: 1, creditor_name: 'Visa', debt_type: 'credit_card', amount_owed: 4200 },
          { id: 2 }, // bare entry
        ]}
        onValidationChange={vi.fn()}
      />
    );

    // Named entries keep their label and a humanized type suffix.
    expect(screen.getByText(/My House/)).toHaveTextContent('(real property)');
    expect(screen.getByText(/Visa/)).toHaveTextContent('(credit_card)');

    // Bare entries get dignity-preserving placeholders, never blanks.
    expect(screen.getByText('Unnamed Asset')).toBeInTheDocument();
    expect(screen.getByText('Unnamed Creditor')).toBeInTheDocument();

    // The whole point: no `undefined` or `NaN` ever leaks into the summary,
    // even from the row the user left empty.
    expect(document.body.textContent).not.toMatch(/undefined|NaN/);
  });

  // DIG-166: the filer's last look before completing includes steps 6 and 7, so a lost or
  // doubled contract or codebtor shows here instead of only on Schedules G and H.
  it('lists the contracts and codebtors the filer saved, or says there are none', () => {
    const { rerender } = render(
      <ReviewStep
        {...baseProps}
        contractsData={[
          {
            id: 4,
            counterparty_name: 'Oak Street Apartments',
            contract_type: 'lease',
            description: 'Apartment lease',
          },
        ]}
        codebtorsData={[
          {
            id: 3,
            name: 'Sam Doe',
            street_address: '',
            city: 'Chicago',
            state: 'IL',
            zip_code: '',
            relationship: 'former_spouse',
          },
        ]}
        onValidationChange={vi.fn()}
      />
    );

    expect(screen.getByText('Contracts & Leases (1)')).toBeInTheDocument();
    expect(screen.getByText(/Oak Street Apartments/)).toHaveTextContent('(lease)');
    expect(screen.getByText('Codebtors (1)')).toBeInTheDocument();
    expect(screen.getByText(/Sam Doe/)).toHaveTextContent('(former spouse)');

    rerender(<ReviewStep {...baseProps} onValidationChange={vi.fn()} />);

    expect(screen.getByText('No contracts or leases listed.')).toBeInTheDocument();
    expect(screen.getByText('No codebtors listed.')).toBeInTheDocument();
  });

  it('signals the step is always valid to proceed', () => {
    const onValidationChange = vi.fn();
    render(<ReviewStep {...baseProps} onValidationChange={onValidationChange} />);
    expect(onValidationChange).toHaveBeenCalledWith(true);
  });
});
