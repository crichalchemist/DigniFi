import { useState } from 'react';
import { fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';
import { DebtsStep } from '../DebtsStep';
import { fill } from '../claims/claimNames';
import * as copy from '../../../../constants/copy';
import type { AssetInfo, DebtInfo, DebtRow, LegacyField, WizardRow } from '../../../../types/api';

// DebtsStep shows and edits the wizard's debt rows, asks every question Schedules D and E/F
// ask of one, and reports whether the step can continue.

const baseDebt: WizardRow<DebtInfo> = {
  _key: '1',
  id: 1,
  session: 42,
  debt_type: 'credit_card',
  creditor_name: 'Chase Bank',
  account_number: '',
  amount_owed: 2500,
  monthly_payment: 50,
  is_secured: false,
  collateral_description: '',
  is_draft: false,
  source_document_name: null,
};

const noop = () => {};

const complete: DebtRow = {
  _key: 'c1',
  id: 1,
  debt_type: 'credit_card',
  creditor_name: 'Demo Card Services',
  account_number: '',
  amount_owed: 500,
  monthly_payment: null as unknown as undefined,
  is_secured: false,
  collateral_description: '',
  street_address: '12 Demo Street',
  street_2: '',
  city: 'Demo City',
  state: 'IL',
  zip_code: '60601',
  outside_us: false,
  secured_by: null,
  home_payment_line: null,
  collateral_who: null,
  lien: null,
  claim_status: [],
  offset_answer: 'no',
  notice_parties: [],
  community_debt: '',
  date_incurred: '',
  _securedPressed: true,
};

const car: WizardRow<AssetInfo> = {
  _key: '3',
  id: 3,
  ab_line: '3',
  details: { make: 'Demo', model: 'Sedan' },
};

const secured: DebtRow = {
  ...complete,
  _key: 's1',
  id: 2,
  debt_type: 'auto_loan',
  is_secured: true,
  secured_by: 3,
  collateral_description: '2014 Demo Sedan',
  lien: { kinds: ['agreement'], other: '' },
  monthly_payment: 0,
  offset_answer: null,
};

function Harness({
  initial = [],
  assets = [],
  onChange = noop,
  onValidity = noop,
  legacyGaps,
  onRemoveLegacy,
}: {
  initial?: DebtRow[];
  assets?: WizardRow<AssetInfo>[];
  onChange?: (rows: DebtRow[]) => void;
  onValidity?: (valid: boolean) => void;
  legacyGaps?: { field: LegacyField; sentence: string }[];
  onRemoveLegacy?: (field: LegacyField) => Promise<void>;
}) {
  const [rows, setRows] = useState<DebtRow[]>(initial);
  const [noDebts, setNoDebts] = useState(false);
  return (
    <DebtsStep
      rows={rows}
      onRowsChange={(next) => {
        setRows(next);
        onChange(next);
      }}
      noDebts={noDebts}
      onNoDebtsChange={setNoDebts}
      assets={assets}
      onValidationChange={onValidity}
      legacyGaps={legacyGaps}
      onRemoveLegacy={onRemoveLegacy}
    />
  );
}

const status = () => screen.getByRole('status');
const field = (name: string) => document.querySelector(`[name="${name}"]`) as HTMLInputElement;
const box = (name: string, value: string) =>
  document.querySelector(`[name="${name}"][value="${value}"]`) as HTMLInputElement;
const all = (selector: string) => document.querySelectorAll(selector);
const lastRows = (fn: ReturnType<typeof vi.fn>) => fn.mock.lastCall![0] as DebtRow[];
const lastValidity = (fn: ReturnType<typeof vi.fn>) => fn.mock.lastCall![0] as boolean;

describe('DebtsStep draft badge', () => {
  const props = { noDebts: false, onNoDebtsChange: noop, assets: [] };

  it('renders "From scan" badge when is_draft is true', () => {
    const draftDebt: WizardRow<DebtInfo> = { ...baseDebt, is_draft: true };

    render(
      <DebtsStep rows={[draftDebt]} onRowsChange={noop} onValidationChange={noop} {...props} />
    );

    expect(screen.getByText('From scan')).toBeInTheDocument();
  });

  it('does not render a badge when is_draft is false', () => {
    const manualDebt: WizardRow<DebtInfo> = { ...baseDebt, is_draft: false };

    render(
      <DebtsStep rows={[manualDebt]} onRowsChange={noop} onValidationChange={noop} {...props} />
    );

    expect(screen.queryByText('From scan')).not.toBeInTheDocument();
  });

  it('does not render a badge when is_draft is absent', () => {
    // Omit is_draft entirely to verify the badge is absent when the field is missing
    const debtWithoutDraft: WizardRow<DebtInfo> = {
      _key: baseDebt._key,
      id: baseDebt.id,
      session: baseDebt.session,
      debt_type: baseDebt.debt_type,
      creditor_name: baseDebt.creditor_name,
      amount_owed: baseDebt.amount_owed,
      monthly_payment: baseDebt.monthly_payment,
      is_secured: baseDebt.is_secured,
    };

    render(
      <DebtsStep
        rows={[debtWithoutDraft]}
        onRowsChange={noop}
        onValidationChange={noop}
        {...props}
      />
    );

    expect(screen.queryByText('From scan')).not.toBeInTheDocument();
  });

  it('renders badge on each draft debt in a mixed list', () => {
    const manualDebt: WizardRow<DebtInfo> = {
      ...baseDebt,
      _key: '2',
      id: 2,
      creditor_name: 'Manual Citi',
      is_draft: false,
    };
    const draftDebt: WizardRow<DebtInfo> = {
      ...baseDebt,
      _key: '3',
      id: 3,
      creditor_name: 'Scanned Wells Fargo',
      is_draft: true,
    };

    render(
      <DebtsStep
        rows={[manualDebt, draftDebt]}
        onRowsChange={noop}
        onValidationChange={noop}
        {...props}
      />
    );

    // Only the draft entry gets a badge — the manual entry must not.
    expect(screen.getAllByText('From scan')).toHaveLength(1);
  });

  it('renders badges on all draft debts when multiple are present', () => {
    const draftA: WizardRow<DebtInfo> = {
      ...baseDebt,
      _key: '10',
      id: 10,
      creditor_name: 'Scanned Amex',
      is_draft: true,
    };
    const draftB: WizardRow<DebtInfo> = {
      ...baseDebt,
      _key: '11',
      id: 11,
      creditor_name: 'Scanned Discover',
      is_draft: true,
      source_document_name: 'credit_report.pdf',
    };

    render(
      <DebtsStep rows={[draftA, draftB]} onRowsChange={noop} onValidationChange={noop} {...props} />
    );

    expect(screen.getAllByText('From scan')).toHaveLength(2);
  });

  it('badge has the correct aria-label for screen reader users', () => {
    const draftDebt: WizardRow<DebtInfo> = { ...baseDebt, is_draft: true };

    render(
      <DebtsStep rows={[draftDebt]} onRowsChange={noop} onValidationChange={noop} {...props} />
    );

    expect(
      screen.getByRole('generic', { name: /pre-filled from document scan/i })
    ).toBeInTheDocument();
  });
});

// Schedule D lists a secured amount owed with what secures it, and the server reads both
// under these names: a renamed key is dropped without an error (DIG-26)
describe('DebtsStep secured amounts owed', () => {
  it('marks a car loan secured and keeps what secures it, under the names the server stores', async () => {
    const onChange = vi.fn();
    render(<Harness onChange={onChange} />);
    const user = userEvent.setup();

    await user.selectOptions(field('debt_type_0'), 'Car or vehicle loan');
    expect(box('is_secured_0', 'yes')).toBeChecked();
    await user.type(field('collateral_description_0'), '2015 Honda Civic');

    expect(onChange).toHaveBeenLastCalledWith([
      expect.objectContaining({
        debt_type: 'auto_loan',
        is_secured: true,
        collateral_description: '2015 Honda Civic',
      }),
    ]);
  });

  // Draft until counsel rules on C-17 (DIG-280)
  it("gives a creditor, not a collector, as the name's example", () => {
    render(<Harness />);
    expect(screen.getByPlaceholderText('e.g., Capital One, Dr. Smith')).toBeInTheDocument();
  });
});

describe('DebtsStep asks every question', () => {
  it("disables Continue until the step's gaps clear, and says the first one", () => {
    const onValidity = vi.fn();
    const { unmount } = render(<Harness onValidity={onValidity} />);
    expect(status()).toHaveTextContent(copy.DEBT_GAP_NO_ANSWER);
    expect(lastValidity(onValidity)).toBe(false);
    unmount();

    const second = vi.fn();
    const again = render(
      <Harness initial={[{ ...complete, street_address: '' }]} onValidity={second} />
    );
    expect(status()).toHaveTextContent(
      fill(copy.CLAIM_GAP_ADDRESS, { name: 'Demo Card Services' })
    );
    expect(lastValidity(second)).toBe(false);
    again.unmount();

    const third = vi.fn();
    render(<Harness initial={[complete]} onValidity={third} />);
    expect(status()).toBeEmptyDOMElement();
    expect(lastValidity(third)).toBe(true);
  });

  it('lets a scanned draft with no other gap press Continue', () => {
    const onValidity = vi.fn();
    render(
      <Harness
        initial={[{ ...complete, is_draft: true, _securedPressed: false }]}
        onValidity={onValidity}
      />
    );
    expect(lastValidity(onValidity)).toBe(true);
  });

  it('shows a stored amount of 0 as an empty box, and a payment of 0 as 0', () => {
    render(<Harness initial={[{ ...complete, amount_owed: 0, monthly_payment: 0 }]} />);
    expect(field('amount_owed_0').value).toBe('');
    expect(field('monthly_payment_0').value).toBe('0');
  });

  it('keeps what the filer typed in the amount box', () => {
    const onChange = vi.fn();
    render(<Harness initial={[complete]} onChange={onChange} />);

    fireEvent.input(field('amount_owed_0'), { target: { value: '0' } });
    expect(field('amount_owed_0').value).toBe('0');

    fireEvent.input(field('amount_owed_0'), { target: { value: '-5' } });
    expect(screen.getByText(copy.AMOUNT_NEGATIVE)).toBeInTheDocument();
    expect(lastRows(onChange)[0].amount_owed).toBe(0);
  });

  it('holds Continue while a box shows a figure the row does not hold, and frees it once corrected', () => {
    const cases: [string, string, string, number | undefined, string][] = [
      ['amount_owed_0', '12345678901', copy.AMOUNT_TOO_LARGE, 500, '1234'],
      ['monthly_payment_0', '75.555', copy.AMOUNT_DECIMALS, undefined, '75.5'],
      ['amount_owed_0', '-2500', copy.AMOUNT_NEGATIVE, 500, '2500'],
    ];
    for (const [name, refused, sentence, lastGood, good] of cases) {
      const onChange = vi.fn();
      const onValidity = vi.fn();
      const { unmount } = render(
        <Harness initial={[complete]} onChange={onChange} onValidity={onValidity} />
      );
      expect(lastValidity(onValidity)).toBe(true);

      fireEvent.input(field(name), { target: { value: refused } });
      expect(screen.getByText(sentence)).toBeInTheDocument();
      expect(field(name).value).toBe(refused);
      expect(lastValidity(onValidity)).toBe(false);
      if (onChange.mock.calls.length > 0) {
        const key = name.startsWith('amount') ? 'amount_owed' : 'monthly_payment';
        expect(lastRows(onChange)[0][key]).toBe(lastGood);
      }

      fireEvent.input(field(name), { target: { value: good } });
      expect(screen.queryByText(sentence)).not.toBeInTheDocument();
      expect(lastValidity(onValidity)).toBe(true);
      const key = name.startsWith('amount') ? 'amount_owed' : 'monthly_payment';
      expect(lastRows(onChange)[0][key]).toBe(Number(good));
      unmount();
    }
  });

  it('holds Continue while an amount box holds only part of a number', () => {
    const onValidity = vi.fn();
    render(<Harness initial={[complete]} onValidity={onValidity} />);
    expect(lastValidity(onValidity)).toBe(true);

    // jsdom does not report badInput for a number box holding text that is not a number, so
    // the test forces it with Object.defineProperty
    const input = field('amount_owed_0');
    Object.defineProperty(input, 'validity', { value: { badInput: true }, configurable: true });
    fireEvent.input(input);
    expect(lastValidity(onValidity)).toBe(false);
  });

  describe('the secured answer and the kind', () => {
    it('leaves a pressed secured answer alone when the type changes, and sets an unpressed one', async () => {
      const user = userEvent.setup();

      const pressedChange = vi.fn();
      const pressed = render(
        <Harness initial={[{ ...complete, _securedPressed: true }]} onChange={pressedChange} />
      );
      await user.selectOptions(field('debt_type_0'), 'auto_loan');
      expect(lastRows(pressedChange)[0]).toMatchObject({
        debt_type: 'auto_loan',
        is_secured: false,
      });
      pressed.unmount();

      const unpressedChange = vi.fn();
      const unpressed = render(
        <Harness initial={[{ ...complete, _securedPressed: false }]} onChange={unpressedChange} />
      );
      await user.selectOptions(field('debt_type_0'), 'auto_loan');
      expect(lastRows(unpressedChange)[0].is_secured).toBe(true);
      unpressed.unmount();

      const firstPressed = vi.fn();
      // A row with no kind shows no answer, so No is a press (a radio already showing No is not)
      render(
        <Harness
          initial={[{ ...complete, debt_type: undefined, _securedPressed: false }]}
          onChange={firstPressed}
        />
      );
      await user.click(box('is_secured_0', 'no'));
      await user.selectOptions(field('debt_type_0'), 'auto_loan');
      expect(lastRows(firstPressed)[0]).toMatchObject({ is_secured: false, _securedPressed: true });
    });

    it('treats a scanned draft as unpressed, so correcting its type to a car loan answers Yes', async () => {
      const user = userEvent.setup();
      render(
        <Harness
          initial={[{ ...complete, is_draft: true, debt_type: 'other', _securedPressed: false }]}
        />
      );
      await user.selectOptions(field('debt_type_0'), 'auto_loan');
      expect(box('is_secured_0', 'yes')).toBeChecked();
    });

    it('starts every radio, select and tick unanswered', async () => {
      const user = userEvent.setup();
      render(<Harness />);
      expect(all('input[type=radio]:checked')).toHaveLength(0);
      expect(all('input[type=checkbox]:checked')).toHaveLength(0);
      expect(field('debt_type_0').value).toBe('');

      await user.selectOptions(field('debt_type_0'), 'auto_loan');
      const checked = all('input[type=radio]:checked');
      expect(checked).toHaveLength(1);
      expect(checked[0]).toBe(box('is_secured_0', 'yes'));
      expect(all('input[type=checkbox]:checked')).toHaveLength(0);
      expect(field('secured_by_0').value).toBe('');
    });

    it('says the secured answer was filled in from the kind, until the filer presses it', async () => {
      const user = userEvent.setup();
      const first = render(<Harness />);
      expect(screen.queryByText(copy.SECURED_PREFILLED_NOTE)).not.toBeInTheDocument();
      await user.selectOptions(field('debt_type_0'), 'auto_loan');
      expect(screen.getByText(copy.SECURED_PREFILLED_NOTE)).toBeInTheDocument();
      await user.click(box('is_secured_0', 'no'));
      expect(screen.queryByText(copy.SECURED_PREFILLED_NOTE)).not.toBeInTheDocument();
      first.unmount();

      const loaded = render(
        <Harness initial={[{ ...secured, _securedPressed: true }]} assets={[car]} />
      );
      expect(screen.queryByText(copy.SECURED_PREFILLED_NOTE)).not.toBeInTheDocument();
      loaded.unmount();

      render(
        <Harness
          initial={[{ ...secured, is_draft: true, _securedPressed: false }]}
          assets={[car]}
        />
      );
      expect(screen.getByText(copy.SECURED_PREFILLED_NOTE)).toBeInTheDocument();
    });
  });

  it('"None of these" and a status tick exclude each other', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<Harness initial={[{ ...complete, claim_status: null }]} onChange={onChange} />);

    await user.click(box('claim_status_0', 'contingent'));
    await user.click(box('claim_status_0', 'none'));
    expect(lastRows(onChange)[0].claim_status).toEqual([]);
    expect(box('claim_status_0', 'contingent')).not.toBeChecked();

    await user.click(box('claim_status_0', 'disputed'));
    expect(lastRows(onChange)[0].claim_status).toEqual(['disputed']);
    await user.click(box('claim_status_0', 'disputed'));
    expect(lastRows(onChange)[0].claim_status).toBeNull();

    await user.click(box('claim_status_0', 'disputed'));
    await user.click(box('claim_status_0', 'contingent'));
    expect(lastRows(onChange)[0].claim_status).toEqual(['contingent', 'disputed']);
  });

  it('picking a property leaves the others unselected', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    const first = { ...secured, _key: 's1', id: 2, secured_by: null };
    const second = { ...secured, _key: 's2', id: 3, secured_by: null };
    render(
      <Harness
        initial={[first, second]}
        assets={[car, { ...car, _key: '4', id: 4 }]}
        onChange={onChange}
      />
    );
    await user.selectOptions(field('secured_by_0'), '3');
    const rows = lastRows(onChange);
    expect(rows[0].secured_by).toBe(3);
    expect(rows[1].secured_by).toBeNull();
    expect(field('secured_by_1').value).toBe('');
  });

  it('asks first or additional only on a link to a row answered "I live here"', () => {
    const home = {
      _key: '3',
      id: 3,
      ab_line: '1',
      details: { street: '12 Demo Street', lives_here: 'yes' as const },
    };
    const first = render(<Harness initial={[secured]} assets={[home]} />);
    const radios = all('[name="home_payment_line_0"]');
    expect(radios).toHaveLength(2);
    expect(all('[name="home_payment_line_0"]:checked')).toHaveLength(0);
    first.unmount();

    const no = render(
      <Harness
        initial={[secured]}
        assets={[{ ...home, details: { ...home.details, lives_here: 'no' as const } }]}
      />
    );
    expect(all('[name="home_payment_line_0"]')).toHaveLength(0);
    no.unmount();

    render(<Harness initial={[{ ...secured, secured_by: null }]} assets={[home]} />);
    expect(all('[name="home_payment_line_0"]')).toHaveLength(0);
  });

  it("asks who owns it only on a link to a row whose shape doesn't ask", () => {
    const piano = { _key: '3', id: 3, ab_line: '6', description: 'Demo Piano' };
    const first = render(<Harness initial={[secured]} assets={[piano]} />);
    expect(all('[name="collateral_who_0"]')).toHaveLength(2);
    first.unmount();

    render(<Harness initial={[secured]} assets={[car]} />);
    expect(all('[name="collateral_who_0"]')).toHaveLength(0);
  });

  it('asks offset only on an unsecured row', () => {
    const first = render(<Harness initial={[complete]} />);
    expect(all('[name="offset_answer_0"]')).toHaveLength(2);
    expect(screen.getByText(copy.OFFSET_HELP)).toBeInTheDocument();
    first.unmount();

    render(<Harness initial={[secured]} assets={[car]} />);
    expect(all('[name="offset_answer_0"]')).toHaveLength(0);
    expect(screen.queryByText(copy.OFFSET_HELP)).not.toBeInTheDocument();
  });

  it('says why the step asks, under its intro', () => {
    const first = render(<Harness />);
    expect(screen.getByText(copy.DEBTS_STEP_WHY)).toBeInTheDocument();
    first.unmount();
    render(<Harness initial={[complete]} />);
    expect(screen.getByText(copy.DEBTS_STEP_WHY)).toBeInTheDocument();
  });

  it('shows the co-owned note when the linked row says it is shared', () => {
    const shared = render(
      <Harness
        initial={[secured]}
        assets={[{ ...car, details: { make: 'Demo', who: 'with_someone' } }]}
      />
    );
    expect(screen.getByText(copy.CO_OWNED_NOTE)).toBeInTheDocument();
    shared.unmount();

    render(
      <Harness
        initial={[secured]}
        assets={[{ ...car, details: { make: 'Demo', who: 'only_you' } }]}
      />
    );
    expect(screen.queryByText(copy.CO_OWNED_NOTE)).not.toBeInTheDocument();
  });

  it("shows the co-owned note when the debt's own who answer says it is shared", () => {
    const piano = { _key: '3', id: 3, ab_line: '6', description: 'Demo Piano' };
    const shared = render(
      <Harness initial={[{ ...secured, collateral_who: 'with_someone' }]} assets={[piano]} />
    );
    expect(screen.getByText(copy.CO_OWNED_NOTE)).toBeInTheDocument();
    shared.unmount();

    render(<Harness initial={[{ ...secured, collateral_who: 'only_you' }]} assets={[piano]} />);
    expect(screen.queryByText(copy.CO_OWNED_NOTE)).not.toBeInTheDocument();
  });

  it('shows no property picked once the linked row is removed on Assets', () => {
    const view = render(
      <Harness initial={[{ ...secured, creditor_name: 'Demo Card Services' }]} assets={[]} />
    );
    expect(field('secured_by_0').value).toBe('');
    expect(status()).toHaveTextContent(
      fill(copy.DEBT_GAP_PROPERTY, { name: 'Demo Card Services' })
    );
    view.rerender(
      <Harness initial={[{ ...secured, creditor_name: 'Demo Card Services' }]} assets={[car]} />
    );
    expect(field('secured_by_0').value).toBe('3');
  });

  it('clears the state and ZIP when the filer ticks outside the US', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<Harness initial={[complete]} onChange={onChange} />);

    await user.click(field('outside_us_0'));
    expect(lastRows(onChange)[0]).toMatchObject({ outside_us: true, state: '', zip_code: '' });
    expect(field('state_0')).toBeNull();
    expect(field('zip_code_0')).toBeNull();

    await user.click(field('outside_us_0'));
    expect(field('state_0').value).toBe('');
    expect(field('zip_code_0').value).toBe('');
  });

  it('lets the filer remove the last row and press "I have no amounts owed"', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    const onValidity = vi.fn();
    render(<Harness initial={[complete]} onChange={onChange} onValidity={onValidity} />);

    await user.click(screen.getByRole('button', { name: 'Remove amount owed 1' }));
    expect(lastRows(onChange)).toEqual([]);

    const none = screen.getByRole('button', { name: copy.NO_DEBTS_BUTTON });
    expect(none).toHaveAttribute('aria-pressed', 'false');
    await user.click(none);
    expect(none).toHaveAttribute('aria-pressed', 'true');
    expect(status()).toBeEmptyDOMElement();
    expect(lastValidity(onValidity)).toBe(true);

    await user.type(field('creditor_name_0'), 'D');
    expect(screen.queryByRole('button', { name: copy.NO_DEBTS_BUTTON })).not.toBeInTheDocument();
  });

  it('brings back an empty blank row after the last typed row is removed', async () => {
    const user = userEvent.setup();
    render(<Harness />);

    await user.type(field('amount_owed_0'), '500');
    await user.type(field('monthly_payment_0'), '40');
    expect(field('amount_owed_0').value).toBe('500');

    await user.click(screen.getByRole('button', { name: 'Remove amount owed 1' }));
    expect(field('amount_owed_0').value).toBe('');
    expect(field('monthly_payment_0').value).toBe('');
  });

  it('clears the property link and its answers when the filer answers No to secured', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <Harness
        initial={[{ ...secured, home_payment_line: 'first', collateral_who: 'with_someone' }]}
        assets={[car]}
        onChange={onChange}
      />
    );
    await user.click(box('is_secured_0', 'no'));
    expect(lastRows(onChange)[0]).toMatchObject({
      is_secured: false,
      secured_by: null,
      home_payment_line: null,
      collateral_who: null,
    });
  });

  it('clears the secured side when an unpressed secured row changes to an unsecured kind', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(
      <Harness
        initial={[
          {
            ...secured,
            _securedPressed: false,
            home_payment_line: 'first',
            collateral_who: 'with_someone',
          },
        ]}
        assets={[car]}
        onChange={onChange}
      />
    );
    await user.selectOptions(field('debt_type_0'), 'credit_card');
    expect(lastRows(onChange)[0]).toMatchObject({
      debt_type: 'credit_card',
      is_secured: false,
      secured_by: null,
      home_payment_line: null,
      collateral_who: null,
    });
  });

  it('says where other property is listed when the Assets step holds none, and only then', () => {
    const none = render(<Harness initial={[secured]} assets={[]} />);
    expect(screen.getByText(copy.SECURING_PROPERTY_NONE)).toBeInTheDocument();
    expect(field('secured_by_0').getAttribute('aria-describedby')).toContain('secured_by_0-help');
    none.unmount();

    const held = render(<Harness initial={[secured]} assets={[car]} />);
    expect(screen.queryByText(copy.SECURING_PROPERTY_NONE)).not.toBeInTheDocument();
    held.unmount();

    render(<Harness initial={[{ ...secured, is_secured: false }]} assets={[]} />);
    expect(screen.queryByText(copy.SECURING_PROPERTY_NONE)).not.toBeInTheDocument();
  });

  it('clears the offset answer when the filer answers Yes to secured', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<Harness initial={[{ ...complete, offset_answer: 'no' }]} onChange={onChange} />);
    await user.click(box('is_secured_0', 'yes'));
    expect(lastRows(onChange)[0]).toMatchObject({ is_secured: true, offset_answer: null });
  });

  it('drops who answers for the old property when another property is picked', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    const piano: WizardRow<AssetInfo> = { _key: '39', id: 4, ab_line: '39', details: {} };
    render(
      <Harness
        initial={[
          {
            ...secured,
            secured_by: 4,
            home_payment_line: 'first',
            collateral_who: 'with_someone',
          },
        ]}
        assets={[car, piano]}
        onChange={onChange}
      />
    );
    await user.selectOptions(field('secured_by_0'), '3');
    expect(lastRows(onChange)[0]).toMatchObject({
      secured_by: 3,
      home_payment_line: null,
      collateral_who: null,
    });
  });

  it('asks the notice question with nothing checked, opens a party under Yes, and shuts at 10', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<Harness initial={[{ ...complete, notice_parties: null }]} onChange={onChange} />);
    expect(all('[name="notice_0"]:checked')).toHaveLength(0);

    await user.click(box('notice_0', 'yes'));
    expect(lastRows(onChange)[0].notice_parties).toHaveLength(1);
    for (const name of [
      'notice_0_0_name',
      'notice_0_0_street_address',
      'notice_0_0_city',
      'notice_0_0_last_4',
    ]) {
      expect(field(name)).not.toBeNull();
    }

    const add = screen.getByRole('button', { name: copy.ADD_ANOTHER_PARTY });
    for (let i = 0; i < 9; i++) await user.click(add);
    expect(lastRows(onChange)[0].notice_parties).toHaveLength(10);
    expect(add).toBeDisabled();
  });

  it('has no axe violations', { timeout: 60_000 }, async () => {
    const row: DebtRow = {
      ...secured,
      lien: { kinds: ['agreement', 'other'], other: 'Demo lien' },
      notice_parties: [
        {
          name: 'Demo Collections',
          street_address: '1 Demo Way',
          street_2: '',
          city: 'Demo City',
          state: '',
          zip_code: '',
          outside_us: true,
          last_4: '',
        },
      ],
    };
    const { container } = render(<Harness initial={[row]} assets={[car]} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe('DebtsStep legacy payments', () => {
  const vehicleGap = { field: 'vehicle_payment' as const, sentence: 'You pay $350 for a car.' };
  const otherGap = {
    field: 'other_property_mortgages' as const,
    sentence: 'You pay $600 on other property.',
  };

  it('shows a legacy sentence with Remove, and Continue stays as the rows decide', () => {
    const complete_ = vi.fn();
    const { unmount } = render(
      <Harness initial={[complete]} legacyGaps={[vehicleGap]} onValidity={complete_} />
    );

    const sentence = screen.getByText(vehicleGap.sentence);
    expect(screen.getByRole('button', { name: copy.LEGACY_REMOVE })).toBeInTheDocument();
    expect(lastValidity(complete_)).toBe(true);
    expect(status()).not.toContainElement(sentence);
    unmount();

    const incomplete = vi.fn();
    render(
      <Harness
        initial={[{ ...complete, street_address: '' }]}
        legacyGaps={[vehicleGap]}
        onValidity={incomplete}
      />
    );

    expect(screen.getByText(vehicleGap.sentence)).toBeInTheDocument();
    expect(lastValidity(incomplete)).toBe(false);
    expect(status()).not.toContainElement(screen.getByText(vehicleGap.sentence));
  });

  it('each Remove calls back with its own field', async () => {
    const onRemoveLegacy = vi.fn().mockResolvedValue(undefined);
    render(
      <Harness
        initial={[complete]}
        legacyGaps={[vehicleGap, otherGap]}
        onRemoveLegacy={onRemoveLegacy}
      />
    );

    const buttons = screen.getAllByRole('button', { name: copy.LEGACY_REMOVE });
    expect(buttons).toHaveLength(2);
    await userEvent.click(
      within(screen.getByText(otherGap.sentence).parentElement!).getByRole('button')
    );

    expect(onRemoveLegacy).toHaveBeenCalledTimes(1);
    expect(onRemoveLegacy).toHaveBeenCalledWith('other_property_mortgages');
    expect(buttons[0]).toHaveAttribute('aria-describedby', 'legacy-vehicle_payment');
    expect(buttons[1]).toHaveAttribute('aria-describedby', 'legacy-other_property_mortgages');
    expect(screen.getByText(vehicleGap.sentence)).toHaveAttribute('id', 'legacy-vehicle_payment');
  });

  it('says a Remove that failed was not saved, and keeps the sentence', async () => {
    const onRemoveLegacy = vi.fn().mockRejectedValue(new Error('no'));
    render(
      <Harness initial={[complete]} legacyGaps={[vehicleGap]} onRemoveLegacy={onRemoveLegacy} />
    );

    await userEvent.click(screen.getByRole('button', { name: copy.LEGACY_REMOVE }));

    expect(await screen.findByRole('alert')).toHaveTextContent(copy.NOT_SAVED_TRY_AGAIN);
    expect(screen.getByText(vehicleGap.sentence)).toBeInTheDocument();
  });

  it("keeps a failed Remove per box: another box's Remove leaves it in place", async () => {
    const onRemoveLegacy = vi.fn((field: LegacyField) =>
      field === 'vehicle_payment' ? Promise.reject(new Error('no')) : Promise.resolve()
    );
    render(
      <Harness
        initial={[complete]}
        legacyGaps={[vehicleGap, otherGap]}
        onRemoveLegacy={onRemoveLegacy}
      />
    );
    const boxOf = (gap: { sentence: string }) => screen.getByText(gap.sentence).parentElement!;

    await userEvent.click(within(boxOf(vehicleGap)).getByRole('button'));
    expect(await within(boxOf(vehicleGap)).findByRole('alert')).toHaveTextContent(
      copy.NOT_SAVED_TRY_AGAIN
    );
    expect(within(boxOf(otherGap)).queryByRole('alert')).toBeNull();

    await userEvent.click(within(boxOf(otherGap)).getByRole('button'));
    expect(onRemoveLegacy).toHaveBeenCalledWith('other_property_mortgages');
    expect(within(boxOf(vehicleGap)).getByRole('alert')).toHaveTextContent(
      copy.NOT_SAVED_TRY_AGAIN
    );
  });

  it("drops a failed Remove's alert when the sentence changes", async () => {
    const onRemoveLegacy = vi.fn().mockRejectedValue(new Error('no'));
    const { rerender } = render(
      <Harness initial={[complete]} legacyGaps={[vehicleGap]} onRemoveLegacy={onRemoveLegacy} />
    );
    await userEvent.click(screen.getByRole('button', { name: copy.LEGACY_REMOVE }));
    expect(await screen.findByRole('alert')).toBeInTheDocument();

    const changed = { ...vehicleGap, sentence: 'You pay $200 for a car.' };
    rerender(
      <Harness initial={[complete]} legacyGaps={[changed]} onRemoveLegacy={onRemoveLegacy} />
    );

    expect(screen.getByText(changed.sentence)).toBeInTheDocument();
    expect(screen.queryByRole('alert')).toBeNull();
  });
});

describe('DebtsStep intro', () => {
  it('the intro says what to list and nothing about which bankruptcy fits', () => {
    render(<Harness />);

    expect(
      screen.getByText(/List all creditors \(companies or people you owe money to\)/)
    ).toBeInTheDocument();
    expect(screen.queryByText(/which type of bankruptcy/i)).toBeNull();
  });
});
