import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';
import { ReviewStep } from '../ReviewStep';
import { REVIEW_HOUSEHOLD_COUNT } from '../../../../constants/copy';
import { MARRIAGE_ANSWER_WORDS } from '../../../../constants/formText';

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
  householdCount: null,
  county: null,
};

const value = (label: string) => screen.getByText(label).nextElementSibling;

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

it("Review shows the marriage answer in the form's words, the household count and the county", () => {
  const { rerender } = render(
    <ReviewStep
      {...baseProps}
      incomeData={{ marital_status: 'married_together' }}
      householdCount={4}
      county="Cook"
      onValidationChange={vi.fn()}
    />
  );
  expect(value('County')).toHaveTextContent('Cook');
  expect(value('Your marriage')).toHaveTextContent(
    'Married and your spouse is NOT filing with you. You and your spouse are: Living in the same household and are not legally separated'
  );
  expect(value('People in your home, counting you')).toHaveTextContent(/^4$/);
  rerender(
    <ReviewStep
      {...baseProps}
      incomeData={{ marital_status: 'not_married' }}
      householdCount={1}
      county="Kane"
      onValidationChange={vi.fn()}
    />
  );
  expect(value('Your marriage')).toHaveTextContent(/^Not married$/);
});

it('Review shows a count not worked out yet as not answered yet', () => {
  render(<ReviewStep {...baseProps} onValidationChange={vi.fn()} />);
  for (const label of ['County', 'Your marriage', 'People in your home, counting you']) {
    expect(value(label)).toHaveTextContent(/^Not answered yet$/);
  }
  expect(document.body.textContent).not.toMatch(/null|undefined|NaN/);
});

it("Review shows a spouse who is filing in that answer's own words, with no sub-answer in front", () => {
  render(
    <ReviewStep
      {...baseProps}
      incomeData={{ marital_status: 'married_spouse_filing' }}
      onValidationChange={vi.fn()}
    />
  );
  expect(value('Your marriage')).toHaveTextContent(
    new RegExp(`^${MARRIAGE_ANSWER_WORDS.married_spouse_filing}$`)
  );
});

it('Review shows a household count of 0 as 0, not as not answered yet', () => {
  render(
    <ReviewStep
      {...baseProps}
      incomeData={{ marital_status: 'not_married' }}
      householdCount={0}
      onValidationChange={vi.fn()}
    />
  );
  expect(value(REVIEW_HOUSEHOLD_COUNT)).toHaveTextContent(/^0$/);
});
