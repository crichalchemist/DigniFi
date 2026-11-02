import { useState } from 'react';
import { render, screen, fireEvent, within } from '@testing-library/react';
import { vi } from 'vitest';
import { IncomeInfoStep } from '../IncomeInfoStep';
import { INCOME_FIELDS } from '../../../../types/api';
import type {
  HouseholdMember,
  IncomeInfo,
  Relationship,
  SpouseIncome,
  WizardRow,
} from '../../../../types/api';

type Row = WizardRow<HouseholdMember>;

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

/**
 * The step inside a stand-in for the wizard, which holds the household rows and the "No one
 * else" answer as the wizard does, so a change the step hands up comes back down to it.
 */
function renderStep(
  initialData: Partial<IncomeInfo>,
  {
    rows = [],
    noOneElse = false,
    spouse,
  }: { rows?: Row[]; noOneElse?: boolean; spouse?: SpouseIncome } = {}
) {
  const onDataChange = vi.fn();
  const onValidationChange = vi.fn();
  const onRowsChange = vi.fn();
  let heldRows = rows;
  function Wizard() {
    const [householdRows, setHouseholdRows] = useState(rows);
    const [pressed, setPressed] = useState(noOneElse);
    return (
      <IncomeInfoStep
        initialData={initialData}
        onDataChange={onDataChange}
        onValidationChange={onValidationChange}
        householdRows={householdRows}
        onHouseholdRowsChange={(next: Row[]) => {
          onRowsChange(next);
          heldRows = next;
          setHouseholdRows(next);
        }}
        noOneElse={pressed}
        onNoOneElseChange={setPressed}
        initialSpouseIncome={spouse}
        onSpouseIncomeChange={() => {}}
      />
    );
  }
  render(<Wizard />);
  const lastEmitted = () =>
    onDataChange.mock.calls[onDataChange.mock.calls.length - 1][0] as Partial<IncomeInfo>;
  // Whether the wizard lets the filer press Continue
  const canContinue = () =>
    onValidationChange.mock.calls[onValidationChange.mock.calls.length - 1][0] as boolean;
  // The rows the wizard holds now
  const lastRows = () => heldRows;
  return { lastEmitted, canContinue, lastRows, onRowsChange };
}

/** A form control by its name, as the journeys find them */
function field(name: string) {
  const control = document.querySelector(`[name="${name}"]`);
  if (!control) throw new Error(`No control named ${name}`);
  return control as HTMLElement;
}

/** Picks one answer of a radio question by its value, as the journeys do */
function pick(name: string, value: string) {
  const radio = document.querySelector(`input[name="${name}"][value="${value}"]`);
  if (!radio) throw new Error(`No answer ${value} to ${name}`);
  fireEvent.click(radio);
}

/** A row loaded from the server, every question answered */
function person(id: number, relationship: Relationship, extra: Partial<HouseholdMember> = {}): Row {
  return {
    _key: String(id),
    id,
    relationship,
    age: 30,
    lives_with_you: true,
    claimed_or_supported: true,
    ...extra,
  };
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

  // The server stores each amount as DecimalField(max_digits=10, decimal_places=2) and refuses
  // anything else, so the box says what is wrong before Continue saves it (W-9)
  it('asks for dollars and cents beside a box with a third decimal place, and blocks Continue', () => {
    const { canContinue } = renderStep({});

    fireEvent.change(screen.getByLabelText(/unemployment/i), { target: { value: '12.345' } });

    expect(screen.getByLabelText(/unemployment/i)).toHaveAccessibleDescription(
      'Please enter dollars and cents, like 1250.50'
    );
    expect(canContinue()).toBe(false);
  });

  it('says beside the box that an amount over $99,999,999.99 is too large, and blocks Continue', () => {
    const { canContinue } = renderStep({});

    fireEvent.change(screen.getByLabelText(/unemployment/i), { target: { value: '100000000' } });

    expect(screen.getByLabelText(/unemployment/i)).toHaveAccessibleDescription(
      'This amount is too large. Please check it'
    );
    expect(canContinue()).toBe(false);
  });

  it('takes the largest amount the server stores, $99,999,999.99', () => {
    const { lastEmitted, canContinue } = renderStep({});

    fireEvent.change(screen.getByLabelText(/unemployment/i), { target: { value: '99999999.99' } });

    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(canContinue()).toBe(true);
    expect(lastEmitted().monthly_unemployment).toBe(99999999.99);
  });

  // Coming back to the step, the wizard hands it the total it last added up, which no box shows
  it('lets a returning filer continue when the total their amounts add up to is not a whole cent', () => {
    const { canContinue } = renderStep({
      monthly_gross_wages: 10.1,
      monthly_tips: 20.2,
      total_monthly_income: 10.1 + 20.2,
    });

    expect(canContinue()).toBe(true);
  });
});

