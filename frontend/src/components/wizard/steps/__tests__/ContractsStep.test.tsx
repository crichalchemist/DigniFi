import { useState } from 'react';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';
import { ContractsStep } from '../ContractsStep';
import { fill } from '../claims/claimNames';
import * as copy from '../../../../constants/copy';
import {
  SCHEDULE_G_LINE_1_QUESTION,
  SCHEDULE_G_NAME_LABEL,
  SCHEDULE_G_PURPOSE_LABEL,
} from '../../../../constants/formText';
import type { AssetInfo, ContractRow, DebtRow, WizardRow, YesNo } from '../../../../types/api';

// The server refuses a contract whose other party's name is longer than its column holds,
// and the wizard can only say it couldn't save, so Continue would never succeed. The box
// stops at that length instead.

const assets: WizardRow<AssetInfo>[] = [
  {
    _key: '20',
    id: 20,
    ab_line: '3',
    description: '',
    details: { year: '2019', make: 'Demo', model: 'Corolla' },
  },
  {
    _key: '22',
    id: 22,
    ab_line: '4',
    description: 'Demo Park trailer',
    details: { lives_here: 'yes' },
  },
  { _key: '21', id: 21, ab_line: '1', description: '12 Demo Street' },
];
const debts: DebtRow[] = [
  {
    _key: '30',
    id: 30,
    creditor_name: 'Demo Auto Credit',
    is_secured: true,
    secured_by: 20,
    monthly_payment: 389,
  },
];
const leaseRow: ContractRow = {
  _key: '4',
  id: 4,
  counterparty_name: 'Demo Motors',
  street_address: '1 Demo St',
  street_2: '',
  city: 'Chicago',
  state: 'IL',
  zip_code: '60601',
  outside_us: false,
  contract_type: 'lease',
  description: 'Car lease',
  lease_kind: 'vehicle',
  vehicle_asset: 20,
  monthly_payment: 389,
  owes_now: 'no',
  owed_debt: null,
};

interface HarnessProps {
  initial?: ContractRow[];
  answer?: YesNo | null;
  debts?: DebtRow[];
  assets?: WizardRow<AssetInfo>[];
  onRowsChange?: (rows: ContractRow[]) => void;
  onValidationChange?: (isValid: boolean) => void;
  onGoToStep?: (stepNumber: number) => void;
}

/** The wizard's part: it holds the rows and the answer the step shows */
function StepWithRows({
  initial = [],
  answer: initialAnswer = 'yes',
  debts: heldDebts = [],
  assets: heldAssets = [],
  onRowsChange = () => {},
  onValidationChange = () => {},
  onGoToStep = vi.fn(),
}: HarnessProps) {
  const [rows, setRows] = useState<ContractRow[]>(initial);
  const [answer, setAnswer] = useState<YesNo | null>(initialAnswer);
  return (
    <ContractsStep
      rows={rows}
      onRowsChange={(next) => {
        setRows(next);
        onRowsChange(next);
      }}
      answer={answer}
      onAnswerChange={setAnswer}
      debts={heldDebts}
      assets={heldAssets}
      onValidationChange={onValidationChange}
      onGoToStep={onGoToStep}
    />
  );
}

const field = (name: string) => document.querySelector(`[name="${name}"]`) as HTMLInputElement;
const nameBox = () =>
  screen.getByRole('textbox', { name: new RegExp(`^${SCHEDULE_G_NAME_LABEL}`) });

