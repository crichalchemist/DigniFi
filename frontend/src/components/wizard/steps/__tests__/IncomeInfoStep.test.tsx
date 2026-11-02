import { useState } from 'react';
import { render, screen, fireEvent, within, cleanup } from '@testing-library/react';
import { vi } from 'vitest';
import { IncomeInfoStep } from '../IncomeInfoStep';
import { INCOME_FIELDS } from '../../../../types/api';
import type { EntryRow } from '../../../../utils/incomeEntries';
import type {
  HouseholdMember,
  IncomeEntry,
  IncomeInfo,
  IncomePeriod,
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
  [/interest, dividends, and royalties/i, 'monthly_interest_and_dividends'],
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
    entries = [],
    spouseEntries = [],
    incomeWindow = { start: '2026-04-01', end: '2026-09-30' },
  }: {
    rows?: Row[];
    noOneElse?: boolean;
    spouse?: SpouseIncome;
    entries?: EntryRow[];
    spouseEntries?: EntryRow[];
    incomeWindow?: IncomePeriod;
  } = {}
) {
  const onDataChange = vi.fn();
  const onValidationChange = vi.fn();
  const onRowsChange = vi.fn();
  let heldRows = rows;
  let heldEntries = entries;
  let heldSpouseEntries = spouseEntries;
  const heldNoEntries = { filer: false, spouse: false };
  function Wizard() {
    const [householdRows, setHouseholdRows] = useState(rows);
    const [pressed, setPressed] = useState(noOneElse);
    const [entryRows, setEntryRows] = useState(entries);
    const [spouseEntryRows, setSpouseEntryRows] = useState(spouseEntries);
    const [noEntries, setNoEntries] = useState(false);
    const [spouseNoEntries, setSpouseNoEntries] = useState(false);
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
        incomeWindow={incomeWindow}
        entryRows={entryRows}
        onEntryRowsChange={(next: EntryRow[]) => {
          heldEntries = next;
          setEntryRows(next);
        }}
        spouseEntryRows={spouseEntryRows}
        onSpouseEntryRowsChange={(next: EntryRow[]) => {
          heldSpouseEntries = next;
          setSpouseEntryRows(next);
        }}
        noEntries={noEntries}
        onNoEntriesChange={(next: boolean) => {
          heldNoEntries.filer = next;
          setNoEntries(next);
        }}
        spouseNoEntries={spouseNoEntries}
        onSpouseNoEntriesChange={(next: boolean) => {
          heldNoEntries.spouse = next;
          setSpouseNoEntries(next);
        }}
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
  // The entries the wizard holds now, and whether each person pressed "none"
  const lastEntries = () => heldEntries;
  const lastSpouseEntries = () => heldSpouseEntries;
  const noEntriesNow = () => heldNoEntries;
  return {
    lastEmitted,
    canContinue,
    lastRows,
    onRowsChange,
    lastEntries,
    lastSpouseEntries,
    noEntriesNow,
  };
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
      ['income_now_different', 'yes'],
      ['income_now_different', 'no'],
      ['assistance_answer', 'yes'],
      ['assistance_answer', 'no'],
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

/** An entry loaded from the server, with its amounts already numbers */
function loadedEntry(id: number, extra: Partial<IncomeEntry> = {}): EntryRow {
  return {
    _key: String(id),
    id,
    kind: 'business',
    description: null,
    gross: null,
    expenses: null,
    current_gross: null,
    current_expenses: null,
    ...extra,
  };
}

const FLOOR_BUSINESS =
  'For your business income, your operating expenses are more than your gross receipts. DigniFi counts this net as $0.00 on Form 122A-1, and on Schedule I unless your income is now different.';
const FLOOR_RENTAL = FLOOR_BUSINESS.replace('business', 'rental');

describe('IncomeInfoStep, averages and the list', () => {
  const ADD = '+ Add a business or property';
  const NO_BUSINESS = 'I have no business or rental income.';

  // §4.4: the months in words, from the ISO parts
  it("the window sentence names the session's months in words", () => {
    renderStep({});
    expect(
      screen.getByText('Your average monthly income for April 1, 2026 through September 30, 2026')
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        'If the amount of your monthly income varied during the 6 months, add the income for all 6 months and divide the total by 6.'
      )
    ).toBeInTheDocument();

    // A window across a year names both years
    cleanup();
    renderStep({}, { incomeWindow: { start: '2026-09-01', end: '2027-02-28' } });
    expect(
      screen.getByText(
        'Your average monthly income for September 1, 2026 through February 28, 2027'
      )
    ).toBeInTheDocument();
  });

  it('interest sits after alimony and child support and before unemployment', () => {
    renderStep({});
    const order = [
      'monthly_child_support',
      'monthly_alimony',
      'monthly_interest_and_dividends',
      'monthly_unemployment',
    ];
    for (let i = 0; i < order.length - 1; i += 1) {
      expect(
        field(order[i]).compareDocumentPosition(field(order[i + 1])) &
          Node.DOCUMENT_POSITION_FOLLOWING
      ).toBeTruthy();
    }
    expect(screen.getByLabelText('Interest, dividends, and royalties')).toBe(
      field('monthly_interest_and_dividends')
    );
    // Rental income is a list entry now, so the old rental box is gone
    const oldRentalBox = ['monthly', 'rental', 'income'].join('_');
    expect(document.querySelector(`[name="${oldRentalBox}"]`)).toBeNull();
  });

  it('the list starts unanswered until the button or an entry', () => {
    const { lastEntries, noEntriesNow } = renderStep({});
    expect(lastEntries()).toEqual([]);
    const none = screen.getByRole('button', { name: NO_BUSINESS });
    expect(none).toHaveAttribute('aria-pressed', 'false');

    fireEvent.click(none);
    expect(screen.getByRole('button', { name: NO_BUSINESS })).toHaveAttribute(
      'aria-pressed',
      'true'
    );
    expect(noEntriesNow().filer).toBe(true);

    fireEvent.click(screen.getByRole('button', { name: ADD }));
    fireEvent.change(field('entry_kind_0'), { target: { value: 'business' } });
    expect(screen.queryByRole('button', { name: NO_BUSINESS })).toBeNull();
    expect(noEntriesNow().filer).toBe(false);
  });

  it('+ Add is disabled at 10 entries', () => {
    const nine = Array.from({ length: 9 }, (_, i) => loadedEntry(i + 1));
    renderStep({}, { entries: nine });
    expect(screen.getByRole('button', { name: ADD })).toBeEnabled();
    fireEvent.click(screen.getByRole('button', { name: ADD }));
    expect(screen.getByRole('button', { name: ADD })).toBeDisabled();
  });

  it('each entry shows its own net', () => {
    renderStep(
      {},
      {
        entries: [
          loadedEntry(1, { gross: 4200, expenses: 830 }),
          loadedEntry(2, { gross: 100, expenses: 300 }),
        ],
      }
    );
    const nets = screen.getAllByText('Net a month').map((label) => label.closest('section'));
    expect(nets[0]).toHaveTextContent('$3,370.00');
    expect(nets[1]).toHaveTextContent('-$200.00');
  });

  // §4.2: information only, on the averages' forms alone
  it("the averages floor sentence shows only while a kind's summed net is below $0, naming only 122A-1 and Schedule I", () => {
    renderStep(
      {},
      {
        entries: [
          loadedEntry(1, { gross: 4200, expenses: 830 }),
          loadedEntry(2, { gross: 100, expenses: 300 }),
        ],
      }
    );
    expect(screen.queryByText(FLOOR_BUSINESS)).toBeNull();

    fireEvent.change(field('entry_gross_0'), { target: { value: '500' } });
    const sentence = screen.getByText(FLOOR_BUSINESS);
    expect(sentence).toBeInTheDocument();
    expect(screen.queryByText(FLOOR_RENTAL)).toBeNull();
    expect(sentence.textContent).toMatch(/Form 122A-1/);
    expect(sentence.textContent).toMatch(/Schedule I/);
    expect(sentence.textContent).not.toMatch(/Schedule J|106/);
  });

  it('the totals line includes the floored nets', () => {
    renderStep(
      {},
      {
        entries: [
          loadedEntry(1, { gross: 4200, expenses: 830 }),
          loadedEntry(2, { kind: 'rental', gross: 100, expenses: 500 }),
        ],
      }
    );
    fireEvent.change(field('monthly_gross_wages'), { target: { value: '1000' } });
    expect(
      screen.getByText('Your income', { selector: 'dt' }).nextElementSibling
    ).toHaveTextContent('$4,370.00');
  });

  it('the operating expenses box says to count a cost once', () => {
    renderStep({}, { entries: [loadedEntry(1)] });
    expect(field('entry_expenses_0')).toHaveAccessibleDescription(
      expect.stringContaining(
        'If one cost is both for this work and for your home, count each dollar once, in one place only: here or on the Expenses step. How you split it is your choice. Legal aid can help.'
      )
    );
  });

  it('a blank amount on a saved entry says so in its own box, for a screen reader', () => {
    renderStep({}, { entries: [loadedEntry(1)] });
    for (const name of ['entry_gross_0', 'entry_expenses_0', 'entry_description_0']) {
      expect(field(name)).toHaveAccessibleDescription(expect.stringContaining('Not answered yet'));
    }
    fireEvent.change(field('entry_gross_0'), { target: { value: '5' } });
    expect(field('entry_gross_0')).not.toHaveAccessibleDescription(
      expect.stringContaining('Not answered yet')
    );
  });

  it("the spouse's cards carry the spouse's name", () => {
    renderStep({ marital_status: 'married_together' }, { spouseEntries: [loadedEntry(2)] });
    expect(
      screen.getByRole('heading', { name: "Spouse's business or property 1" })
    ).toBeInTheDocument();
  });

  it("the spouse's list carries the form's one-column sentence, and its own buttons", () => {
    renderStep({ marital_status: 'married_together' });
    const section = screen
      .getByRole('heading', { name: "Your spouse's income" })
      .closest('section');
    expect(section).toHaveTextContent(
      'Do not include any income amount more than once. For example, if both spouses own the same rental property, put the income from that property in one column only.'
    );
    expect(
      screen.getByRole('button', { name: "+ Add your spouse's business or property" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'My spouse has no business or rental income.' })
    ).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: ADD })).toHaveLength(1);

    fireEvent.click(
      screen.getByRole('button', { name: "+ Add your spouse's business or property" })
    );
    expect(field('spouse_entry_kind_0')).toBeInTheDocument();
    pick('marital_status', 'not_filing');
    pick('spouse_household', 'married_separately');
    expect(document.querySelector('[name^="spouse_entry_"]')).toBeNull();
  });

  it('an entry amount the server would refuse blocks Continue', () => {
    const { canContinue } = renderStep({}, { entries: [loadedEntry(1)] });
    fireEvent.change(field('entry_gross_0'), { target: { value: '12.345' } });
    expect(canContinue()).toBe(false);
    fireEvent.change(field('entry_gross_0'), { target: { value: '12.34' } });
    expect(canContinue()).toBe(true);
    // A blank description, kind or amount never blocks
    fireEvent.change(field('entry_description_0'), { target: { value: '' } });
    fireEvent.change(field('entry_kind_0'), { target: { value: '' } });
    fireEvent.change(field('entry_gross_0'), { target: { value: '' } });
    expect(canContinue()).toBe(true);
  });
});

