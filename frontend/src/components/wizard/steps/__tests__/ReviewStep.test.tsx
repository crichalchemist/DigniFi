import { fireEvent, render, screen, within } from '@testing-library/react';
import { vi } from 'vitest';
import { ReviewStep } from '../ReviewStep';
import {
  REVIEW_ASSISTANCE,
  REVIEW_DEDUCTIONS,
  REVIEW_ENTRIES,
  REVIEW_HOUSEHOLD_COUNT,
  REVIEW_LINE_3,
  REVIEW_NOW_DIFFERENT,
  REVIEW_SPOUSE_NOW_DIFFERENT,
  VALUE_UNKNOWN_HEADING,
} from '../../../../constants/copy';
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
  spouseIncomeData: {},
  entries: null,
  spouseEntries: null,
};

const value = (label: string) => screen.getByText(label).nextElementSibling;

describe('ReviewStep null-safe rendering', () => {
  it('falls back to placeholders for old assets and debts missing a name or type', () => {
    render(
      <ReviewStep
        {...baseProps}
        assetsData={[
          {
            id: 1,
            ab_line: null,
            description: 'My House',
            asset_type: 'real_property',
            current_value: 250000,
          },
          { id: 2 }, // bare entry — no line, description, type or value (id only for the React key)
        ]}
        debtsData={[
          { id: 1, creditor_name: 'Visa', debt_type: 'credit_card', amount_owed: 4200 },
          { id: 3, creditor_name: 'Demo Clinic', debt_type: 'medical', amount_owed: 80 },
          { id: 2 }, // bare entry
        ]}
        onValidationChange={vi.fn()}
      />
    );

    // Named entries keep their label and a humanized type suffix.
    expect(screen.getByText(/My House/)).toHaveTextContent('(Real estate or home)');
    expect(screen.getByText(/Visa/)).toHaveTextContent('(Credit card)');
    expect(screen.getByText(/Demo Clinic/)).toHaveTextContent('(Medical bill)');

    // Bare entries get dignity-preserving placeholders, never blanks.
    expect(screen.getByText('One item')).toBeInTheDocument();
    expect(screen.getByText('Unnamed Creditor')).toBeInTheDocument();

    // The whole point: no `undefined` or `NaN` ever leaks into the summary,
    // even from the row the user left empty.
    expect(document.body.textContent).not.toMatch(/undefined|NaN/);
  });

  // DIG-166: the filer's last look before completing includes steps 7 and 8, so a lost or
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
          {
            id: 5,
            counterparty_name: 'Demo Gym',
            contract_type: 'contract',
            description: 'Membership',
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
          {
            id: 4,
            name: 'Demo Cosigner',
            street_address: '',
            city: '',
            state: '',
            zip_code: '',
            relationship: '',
          },
        ]}
        onValidationChange={vi.fn()}
      />
    );

    expect(screen.getByText('Contracts & Leases (2)')).toBeInTheDocument();
    expect(screen.getByText(/Oak Street Apartments/)).toHaveTextContent('(Lease)');
    expect(screen.getByText(/Demo Gym/)).toHaveTextContent('(Executory Contract)');
    expect(screen.getByText('Codebtors (2)')).toBeInTheDocument();
    expect(screen.getByText(/Sam Doe/)).toHaveTextContent('(Former Spouse)');
    expect(screen.getByText(/Demo Cosigner/)).toHaveTextContent(/^Demo Cosigner$/);
    expect(document.body.textContent).not.toMatch(
      /auto_loan|credit_card|former_spouse|undefined|NaN/
    );

    rerender(<ReviewStep {...baseProps} onValidationChange={vi.fn()} />);

    expect(screen.getByText('No contracts or leases listed.')).toBeInTheDocument();
    expect(screen.getByText('No codebtors listed.')).toBeInTheDocument();
  });

  it('names a row with no name in words', () => {
    render(
      <ReviewStep
        {...baseProps}
        contractsData={[{ id: 6, counterparty_name: '', contract_type: 'lease', description: '' }]}
        codebtorsData={[
          {
            id: 7,
            name: '',
            street_address: '',
            city: '',
            state: '',
            zip_code: '',
            relationship: '',
          },
        ]}
        onValidationChange={vi.fn()}
      />
    );

    expect(screen.getByText(/Unnamed contract/)).toHaveTextContent('Unnamed contract (Lease)');
    expect(screen.getByText('Unnamed codebtor')).toBeInTheDocument();
  });

  it('says the filer has no amounts owed when they pressed it', () => {
    const { rerender } = render(
      <ReviewStep
        {...baseProps}
        claimAnswers={{ no_debts: true }}
        debtsData={[]}
        onValidationChange={vi.fn()}
      />
    );
    expect(screen.getByText('You said you have no amounts owed.')).toBeInTheDocument();
    expect(screen.queryByText('No amounts owed listed.')).not.toBeInTheDocument();

    rerender(<ReviewStep {...baseProps} debtsData={[]} onValidationChange={vi.fn()} />);
    expect(screen.getByText('No amounts owed listed.')).toBeInTheDocument();

    rerender(
      <ReviewStep
        {...baseProps}
        claimAnswers={{ no_debts: true }}
        debtsData={[{ id: 1, creditor_name: 'Demo Bank', debt_type: 'credit_card' }]}
        onValidationChange={vi.fn()}
      />
    );
    expect(screen.queryByText('You said you have no amounts owed.')).not.toBeInTheDocument();
    expect(screen.getByText(/Demo Bank/)).toBeInTheDocument();
  });

  it('says the filer has no contracts or codebtors when they answered No', () => {
    const { rerender } = render(
      <ReviewStep
        {...baseProps}
        claimAnswers={{ contracts_answer: 'no', codebtors_answer: 'no' }}
        onValidationChange={vi.fn()}
      />
    );
    expect(screen.getByText('You said you have no contracts or leases.')).toBeInTheDocument();
    expect(screen.getByText('You said you have no codebtors.')).toBeInTheDocument();
    expect(screen.queryByText('No contracts or leases listed.')).not.toBeInTheDocument();
    expect(screen.queryByText('No codebtors listed.')).not.toBeInTheDocument();

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

it('Review shows each new answer, or not answered yet', () => {
  const { unmount } = render(
    <ReviewStep
      {...baseProps}
      incomeData={{
        marital_status: 'not_married',
        income_now_different: 'no',
        assistance_answer: 'yes',
      }}
      entries={[]}
      expenseData={{ expenses_include_others: 'yes' }}
      onValidationChange={vi.fn()}
    />
  );
  expect(value(REVIEW_NOW_DIFFERENT)).toHaveTextContent(/^No$/);
  expect(value(REVIEW_ASSISTANCE)).toHaveTextContent(/^Yes$/);
  expect(value(REVIEW_ENTRIES)).toHaveTextContent(/^None$/);
  expect(value(REVIEW_LINE_3)).toHaveTextContent(/^Yes$/);
  unmount();

  render(<ReviewStep {...baseProps} onValidationChange={vi.fn()} />);
  for (const label of [REVIEW_NOW_DIFFERENT, REVIEW_ASSISTANCE, REVIEW_ENTRIES, REVIEW_LINE_3]) {
    expect(value(label)).toHaveTextContent(/^Not answered yet$/);
  }
});

it('Review lists each business or property by its description', () => {
  render(
    <ReviewStep
      {...baseProps}
      entries={[
        {
          kind: 'business',
          description: 'Rideshare and delivery driving',
          gross: 1000,
          expenses: 200,
          current_gross: null,
          current_expenses: null,
        },
      ]}
      onValidationChange={vi.fn()}
    />
  );
  expect(value(REVIEW_ENTRIES)).toHaveTextContent('Rideshare and delivery driving');
});

it("Review shows the spouse's answers only for a spouse at home", () => {
  const { unmount } = render(
    <ReviewStep
      {...baseProps}
      incomeData={{ marital_status: 'married_together' }}
      spouseIncomeData={{ income_now_different: 'no' }}
      onValidationChange={vi.fn()}
    />
  );
  expect(value(REVIEW_SPOUSE_NOW_DIFFERENT)).toHaveTextContent(/^No$/);
  unmount();

  render(
    <ReviewStep
      {...baseProps}
      incomeData={{ marital_status: 'not_married' }}
      onValidationChange={vi.fn()}
    />
  );
  expect(screen.queryByText(REVIEW_SPOUSE_NOW_DIFFERENT)).toBeNull();
});

it('Review shows a Take-home pay section between Income and Monthly Expenses', () => {
  const first = render(
    <ReviewStep
      {...baseProps}
      incomeData={{ monthly_gross_wages: 3000, payroll_tax: 400 }}
      onValidationChange={vi.fn()}
    />
  );
  const titles = Array.from(document.querySelectorAll('.review-section-title')).map(
    (node) => node.textContent ?? ''
  );
  const among = titles.filter((t) => ['Income', 'Take-home pay', 'Monthly Expenses'].includes(t));
  expect(among).toEqual(['Income', 'Take-home pay', 'Monthly Expenses']);
  expect(value(REVIEW_DEDUCTIONS)).toHaveTextContent('$400.00');
  first.unmount();

  const second = render(
    <ReviewStep
      {...baseProps}
      incomeData={{ monthly_gross_wages: 3000 }}
      onValidationChange={vi.fn()}
    />
  );
  expect(value(REVIEW_DEDUCTIONS)).toHaveTextContent(/^Not answered yet$/);
  second.unmount();

  render(<ReviewStep {...baseProps} onValidationChange={vi.fn()} />);
  expect(value(REVIEW_DEDUCTIONS)).toHaveTextContent('$0.00');
});

describe('Review of Schedule A/B', () => {
  const street = { id: 1, ab_line: '1', current_value: 8000, details: { street: '1 Elm' } };
  const cash = { id: 2, ab_line: '16', current_value: 0, description: '', details: {} };
  const car = { id: 3, ab_line: '3', current_value: 500, details: { make: 'Ford' } };
  const shares = {
    id: 4,
    ab_line: '19',
    description: 'Oak Bakery',
    current_value: null,
    details: { value_unknown: true },
  };

  const listItems = () =>
    Array.from(document.querySelectorAll('.review-list-item')).map((item) => item.textContent);

  it('lists the rows by Part with each line number, in the form order, whatever order they came in', () => {
    render(
      <ReviewStep
        {...baseProps}
        assetsData={[shares, cash, car, street]}
        onValidationChange={vi.fn()}
      />
    );

    const headings = Array.from(document.querySelectorAll('.ab-subheading')).map(
      (heading) => heading.textContent
    );
    expect(headings).toEqual([
      expect.stringMatching(/^Part 1/),
      expect.stringMatching(/^Part 2/),
      expect.stringMatching(/^Part 4/),
      VALUE_UNKNOWN_HEADING,
    ]);
    expect(listItems().slice(0, 4)).toEqual([
      expect.stringContaining('Line 1: 1 Elm'),
      expect.stringContaining('Line 3: Ford'),
      expect.stringContaining('Line 16: Cash'),
      expect.stringContaining('Line 19: Oak Bakery'),
    ]);
  });

  // A replacement string reads $ as a pattern, so Review would show something the filer never typed
  it.each(['TV $& stand', '$$', "$'", '$`'])('prints %s as the filer typed it', (typed) => {
    const row = {
      id: 1,
      ab_line: '6',
      description: typed,
      current_value: null,
      details: { value_unknown: true },
    };
    render(<ReviewStep {...baseProps} assetsData={[row]} onValidationChange={vi.fn()} />);

    expect(listItems()[0]).toContain(`Line 6: ${typed}`);
    expect(
      screen.getByRole('button', { name: `Go to Assets for Line 6: ${typed}` })
    ).toBeInTheDocument();
  });

  // The form prints a line's rows by id, so a filer checking Review against it finds the same order
  it('lists the rows of one line by id as the form prints them, an unsaved row last', () => {
    const row = (id: number | undefined, description: string) => ({
      id,
      ab_line: '6',
      description,
      current_value: 1,
      details: {},
    });
    render(
      <ReviewStep
        {...baseProps}
        assetsData={[row(undefined, 'Lamp'), row(9, 'Sofa'), row(4, 'Table')]}
        onValidationChange={vi.fn()}
      />
    );

    expect(listItems()).toEqual([
      expect.stringContaining('Table'),
      expect.stringContaining('Sofa'),
      expect.stringContaining('Lamp'),
    ]);
  });

  // A typed $0 is an answer, and a value the filer doesn't know is not a $0
  it('shows a $0 as $0.00 and an unknown value in words, never as $0.00', () => {
    render(<ReviewStep {...baseProps} assetsData={[cash, shares]} onValidationChange={vi.fn()} />);

    const [cashRow, sharesRow] = listItems();
    expect(cashRow).toContain('$0.00');
    expect(sharesRow).not.toContain('$0.00');
    expect(sharesRow).toContain("You don't know");
    expect(document.body.textContent).not.toMatch(/undefined|NaN/);
  });

  it('Review lists values the filer does not know, and omits the list when there are none', () => {
    const onGoToStep = vi.fn();
    const entireOnly = {
      id: 5,
      ab_line: '3',
      current_value: 500,
      details: { make: 'Honda', entire_unknown: true },
    };
    const { unmount } = render(
      <ReviewStep
        {...baseProps}
        assetsData={[shares, street, entireOnly]}
        onValidationChange={vi.fn()}
        onGoToStep={onGoToStep}
      />
    );

    const heading = screen.getByText(VALUE_UNKNOWN_HEADING);
    const list = within(heading.nextElementSibling as HTMLElement);
    expect(list.getAllByRole('listitem').map((item) => item.textContent)).toEqual([
      expect.stringContaining('Line 3: Honda'),
      expect.stringContaining('Line 19: Oak Bakery'),
    ]);
    // One button a row, and a screen reader's list of buttons tells them apart
    fireEvent.click(list.getByRole('button', { name: 'Go to Assets for Line 3: Honda' }));
    expect(onGoToStep).toHaveBeenCalledWith(5);
    expect(
      list.getByRole('button', { name: 'Go to Assets for Line 19: Oak Bakery' })
    ).toHaveTextContent(/^Go to Assets$/);
    unmount();

    render(<ReviewStep {...baseProps} assetsData={[street, cash]} onValidationChange={vi.fn()} />);
    expect(screen.queryByText(VALUE_UNKNOWN_HEADING)).toBeNull();
  });
});
