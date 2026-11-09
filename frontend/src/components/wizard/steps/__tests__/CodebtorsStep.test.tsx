import { useState } from 'react';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';
import { CodebtorsStep } from '../CodebtorsStep';
import { fill } from '../claims/claimNames';
import * as copy from '../../../../constants/copy';
import {
  AB_CITY_LABEL,
  AB_STATE_LABEL,
  AB_ZIP_LABEL,
  CLAIM_STREET_LABEL,
  SCHEDULE_H_COLUMN_2,
  SCHEDULE_H_LINE_1_QUESTION,
  SCHEDULE_H_LINE_2_QUESTION,
  SCHEDULE_H_LINE_2_SPOUSE_QUESTION,
} from '../../../../constants/formText';
import type { ClaimAnswers, CodebtorRow, ContractRow, DebtRow } from '../../../../types/api';

// The server refuses a codebtor whose name, street, city or ZIP is longer than its column
// holds, and the wizard can only say it couldn't save, so Continue would never succeed.
// Each box stops at that length instead.

const debts = [{ _key: '30', id: 30, creditor_name: 'Demo Card Services' }] as DebtRow[];
const contracts = [{ _key: '4', id: 4, counterparty_name: 'Demo Motors' }] as ContractRow[];
const rohan: CodebtorRow = {
  _key: '3',
  id: 3,
  name: 'Rohan Demo',
  street_address: '2 Demo Ave',
  street_2: '',
  city: 'Chicago',
  state: 'IL',
  zip_code: '60602',
  outside_us: false,
  relationship: '',
  links: [{ kind: 'debt', id: 30 }],
};
const given: ClaimAnswers = { codebtors_answer: 'yes', community_lived: 'no' };

interface HarnessProps {
  initial?: CodebtorRow[];
  initialAnswers?: ClaimAnswers;
  debts?: DebtRow[];
  contracts?: ContractRow[];
  onRowsChange?: (rows: CodebtorRow[]) => void;
  onAnswersChange?: (answers: ClaimAnswers) => void;
  onValidationChange?: (isValid: boolean) => void;
}

/** The wizard's part: it holds the rows and the answers the step shows */
function StepWithRows({
  initial = [],
  initialAnswers = {},
  debts: heldDebts = [],
  contracts: heldContracts = [],
  onRowsChange = () => {},
  onAnswersChange = () => {},
  onValidationChange = () => {},
}: HarnessProps) {
  const [rows, setRows] = useState<CodebtorRow[]>(initial);
  const [answers, setAnswers] = useState<ClaimAnswers>(initialAnswers);
  return (
    <CodebtorsStep
      rows={rows}
      onRowsChange={(next) => {
        setRows(next);
        onRowsChange(next);
      }}
      answers={answers}
      onAnswersChange={(next) => {
        setAnswers(next);
        onAnswersChange(next);
      }}
      debts={heldDebts}
      contracts={heldContracts}
      onValidationChange={onValidationChange}
    />
  );
}

const field = (name: string) => document.querySelector(`[name="${name}"]`) as HTMLInputElement;
const status = () => screen.getByRole('status');
const group = (sentence: string) =>
  screen.getByRole('group', {
    name: new RegExp(`^${sentence.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}`),
  });