describe('IncomeInfoStep, now different and assistance', () => {
  const NOW_HEADING = 'Your income now (a month)';
  const START = 'Start from my average figures';
  const ASSISTANCE_8F =
    'Other government assistance that you regularly receive. Include cash assistance and the value (if known) of any non-cash assistance that you receive, such as food stamps (benefits under the Supplemental Nutrition Assistance Program) or housing subsidies.';
  const FLOOR_CURRENT_BUSINESS =
    'For your business income now, your operating expenses are more than your gross receipts. DigniFi counts this net as $0.00 on Schedule I.';
  const CURRENT_BOXES = INCOME_FIELDS.map((f) => `current_${f}`);
  const ASSISTANCE_BOXES = [
    'cash_assistance_kind',
    'cash_assistance_amount',
    'noncash_assistance_kind',
    'noncash_assistance_value',
  ];

  it('no new question starts answered', () => {
    const { lastEmitted } = renderStep({ marital_status: 'married_together' });
    for (const name of [
      'income_now_different',
      'assistance_answer',
      'spouse_income_now_different',
      'spouse_assistance_answer',
    ]) {
      for (const value of ['yes', 'no']) {
        const radio = document.querySelector(`input[name="${name}"][value="${value}"]`);
        expect(radio).not.toBeNull();
        expect(radio).not.toBeChecked();
      }
    }
    expect(lastEmitted().income_now_different ?? null).toBeNull();
    expect(lastEmitted().assistance_answer ?? null).toBeNull();
  });

  it('the current section shows only under Yes, with no pre-fill', () => {
    renderStep({ monthly_gross_wages: 3000 });
    expect(document.querySelector('[name="current_monthly_gross_wages"]')).toBeNull();

    pick('income_now_different', 'yes');
    expect(screen.getByRole('heading', { name: NOW_HEADING })).toBeInTheDocument();
    for (const name of CURRENT_BOXES) expect(field(name)).toHaveValue(null);
    expect(field('monthly_gross_wages')).toHaveValue(3000);

    pick('income_now_different', 'no');
    expect(screen.queryByRole('heading', { name: NOW_HEADING })).toBeNull();
    expect(document.querySelector('[name="current_monthly_gross_wages"]')).toBeNull();
  });

  it('Start from my average figures copies the averages, and the filer then edits', () => {
    const { lastEmitted } = renderStep(
      { monthly_gross_wages: 3000 },
      { entries: [loadedEntry(1, { gross: 4200, expenses: 830 })] }
    );
    pick('income_now_different', 'yes');
    fireEvent.click(screen.getByRole('button', { name: START }));

    expect(field('current_monthly_gross_wages')).toHaveValue(3000);
    expect(field('current_monthly_tips')).toHaveValue(null);
    expect(field('entry_current_gross_0')).toHaveValue(4200);
    expect(field('entry_current_expenses_0')).toHaveValue(830);

    fireEvent.change(field('current_monthly_gross_wages'), { target: { value: '2500' } });
    expect(lastEmitted().current_monthly_gross_wages).toBe(2500);
    expect(lastEmitted().monthly_gross_wages).toBe(3000);
  });

  it('the current floor sentence shows only while a kind’s current net is below $0, naming only Schedule I', () => {
    renderStep(
      {},
      {
        entries: [
          loadedEntry(1, { gross: 4200, expenses: 830, current_gross: 400, current_expenses: 830 }),
        ],
      }
    );
    expect(screen.queryByText(FLOOR_CURRENT_BUSINESS)).toBeNull();
    pick('income_now_different', 'yes');

    const sentence = screen.getByText(FLOOR_CURRENT_BUSINESS);
    expect(sentence).not.toHaveTextContent(/122A-1/);
    expect(screen.queryByText(/DigniFi counts this net as \$0.00 on Form 122A-1/)).toBeNull();

    fireEvent.change(field('entry_current_gross_0'), { target: { value: '900' } });
    expect(screen.queryByText(FLOOR_CURRENT_BUSINESS)).toBeNull();
  });

  it('the assistance boxes show under Yes, in the form’s words', () => {
    const { lastEmitted } = renderStep({});
    expect(screen.getByRole('group', { name: ASSISTANCE_8F })).toBeInTheDocument();
    expect(
      screen.getByText('Unemployment and Social Security have their own boxes. They are above.')
    ).toBeInTheDocument();
    for (const name of ASSISTANCE_BOXES) {
      expect(document.querySelector(`[name="${name}"]`)).toBeNull();
    }

    pick('assistance_answer', 'yes');
    for (const name of ASSISTANCE_BOXES) expect(field(name)).toBeInTheDocument();
    expect(field('cash_assistance_kind')).toHaveAttribute('maxlength', '100');
    expect(field('noncash_assistance_kind')).toHaveAttribute('maxlength', '100');
    fireEvent.change(field('noncash_assistance_kind'), { target: { value: 'SNAP (food stamps)' } });

    pick('assistance_answer', 'no');
    for (const name of ASSISTANCE_BOXES) {
      expect(document.querySelector(`[name="${name}"]`)).toBeNull();
    }
    expect(lastEmitted().noncash_assistance_kind).toBe('SNAP (food stamps)');
  });

  it('the spouse’s questions show only under married_together', () => {
    renderStep({ marital_status: 'married_together' });
    for (const name of ['spouse_income_now_different', 'spouse_assistance_answer']) {
      expect(document.querySelector(`input[name="${name}"][value="yes"]`)).not.toBeNull();
    }
    expect(
      screen.getByRole('heading', { name: "Your spouse's government assistance" })
    ).toBeInTheDocument();
    pick('spouse_income_now_different', 'yes');
    expect(
      screen.getByRole('heading', { name: "Your spouse's income now (a month)" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: "Start from my spouse's average figures" })
    ).toBeInTheDocument();
    expect(field('spouse_current_monthly_gross_wages')).toHaveValue(null);
    pick('spouse_assistance_answer', 'yes');
    expect(field('spouse_cash_assistance_kind')).toBeInTheDocument();
    expect(field('spouse_noncash_assistance_value')).toBeInTheDocument();

    cleanup();
    renderStep({ marital_status: 'married_separately' });
    expect(document.querySelector('[name^="spouse_income_now"]')).toBeNull();
    expect(document.querySelector('[name^="spouse_assistance"]')).toBeNull();
  });

  it('an amount the server would refuse stays on screen after the answer moves to No', () => {
    const { canContinue } = renderStep({});
    pick('assistance_answer', 'yes');
    fireEvent.change(field('cash_assistance_amount'), { target: { value: '12.345' } });
    pick('assistance_answer', 'no');

    expect(field('cash_assistance_amount')).toBeInTheDocument();
    expect(screen.getByText('Please enter dollars and cents, like 1250.50')).toBeInTheDocument();
    expect(canContinue()).toBe(false);

    fireEvent.change(field('cash_assistance_amount'), { target: { value: '12.34' } });
    expect(document.querySelector('[name="cash_assistance_amount"]')).toBeNull();
    expect(canContinue()).toBe(true);
  });

  it('an unanswered question says so on its own group, for a screen reader', () => {
    renderStep({});
    const group = screen.getByRole('group', {
      name: 'Is your income now different from that average?',
    });
    expect(group).toHaveAccessibleDescription(expect.stringContaining('Not answered yet'));
    pick('income_now_different', 'no');
    expect(group).not.toHaveAccessibleDescription(expect.stringContaining('Not answered yet'));
  });
});