describe('ContractsStep', () => {
  it("keeps the other party's name within the length the server stores, so a long name never blocks Continue", async () => {
    const onRowsChange = vi.fn();
    render(<StepWithRows initial={[leaseRow]} onRowsChange={onRowsChange} />);

    const user = userEvent.setup();
    await user.clear(nameBox());
    await user.paste('O'.repeat(300));

    expect(onRowsChange).toHaveBeenLastCalledWith([
      { ...leaseRow, counterparty_name: 'O'.repeat(255) },
    ]);
  });

  it("ties the missing-name message to the other party's name box, so a screen reader hears it there", async () => {
    render(<StepWithRows initial={[leaseRow]} />);

    expect(nameBox()).toBeValid();

    await userEvent.setup().clear(nameBox());

    expect(nameBox()).toBeInvalid();
    expect(nameBox()).toHaveAccessibleDescription(copy.CONTRACT_GAP_NO_NAME);
  });

  it("won't let a stored contract go without its other party's name, even with nothing else typed", async () => {
    const gym: ContractRow = {
      _key: '5',
      id: 5,
      counterparty_name: 'Metro Gym',
      contract_type: 'contract',
      description: '',
    };
    const onValidationChange = vi.fn();
    render(<StepWithRows initial={[gym]} onValidationChange={onValidationChange} />);

    await userEvent.setup().clear(nameBox());

    expect(nameBox()).toBeInvalid();
    expect(nameBox()).toHaveAccessibleDescription(copy.CONTRACT_GAP_NO_NAME);
    expect(onValidationChange).toHaveBeenLastCalledWith(false);
  });

  it('names every box for a screen reader', () => {
    render(<StepWithRows initial={[leaseRow]} />);

    expect(screen.getByLabelText(/^Type/)).toBe(screen.getByRole('combobox', { name: /^Type/ }));
    expect(screen.getByLabelText(new RegExp(`^${SCHEDULE_G_PURPOSE_LABEL}`))).toBe(
      screen.getByRole('textbox', { name: new RegExp(`^${SCHEDULE_G_PURPOSE_LABEL}`) })
    );
  });

  it('gives a lease, not a loan, as its example', () => {
    render(<StepWithRows initial={[leaseRow]} />);

    expect(screen.getByPlaceholderText('e.g., Apartment lease, car lease')).toBeInTheDocument();
  });

  it("asks G's question first with nothing checked", () => {
    render(<StepWithRows answer={null} />);

    const group = screen.getByRole('group', { name: new RegExp(`^${SCHEDULE_G_LINE_1_QUESTION}`) });
    const radios = within(group).getAllByRole('radio');
    expect(radios).toHaveLength(2);
    radios.forEach((radio) => {
      expect(radio).toHaveAttribute('name', 'contracts_answer');
      expect(radio).not.toBeChecked();
    });
    expect(field('counterparty_name_0')).toBeNull();
    expect(screen.queryByRole('button', { name: /add contract/i })).not.toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent(copy.CONTRACT_GAP_NO_ANSWER);
  });

  it("disables Continue until the step's gaps clear", async () => {
    const onValidationChange = vi.fn();
    const { unmount } = render(
      <StepWithRows answer={null} onValidationChange={onValidationChange} />
    );
    expect(onValidationChange).toHaveBeenLastCalledWith(false);

    await userEvent
      .setup()
      .click(document.querySelector('[name="contracts_answer"][value="yes"]')!);
    expect(onValidationChange).toHaveBeenLastCalledWith(false);
    expect(screen.getByRole('status')).toHaveTextContent(copy.CONTRACT_GAP_YES_BUT_NONE);
    unmount();

    const valid = vi.fn();
    render(
      <StepWithRows initial={[leaseRow]} debts={debts} assets={assets} onValidationChange={valid} />
    );
    expect(valid).toHaveBeenLastCalledWith(true);
    expect(screen.getByRole('status')).toBeEmptyDOMElement();
  });

  it('asks the kind of lease only on a lease, and a vehicle and payment only on a vehicle lease', async () => {
    const plain: ContractRow = { ...leaseRow, contract_type: 'contract', lease_kind: null };
    const { unmount } = render(<StepWithRows initial={[plain]} assets={assets} />);
    expect(field('lease_kind_0')).toBeNull();
    unmount();

    render(<StepWithRows initial={[{ ...leaseRow, lease_kind: null }]} assets={assets} />);
    expect(field('lease_kind_0')).not.toBeNull();
    expect(field('vehicle_asset_0')).toBeNull();
    expect(field('monthly_payment_0')).toBeNull();

    await userEvent.setup().selectOptions(field('lease_kind_0'), 'vehicle');
    expect(field('vehicle_asset_0')).not.toBeNull();
    expect(field('monthly_payment_0')).not.toBeNull();
  });

  it('leaves out of the vehicle picker a row answered "I live here"', () => {
    render(<StepWithRows initial={[leaseRow]} assets={assets} />);

    const options = within(field('vehicle_asset_0')).getAllByRole('option');
    expect(options.map((option) => option.textContent)).toEqual([
      'Choose one',
      'Line 3: 2019 Demo Corolla',
    ]);
  });

  it('says why the step asks, and why the address is asked', () => {
    const { unmount } = render(<StepWithRows />);
    expect(screen.getByText(copy.CONTRACTS_STEP_WHY)).toBeInTheDocument();
    unmount();

    render(<StepWithRows initial={[leaseRow]} assets={assets} />);
    expect(screen.getByText(copy.CONTRACTS_STEP_WHY)).toBeInTheDocument();
    const help = screen.getByText(copy.CONTRACT_ADDRESS_HELP);
    const street = field('street_address_0');
    expect(help.compareDocumentPosition(street) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('lists the filer\'s amounts owed for "owe money on this now", none picked, and links to Amounts Owed', async () => {
    const onGoToStep = vi.fn();
    render(
      <StepWithRows initial={[leaseRow]} debts={debts} assets={assets} onGoToStep={onGoToStep} />
    );
    const user = userEvent.setup();
    await user.click(document.querySelector('[name="owes_now_0"][value="yes"]')!);

    const picker = field('owed_debt_0') as unknown as HTMLSelectElement;
    const options = within(picker).getAllByRole('option') as HTMLOptionElement[];
    expect(options.map((option) => [option.textContent, option.value])).toEqual([
      ['Choose one', ''],
      ['Demo Auto Credit', '30'],
    ]);
    expect(picker.value).toBe('');
    expect(screen.getByText(copy.OWES_NOW_ADD_HELP)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: copy.GO_TO_AMOUNTS_OWED }));
    expect(onGoToStep).toHaveBeenCalledWith(6);
  });

  it('clears the picked amount owed when the filer answers No', async () => {
    const onRowsChange = vi.fn();
    render(
      <StepWithRows
        initial={[{ ...leaseRow, owes_now: 'yes', owed_debt: 30 }]}
        debts={debts}
        assets={assets}
        onRowsChange={onRowsChange}
      />
    );
    await userEvent.setup().click(document.querySelector('[name="owes_now_0"][value="no"]')!);

    const [row] = onRowsChange.mock.calls.at(-1)![0] as ContractRow[];
    expect(row.owed_debt).toBeNull();
    expect(row.owes_now).toBe('no');
  });

  it('names the same-vehicle overlap until one payment is 0', async () => {
    const onValidationChange = vi.fn();
    render(
      <StepWithRows
        initial={[{ ...leaseRow, owes_now: 'yes', owed_debt: 30 }]}
        debts={debts}
        assets={assets}
        onValidationChange={onValidationChange}
      />
    );
    const sentence = fill(copy.CONTRACT_GAP_SAME_VEHICLE, {
      name: 'Demo Motors',
      debt: 'Demo Auto Credit',
    });
    expect(screen.getByRole('status')).toHaveTextContent(sentence);
    expect(onValidationChange).toHaveBeenLastCalledWith(false);

    const user = userEvent.setup();
    await user.clear(field('monthly_payment_0'));
    await user.type(field('monthly_payment_0'), '0');

    expect(screen.getByRole('status')).not.toHaveTextContent(sentence);
    expect(onValidationChange).toHaveBeenLastCalledWith(true);
  });

  it('starts a new row with no kind', async () => {
    const onRowsChange = vi.fn();
    render(<StepWithRows answer="yes" onRowsChange={onRowsChange} />);
    await userEvent.setup().click(screen.getByRole('button', { name: /add contract/i }));

    expect(field('contract_type_0').value).toBe('');
    const [row] = onRowsChange.mock.calls.at(-1)![0] as ContractRow[];
    expect(row.contract_type).toBe('');
  });

  it('keeps showing the rows under a No, so the gap that names them points at something', () => {
    render(<StepWithRows initial={[leaseRow]} answer="no" assets={assets} />);
    expect(field('counterparty_name_0')).not.toBeNull();
    expect(screen.getByRole('status')).toHaveTextContent(copy.CONTRACT_GAP_NO_BUT_LISTED);
  });

  it('has no axe violations', async () => {
    const full = render(
      <StepWithRows
        initial={[{ ...leaseRow, owes_now: 'yes', owed_debt: 30, monthly_payment: 0 }]}
        debts={debts}
        assets={assets}
      />
    );
    expect(await axe(full.container)).toHaveNoViolations();
    full.unmount();

    const empty = render(<StepWithRows answer={null} />);
    expect(await axe(empty.container)).toHaveNoViolations();
  });
});