// Form 122A-1 line 1 and the household list come first, in the form's words (3e1 spec §8.2)
describe('IncomeInfoStep, family first', () => {
  const SPOUSE_DEPENDENT = 'Is your spouse a dependent of yours?';
  const NO_ONE_ELSE = 'No one else lives with me or depends on me.';

  // Line 1 is the filer's sworn answer, so the step never picks one for them
  it('nothing is selected on line 1 until the filer picks', () => {
    const { lastEmitted } = renderStep({});

    const radios = screen.getAllByRole('radio') as HTMLInputElement[];
    expect(radios.map((radio) => [radio.name, radio.value])).toEqual([
      ['marital_status', 'not_married'],
      ['marital_status', 'married_spouse_filing'],
      ['marital_status', 'not_filing'],
    ]);
    for (const radio of radios) expect(radio).not.toBeChecked();
    expect(
      screen.queryByLabelText('Living in the same household and are not legally separated')
    ).not.toBeInTheDocument();
    expect(lastEmitted().marital_status ?? null).toBeNull();
  });

  it('the spouse filing answer says DigniFi prepares forms for one person', () => {
    const { lastEmitted, canContinue } = renderStep({});

    pick('marital_status', 'married_spouse_filing');

    expect(
      screen.getByText(
        "DigniFi prepares forms for one person filing alone. It can't prepare a case your spouse files with you."
      )
    ).toBeInTheDocument();
    expect(lastEmitted().marital_status).toBe('married_spouse_filing');
    // Complete names it, so the step still saves
    expect(canContinue()).toBe(true);
  });

  // The Yes rests on the filer's own answer, so the added row follows that answer until the filer
  // answers "Lives with you?" on it themselves
  it('picking Living in the same household adds a spouse row that lives with you', () => {
    const { lastRows } = renderStep({});

    pick('marital_status', 'not_filing');
    pick('spouse_household', 'married_together');

    expect(lastRows()).toHaveLength(1);
    expect(lastRows()[0]).toMatchObject({
      _key: expect.stringMatching(/^new-\d+$/),
      relationship: 'spouse',
      age: null,
      lives_with_you: true,
      claimed_or_supported: null,
    });

    pick('spouse_household', 'married_separately');
    expect(lastRows()[0].lives_with_you).toBeNull();

    pick('spouse_household', 'married_together');
    expect(lastRows()).toHaveLength(1);
    expect(lastRows()[0].lives_with_you).toBe(true);

    pick('lives_with_you_0', 'no');
    pick('spouse_household', 'married_separately');
    expect(lastRows()[0].lives_with_you).toBe(false);
  });

  // The list holds at most 20 rows; Complete names the missing spouse instead
  it('with 20 rows, picking living together adds no spouse row', () => {
    const rows = Array.from({ length: 20 }, (_, index) => person(index + 1, 'other'));
    const { lastRows } = renderStep({}, { rows });

    pick('marital_status', 'not_filing');
    pick('spouse_household', 'married_together');

    expect(lastRows()).toHaveLength(20);
    expect(lastRows().some((row) => row.relationship === 'spouse')).toBe(false);
  });

  // A saved answer is the filer's own and is never inferred (U:308)
  it("a loaded spouse row's answers are never changed by the marriage answer", () => {
    const { onRowsChange } = renderStep(
      {},
      { rows: [person(1, 'spouse', { lives_with_you: false, spouse_is_dependent: false })] }
    );

    pick('marital_status', 'not_filing');
    pick('spouse_household', 'married_together');
    pick('spouse_household', 'married_separately');

    expect(onRowsChange).not.toHaveBeenCalled();
  });

  // The server refuses a second spouse row
  it('Spouse is offered only when no other row is the spouse', () => {
    renderStep(
      {},
      { rows: [person(1, 'spouse', { spouse_is_dependent: false }), person(2, 'son')] }
    );

    const offered = (name: string) =>
      Array.from((field(name) as HTMLSelectElement).options).map((option) => option.value);
    expect(offered('relationship_0')).toContain('spouse');
    expect(offered('relationship_1')).not.toContain('spouse');
  });

  // The server refuses the spouse's question on any other row, so every save would fail
  it('changing a row away from spouse drops its spouse question', () => {
    const { lastRows } = renderStep(
      {},
      { rows: [person(1, 'spouse', { spouse_is_dependent: false })] }
    );
    expect(screen.getByRole('group', { name: SPOUSE_DEPENDENT })).toBeInTheDocument();

    fireEvent.change(field('relationship_0'), { target: { value: 'son' } });

    expect(screen.queryByRole('group', { name: SPOUSE_DEPENDENT })).not.toBeInTheDocument();
    expect(lastRows()[0]).not.toHaveProperty('spouse_is_dependent');
  });

  // The server refuses a 21st row
  it('+ Add a person is disabled at 20 rows', () => {
    const rows = Array.from({ length: 19 }, (_, index) => person(index + 1, 'other'));
    renderStep({}, { rows });

    const add = screen.getByRole('button', { name: '+ Add a person' });
    expect(add).toBeEnabled();
    fireEvent.click(add);
    expect(add).toBeDisabled();
  });

  // The server refuses any other age, so the box says what is wrong before Continue saves it
  it('an age outside 0–120 or not whole blocks saving', () => {
    const { canContinue } = renderStep({}, { rows: [person(1, 'son')] });

    for (const age of ['-1', '121', '7.5']) {
      fireEvent.change(field('age_0'), { target: { value: age } });
      expect(field('age_0')).toHaveAccessibleDescription(
        'Please enter an age from 0 to 120, in whole years'
      );
      expect(canContinue()).toBe(false);
    }
    for (const age of ['0', '120']) {
      fireEvent.change(field('age_0'), { target: { value: age } });
      expect(canContinue()).toBe(true);
    }
  });

  // The spouse's figures stay saved but count for nothing away from living together (§5.1)
  it('a hidden spouse section neither saves nor blocks', () => {
    const { canContinue } = renderStep(
      { marital_status: 'married_together' },
      { spouse: { monthly_gross_wages: 1800 } }
    );

    fireEvent.change(field('spouse_monthly_tips'), { target: { value: '12.345' } });
    expect(canContinue()).toBe(false);

    pick('spouse_household', 'married_separately');
    expect(document.querySelector('[name="spouse_monthly_tips"]')).toBeNull();
    expect(canContinue()).toBe(true);
  });

  it("the Income step asks the family first, in the form's words", () => {
    renderStep(
      { marital_status: 'married_together' },
      { rows: [person(1, 'spouse', { spouse_is_dependent: false })] }
    );

    expect(
      screen.getByRole('group', { name: 'What is your marital and filing status? Check one only.' })
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        'By checking this box, you declare under penalty of perjury that you and your spouse are legally separated under nonbankruptcy law that applies or that you and your spouse are living apart for reasons that do not include evading the Means Test requirements. 11 U.S.C. § 707(b)(7)(B).'
      )
    ).toBeInTheDocument();

    const inOrder = [
      screen.getByRole('heading', { name: 'Your marriage' }),
      screen.getByRole('heading', { name: 'People in your home, and people you support' }),
      field('monthly_gross_wages'),
      screen.getByRole('heading', { name: "Your spouse's income" }),
      field('spouse_monthly_gross_wages'),
    ];
    for (let index = 1; index < inOrder.length; index += 1) {
      expect(
        inOrder[index - 1].compareDocumentPosition(inOrder[index]) &
          Node.DOCUMENT_POSITION_FOLLOWING
      ).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
    }

    expect(
      screen.getByText(
        "List everyone who lives with you, and anyone you support who lives somewhere else. Don't include yourself. Don't type anyone's name."
      )
    ).toBeInTheDocument();
    const spouseCard = within(field('relationship_0').closest('section') as HTMLElement);
    expect(spouseCard.getByRole('group', { name: SPOUSE_DEPENDENT })).toBeInTheDocument();
    expect(
      spouseCard.getByText(
        'A person who is economically dependent on you regardless of whether the person can be claimed as a dependent on your federal tax return.',
        { exact: false }
      )
    ).toBeInTheDocument();
  });

  it('answering anything on an added row clears No one else', () => {
    renderStep({}, { noOneElse: true });

    fireEvent.click(screen.getByRole('button', { name: '+ Add a person' }));
    fireEvent.change(field('relationship_0'), { target: { value: 'son' } });
    expect(screen.queryByRole('button', { name: NO_ONE_ELSE })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Remove person 1' }));
    expect(screen.getByRole('button', { name: NO_ONE_ELSE })).toHaveAttribute(
      'aria-pressed',
      'false'
    );
  });

  it("the totals show the filer's and the spouse's income, a month each", () => {
    renderStep(
      { monthly_gross_wages: 12000, marital_status: 'married_together' },
      { spouse: { monthly_gross_wages: 1800 } }
    );

    // The amount listed under a total's label
    const total = (label: string) => screen.getByText(label, { selector: 'dt' }).nextElementSibling;
    expect(total('Your income')).toHaveTextContent('$12,000.00');
    expect(total("Your spouse's income")).toHaveTextContent('$1,800.00');
    // The sentence under the totals never calls the spouse's figure "your total"
    expect(
      screen.getByText('Both totals are monthly, before taxes and deductions.')
    ).toBeInTheDocument();
    expect(screen.queryByText(/this is your total monthly income/i)).not.toBeInTheDocument();

    pick('marital_status', 'not_married');
    expect(screen.queryByText("Your spouse's income")).not.toBeInTheDocument();
    expect(
      screen.getByText('This is your total monthly income before taxes and deductions.')
    ).toBeInTheDocument();
    expect(screen.queryByText(/both totals/i)).not.toBeInTheDocument();
  });

  // The help under the filer's support boxes says "you receive", and the spouse's figures would
  // count twice if a filer typed their own into the spouse's boxes
  it("the spouse's boxes carry none of the filer's help", () => {
    renderStep({ marital_status: 'married_together' });

    for (const name of ['monthly_child_support', 'monthly_alimony']) {
      expect(field(name)).toHaveAccessibleDescription(/you receive/i);
      expect(field(`spouse_${name}`)).not.toHaveAccessibleDescription(/you receive/i);
    }
  });
});
