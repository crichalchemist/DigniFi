/**
 * Review Step - Summary of all entered information
 *
 * Allows users to review and edit their information before
 * submitting for means test calculation.
 */

import { useEffect } from 'react';
import { UPLDisclaimer } from '../../compliance';
import { UPL_REVIEW_DISCLAIMER } from '../../../constants/upl';
import type {
  DebtorInfo,
  IncomeInfo,
  ExpenseInfo,
  AssetInfo,
  DebtInfo,
  ExecutoryContract,
  Codebtor,
} from '../../../types/api';

interface ReviewStepProps {
  debtorData: Partial<DebtorInfo>;
  incomeData: Partial<IncomeInfo>;
  expenseData: Partial<ExpenseInfo>;
  assetsData: Partial<AssetInfo>[];
  debtsData: Partial<DebtInfo>[];
  contractsData: ExecutoryContract[];
  codebtorsData: Codebtor[];
  onValidationChange: (isValid: boolean) => void;
}

export function ReviewStep({
  debtorData,
  incomeData,
  expenseData,
  assetsData,
  debtsData,
  contractsData,
  codebtorsData,
  onValidationChange,
}: ReviewStepProps) {
  // Always valid to proceed from review (unless we add specific checks)
  useEffect(() => {
    onValidationChange(true);
  }, [onValidationChange]);

  const formatCurrency = (amount?: number | null) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount || 0);
  };

  const fullName =
    [debtorData.first_name, debtorData.middle_name, debtorData.last_name]
      .filter(Boolean)
      .join(' ') || '—';

  return (
    <div className="review-step">
      <div className="info-box">
        <h3 className="info-title">Review Your Information</h3>
        <p className="info-message">
          Please review the information below carefully. This information will be used to calculate
          your eligibility.
        </p>
      </div>

      {/* Debtor Info Summary */}
      <section className="review-section">
        <h4 className="review-section-title">Personal Information</h4>
        <div className="review-grid">
          <div className="review-field">
            <span className="review-field-label">Name</span>
            <span className="review-field-value">{fullName}</span>
          </div>
          <div className="review-field">
            <span className="review-field-label">SSN</span>
            <span className="review-field-value">***-**-{debtorData.ssn?.slice(-4) || '****'}</span>
          </div>
        </div>
      </section>

      {/* Income Summary */}
      <section className="review-section">
        <h4 className="review-section-title">Income</h4>
        <div className="review-grid">
          <div className="review-field">
            <span className="review-field-label">Total Monthly Income</span>
            <span className="review-field-value">
              {formatCurrency(incomeData.total_monthly_income)}
            </span>
          </div>
        </div>
      </section>

      {/* Expenses Summary */}
      <section className="review-section">
        <h4 className="review-section-title">Monthly Expenses</h4>
        <div className="review-grid">
          <div className="review-field">
            <span className="review-field-label">Rent / Mortgage</span>
            <span className="review-field-value">
              {formatCurrency(expenseData.rent_or_mortgage)}
            </span>
          </div>
          <div className="review-field">
            <span className="review-field-label">Total Expenses</span>
            <span className="review-field-value">
              {formatCurrency(expenseData.total_monthly_expenses)}
            </span>
          </div>
        </div>
      </section>

      {/* Assets Summary */}
      <section className="review-section">
        <h4 className="review-section-title">Assets ({assetsData.length})</h4>
        {assetsData.length === 0 ? (
          <p className="review-empty">No assets listed.</p>
        ) : (
          <ul className="review-list">
            {assetsData.map((asset, index) => (
              <li key={asset.id || index} className="review-list-item">
                <span>
                  {asset.description || 'Unnamed Asset'}
                  {asset.asset_type ? ` (${asset.asset_type.replace('_', ' ')})` : ''}
                </span>
                <span className="review-field-value">{formatCurrency(asset.current_value)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Debts Summary */}
      <section className="review-section">
        <h4 className="review-section-title">Amounts Owed ({debtsData.length})</h4>
        {debtsData.length === 0 ? (
          <p className="review-empty">No amounts owed listed.</p>
        ) : (
          <ul className="review-list">
            {debtsData.map((debt, index) => (
              <li key={debt.id || index} className="review-list-item">
                <span>
                  {debt.creditor_name || 'Unnamed Creditor'}
                  {debt.debt_type ? ` (${debt.debt_type})` : ''}
                </span>
                <span className="review-field-value">{formatCurrency(debt.amount_owed)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Contracts Summary */}
      <section className="review-section">
        <h4 className="review-section-title">Contracts & Leases ({contractsData.length})</h4>
        {contractsData.length === 0 ? (
          <p className="review-empty">No contracts or leases listed.</p>
        ) : (
          <ul className="review-list">
            {contractsData.map((contract, index) => (
              <li key={contract.id || index} className="review-list-item">
                <span>
                  {contract.counterparty_name} ({contract.contract_type})
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Codebtors Summary */}
      <section className="review-section">
        <h4 className="review-section-title">Codebtors ({codebtorsData.length})</h4>
        {codebtorsData.length === 0 ? (
          <p className="review-empty">No codebtors listed.</p>
        ) : (
          <ul className="review-list">
            {codebtorsData.map((codebtor, index) => (
              <li key={codebtor.id || index} className="review-list-item">
                <span>
                  {codebtor.name} ({codebtor.relationship.replace('_', ' ')})
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <UPLDisclaimer text={UPL_REVIEW_DISCLAIMER} variant="banner" />
    </div>
  );
}
