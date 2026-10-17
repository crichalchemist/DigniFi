import { useState } from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DebtsStep } from '../DebtsStep';
import type { DebtInfo, WizardRow } from '../../../../types/api';

// DebtsStep validates and renders the wizard's debt rows.
// These tests focus on the draft-badge feature: when is_draft is true on a
// debt, the component must render a visible "From scan" badge so users know
// the entry was pre-filled by document scanning rather than entered manually.

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

describe('DebtsStep draft badge', () => {
  it('renders "From scan" badge when is_draft is true', () => {
    const draftDebt: WizardRow<DebtInfo> = { ...baseDebt, is_draft: true };

    render(<DebtsStep rows={[draftDebt]} onRowsChange={noop} onValidationChange={noop} />);

    expect(screen.getByText('From scan')).toBeInTheDocument();
  });

  it('does not render a badge when is_draft is false', () => {
    const manualDebt: WizardRow<DebtInfo> = { ...baseDebt, is_draft: false };

    render(<DebtsStep rows={[manualDebt]} onRowsChange={noop} onValidationChange={noop} />);

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

    render(<DebtsStep rows={[debtWithoutDraft]} onRowsChange={noop} onValidationChange={noop} />);

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
      <DebtsStep rows={[manualDebt, draftDebt]} onRowsChange={noop} onValidationChange={noop} />
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

    render(<DebtsStep rows={[draftA, draftB]} onRowsChange={noop} onValidationChange={noop} />);

    expect(screen.getAllByText('From scan')).toHaveLength(2);
  });

  it('badge has the correct aria-label for screen reader users', () => {
    const draftDebt: WizardRow<DebtInfo> = { ...baseDebt, is_draft: true };

    render(<DebtsStep rows={[draftDebt]} onRowsChange={noop} onValidationChange={noop} />);

    expect(
      screen.getByRole('generic', { name: /pre-filled from document scan/i })
    ).toBeInTheDocument();
  });
});

// Schedule D lists a secured amount owed with what secures it, and the server reads both
// under these names: a renamed key is dropped without an error (DIG-26)
describe('DebtsStep secured amounts owed', () => {
  /** The wizard's part: it holds the rows the step shows */
  function StepWithRows({ onRowsChange }: { onRowsChange: (rows: WizardRow<DebtInfo>[]) => void }) {
    const [rows, setRows] = useState<WizardRow<DebtInfo>[]>([]);
    return (
      <DebtsStep
        rows={rows}
        onRowsChange={(next) => {
          setRows(next);
          onRowsChange(next);
        }}
        onValidationChange={noop}
      />
    );
  }

  it('marks a car loan secured and keeps what secures it, under the names the server stores', async () => {
    const onRowsChange = vi.fn();
    render(<StepWithRows onRowsChange={onRowsChange} />);
    const user = userEvent.setup();

    await user.selectOptions(
      screen.getByLabelText(/what kind of amount owed is this/i),
      'Car or vehicle loan'
    );
    await user.type(screen.getByLabelText(/what secures this amount owed/i), '2015 Honda Civic');

    expect(onRowsChange).toHaveBeenLastCalledWith([
      expect.objectContaining({
        debt_type: 'auto_loan',
        is_secured: true,
        collateral_description: '2015 Honda Civic',
      }),
    ]);
  });
});