describe('CodebtorsStep', () => {
  it('keeps each box within the length the server stores, so a long entry never blocks Continue', async () => {
    const onRowsChange = vi.fn();
    render(<StepWithRows initial={[rohan]} initialAnswers={given} onRowsChange={onRowsChange} />);

    const user = userEvent.setup();
    const typeOver = async (name: string, text: string) => {
      await user.clear(field(name));
      await user.paste(text);
    };
    await typeOver('codebtor_name_0', 'N'.repeat(300));
    await typeOver('codebtor_street_address_0', 'S'.repeat(300));
    await typeOver('codebtor_city_0', 'C'.repeat(150));
    await typeOver('codebtor_zip_code_0', '60601-1234-99');

    expect(onRowsChange).toHaveBeenLastCalledWith([
      {
        ...rohan,
        name: 'N'.repeat(255),
        street_address: 'S'.repeat(255),
        city: 'C'.repeat(100),
        zip_code: '60601-1234',
      },
    ]);
  });

  it('asks H line 1 and line 2 with nothing checked, and says what is missing', () => {
    render(<StepWithRows />);

    expect(screen.getAllByRole('group')).toHaveLength(2);
    expect(group(SCHEDULE_H_LINE_1_QUESTION)).toBeVisible();
    expect(group(SCHEDULE_H_LINE_2_QUESTION)).toBeVisible();
    for (const radio of screen.getAllByRole('radio')) expect(radio).not.toBeChecked();
    expect(screen.queryByText(SCHEDULE_H_LINE_2_SPOUSE_QUESTION)).toBeNull();
    expect(status()).toHaveTextContent(copy.CODEBTOR_GAP_NO_ANSWER);
  });

  it('says why the step asks, and why the address is asked', () => {
    const { unmount } = render(<StepWithRows />);
    expect(screen.getByText(copy.CODEBTORS_STEP_WHY)).toBeInTheDocument();
    unmount();

    render(<StepWithRows initial={[rohan]} initialAnswers={given} />);
    expect(screen.getByText(copy.CODEBTORS_STEP_WHY)).toBeInTheDocument();
    const help = screen.getByText(copy.CODEBTOR_ADDRESS_HELP);
    const street = field('codebtor_street_address_0');
    expect(help.compareDocumentPosition(street) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("asks the spouse's state, name and address only under both Yes answers", async () => {
    render(<StepWithRows />);
    const user = userEvent.setup();

    await user.click(within(group(SCHEDULE_H_LINE_2_QUESTION)).getByRole('radio', { name: 'Yes' }));
    expect(screen.getByText(SCHEDULE_H_LINE_2_SPOUSE_QUESTION)).toBeInTheDocument();
    expect(field('community_state')).toBeNull();

    const spouseGroup = screen.getByRole('group', {
      name: new RegExp(`^${SCHEDULE_H_LINE_2_SPOUSE_QUESTION}`),
    });
    await user.click(within(spouseGroup).getByRole('radio', { name: 'Yes' }));
    const state = field('community_state');
    const name = field('community_spouse_name');
    const street = field('community_spouse_street_address');
    expect(state).not.toBeNull();
    expect(state.compareDocumentPosition(name) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(name.compareDocumentPosition(street) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();

    await user.click(within(spouseGroup).getByRole('radio', { name: 'No' }));
    expect(field('community_state')).toBeNull();
    expect(field('community_spouse_name')).toBeNull();
    expect(field('community_spouse_street_address')).toBeNull();
  });

  it('keeps what was typed under line 2 when the answer is flipped', async () => {
    render(<StepWithRows />);
    const user = userEvent.setup();
    await user.click(within(group(SCHEDULE_H_LINE_2_QUESTION)).getByRole('radio', { name: 'Yes' }));
    const spouseGroup = () =>
      screen.getByRole('group', { name: new RegExp(`^${SCHEDULE_H_LINE_2_SPOUSE_QUESTION}`) });
    await user.click(within(spouseGroup()).getByRole('radio', { name: 'Yes' }));
    await user.type(field('community_state'), 'Illinois');

    await user.click(within(spouseGroup()).getByRole('radio', { name: 'No' }));
    await user.click(within(spouseGroup()).getByRole('radio', { name: 'Yes' }));

    expect(field('community_state')).toHaveValue('Illinois');
  });

  it("holds the spouse's two-letter state to two letters, as the server does", async () => {
    render(
      <StepWithRows
        initialAnswers={{ community_lived: 'yes', community_spouse_lived_with: 'yes' }}
      />
    );
    expect(field('community_spouse_state')).toHaveAttribute('maxlength', '2');
    expect(field('community_state')).toHaveAttribute('maxlength', '100');
    expect(field('community_spouse_name')).toHaveAttribute('maxlength', '255');
  });

  it("writes the spouse's address into the answers", async () => {
    const onAnswersChange = vi.fn();
    render(
      <StepWithRows
        initialAnswers={{ community_lived: 'yes', community_spouse_lived_with: 'yes' }}
        onAnswersChange={onAnswersChange}
      />
    );
    await userEvent.setup().type(field('community_spouse_city'), 'Chi');
    expect(onAnswersChange).toHaveBeenLastCalledWith({
      community_lived: 'yes',
      community_spouse_lived_with: 'yes',
      community_spouse_city: 'Chi',
    });
  });

  it("requires a codebtor's address", async () => {
    const onValidationChange = vi.fn();
    render(
      <StepWithRows
        initial={[{ ...rohan, city: '' }]}
        initialAnswers={given}
        debts={debts}
        onValidationChange={onValidationChange}
      />
    );
    expect(onValidationChange).toHaveBeenLastCalledWith(false);
    expect(status()).toHaveTextContent(
      'Enter the street, city, two-letter state and ZIP for Rohan Demo.'
    );

    await userEvent.setup().type(field('codebtor_city_0'), 'Chicago');
    expect(onValidationChange).toHaveBeenLastCalledWith(true);
  });

  it("lists the filer's amounts owed and contracts by name to link, none picked", () => {
    const { unmount } = render(
      <StepWithRows
        initial={[{ ...rohan, links: [] }]}
        initialAnswers={given}
        debts={debts}
        contracts={contracts}
      />
    );
    const boxes = screen.getAllByRole('checkbox', {
      name: /Demo Card Services|Demo Motors/,
    }) as HTMLInputElement[];
    expect(boxes.map((box) => box.value)).toEqual(['debt-30', 'contract-4']);
    for (const box of boxes) {
      expect(box).not.toBeChecked();
      expect(box).toHaveAttribute('name', 'codebtor_links_0');
    }
    const links = screen.getByRole('group', { name: new RegExp(`^${SCHEDULE_H_COLUMN_2}`) });
    expect(within(links).getByText(copy.CODEBTOR_LINKS_DEBTS)).toBeInTheDocument();
    expect(within(links).getByText(copy.CODEBTOR_LINKS_CONTRACTS)).toBeInTheDocument();
    expect(within(links).getByText(copy.CODEBTOR_LINKS_HELP)).toBeInTheDocument();
    unmount();

    render(<StepWithRows initial={[{ ...rohan, links: [] }]} initialAnswers={given} />);
    expect(screen.getByText(copy.CODEBTOR_LINKS_NONE)).toBeInTheDocument();
  });

  it('counts a link to a removed amount owed as no link', async () => {
    const onRowsChange = vi.fn();
    const { unmount } = render(
      <StepWithRows
        initial={[
          {
            ...rohan,
            links: [
              { kind: 'debt', id: 30 },
              { kind: 'debt', id: 99 },
            ],
          },
        ]}
        initialAnswers={given}
        debts={debts}
        contracts={contracts}
      />
    );
    expect(document.querySelector('[value="debt-30"]')).toBeChecked();
    expect(status()).toBeEmptyDOMElement();
    unmount();

    render(
      <StepWithRows
        initial={[{ ...rohan, links: [{ kind: 'debt', id: 99 }] }]}
        initialAnswers={given}
        debts={debts}
        contracts={contracts}
        onRowsChange={onRowsChange}
      />
    );
    expect(document.querySelector('[value="debt-30"]')).not.toBeChecked();
    expect(status()).toHaveTextContent(fill(copy.CODEBTOR_GAP_NO_LINK, { name: 'Rohan Demo' }));

    await userEvent.setup().click(document.querySelector('[value="contract-4"]') as Element);
    expect(onRowsChange.mock.lastCall?.[0][0].links).toEqual([{ kind: 'contract', id: 4 }]);
  });

  it("disables Continue until the step's gaps clear", () => {
    const onValidationChange = vi.fn();
    const { unmount } = render(<StepWithRows onValidationChange={onValidationChange} />);
    expect(onValidationChange).toHaveBeenLastCalledWith(false);
    unmount();

    render(
      <StepWithRows
        initial={[rohan]}
        initialAnswers={given}
        debts={debts}
        onValidationChange={onValidationChange}
      />
    );
    expect(onValidationChange).toHaveBeenLastCalledWith(true);
  });

  it('starts a new row with no relationship', async () => {
    const onRowsChange = vi.fn();
    render(<StepWithRows initialAnswers={given} onRowsChange={onRowsChange} />);
    await userEvent.setup().click(screen.getByRole('button', { name: /add codebtor/i }));

    expect(field('codebtor_relationship_0')).toHaveValue('');
    expect(onRowsChange.mock.lastCall?.[0][0]).toMatchObject({
      name: '',
      street_address: '',
      street_2: '',
      city: '',
      state: '',
      zip_code: '',
      outside_us: false,
      relationship: '',
      links: [],
    });
  });

  it('shows the rows of a No answer, so the filer can remove them', () => {
    render(
      <StepWithRows initial={[rohan]} initialAnswers={{ ...given, codebtors_answer: 'no' }} />
    );
    expect(field('codebtor_name_0')).toHaveValue('Rohan Demo');
    expect(status()).toHaveTextContent(copy.CODEBTOR_GAP_NO_BUT_LISTED);
  });

  it("ties the missing-name message to the person's name box, so a screen reader hears it there", async () => {
    render(<StepWithRows initial={[rohan]} initialAnswers={given} debts={debts} />);

    const nameBox = field('codebtor_name_0');
    expect(nameBox).toBeValid();

    await userEvent.setup().clear(nameBox);

    expect(nameBox).toBeInvalid();
    expect(nameBox).toHaveAccessibleDescription(copy.CODEBTOR_GAP_NO_NAME);
  });

  it("won't let a stored codebtor go without a name, even with no address", async () => {
    const stored: CodebtorRow = {
      id: 3,
      name: 'Sam Doe',
      street_address: '',
      city: '',
      state: '',
      zip_code: '',
      relationship: 'relative',
      _key: '3',
    };
    const onValidationChange = vi.fn();
    render(
      <StepWithRows
        initial={[stored]}
        initialAnswers={given}
        onValidationChange={onValidationChange}
      />
    );

    const nameBox = field('codebtor_name_0');
    await userEvent.setup().clear(nameBox);

    expect(nameBox).toBeInvalid();
    expect(nameBox).toHaveAccessibleDescription(copy.CODEBTOR_GAP_NO_NAME);
    expect(onValidationChange).toHaveBeenLastCalledWith(false);
  });

  it('keeps the intro that no longer promises a joint filer’s spouse appears', () => {
    render(<StepWithRows />);
    expect(
      screen.getByText('List anyone who is jointly liable on any of your debts.')
    ).toBeInTheDocument();
    expect(screen.queryByText(/filed jointly/i)).toBeNull();
  });

  it('names every box for a screen reader', () => {
    render(
      <StepWithRows initial={[rohan]} initialAnswers={given} debts={debts} contracts={contracts} />
    );

    expect(screen.getByLabelText('Relationship')).toBe(
      screen.getByRole('combobox', { name: 'Relationship' })
    );
    for (const label of [CLAIM_STREET_LABEL, AB_CITY_LABEL, AB_STATE_LABEL, AB_ZIP_LABEL]) {
      expect(screen.getByRole('textbox', { name: new RegExp(`^${label}`) })).toBeVisible();
    }
  });

  it('has no axe violations', async () => {
    const empty = render(<StepWithRows />);
    expect(await axe(empty.container)).toHaveNoViolations();
    empty.unmount();

    const full = render(
      <StepWithRows
        initial={[rohan]}
        initialAnswers={{
          codebtors_answer: 'yes',
          community_lived: 'yes',
          community_spouse_lived_with: 'yes',
          community_state: 'Illinois',
          community_spouse_name: 'Demo Spouse',
          community_spouse_street_address: '1 Demo Way',
          community_spouse_city: 'Chicago',
          community_spouse_state: 'IL',
          community_spouse_zip_code: '60601',
        }}
        debts={debts}
        contracts={contracts}
      />
    );
    expect(await axe(full.container)).toHaveNoViolations();
  });
});
