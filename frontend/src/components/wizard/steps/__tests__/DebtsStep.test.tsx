import { render, screen } from '@testing-library/react';
import { DebtsStep } from '../DebtsStep';
import type { DebtInfo } from '../../../../types/api';

// DebtsStep validates and renders debts passed via initialData.
// These tests focus on the draft-badge feature: when is_draft is true on a
// debt, the component must render a visible "From scan" badge so users know
// the entry was pre-filled by document scanning rather than entered manually.

const baseDebt: Partial<DebtInfo> = {
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
    const draftDebt: Partial<DebtInfo> = { ...baseDebt, is_draft: true };

    render(<DebtsStep initialData={[draftDebt]} onDataChange={noop} onValidationChange={noop} />);

    expect(screen.getByText('From scan')).toBeInTheDocument();
  });

  it('does not render a badge when is_draft is false', () => {
    const manualDebt: Partial<DebtInfo> = { ...baseDebt, is_draft: false };

    render(<DebtsStep initialData={[manualDebt]} onDataChange={noop} onValidationChange={noop} />);

    expect(screen.queryByText('From scan')).not.toBeInTheDocument();
  });

  it('does not render a badge when is_draft is absent', () => {
    // Omit is_draft entirely to verify the badge is absent when the field is missing
    const debtWithoutDraft: Partial<DebtInfo> = {
      id: baseDebt.id,
      session: baseDebt.session,
      debt_type: baseDebt.debt_type,
      creditor_name: baseDebt.creditor_name,
      amount_owed: baseDebt.amount_owed,
      monthly_payment: baseDebt.monthly_payment,
      is_secured: baseDebt.is_secured,
    };

    render(
      <DebtsStep initialData={[debtWithoutDraft]} onDataChange={noop} onValidationChange={noop} />
    );

    expect(screen.queryByText('From scan')).not.toBeInTheDocument();
  });

  it('renders badge on each draft debt in a mixed list', () => {
    const manualDebt: Partial<DebtInfo> = {
      ...baseDebt,
      id: 2,
      creditor_name: 'Manual Citi',
      is_draft: false,
    };
    const draftDebt: Partial<DebtInfo> = {
      ...baseDebt,
      id: 3,
      creditor_name: 'Scanned Wells Fargo',
      is_draft: true,
    };

    render(
      <DebtsStep
        initialData={[manualDebt, draftDebt]}
        onDataChange={noop}
        onValidationChange={noop}
      />
    );

    // Only the draft entry gets a badge — the manual entry must not.
    expect(screen.getAllByText('From scan')).toHaveLength(1);
  });

  it('renders badges on all draft debts when multiple are present', () => {
    const draftA: Partial<DebtInfo> = {
      ...baseDebt,
      id: 10,
      creditor_name: 'Scanned Amex',
      is_draft: true,
    };
    const draftB: Partial<DebtInfo> = {
      ...baseDebt,
      id: 11,
      creditor_name: 'Scanned Discover',
      is_draft: true,
      source_document_name: 'credit_report.pdf',
    };

    render(
      <DebtsStep initialData={[draftA, draftB]} onDataChange={noop} onValidationChange={noop} />
    );

    expect(screen.getAllByText('From scan')).toHaveLength(2);
  });

  it('badge has the correct aria-label for screen reader users', () => {
    const draftDebt: Partial<DebtInfo> = { ...baseDebt, is_draft: true };

    render(<DebtsStep initialData={[draftDebt]} onDataChange={noop} onValidationChange={noop} />);

    expect(
      screen.getByRole('generic', { name: /pre-filled from document scan/i })
    ).toBeInTheDocument();
  });
});
