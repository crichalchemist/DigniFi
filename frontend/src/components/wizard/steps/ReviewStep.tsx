/**
 * Review Step - Summary of all entered information
 *
 * Allows users to review and edit their information before
 * submitting for means test calculation.
 */

import { useEffect } from 'react';
import { Button } from '../../common';
import { UPLDisclaimer } from '../../compliance';
import { UPL_REVIEW_DISCLAIMER } from '../../../constants/upl';
import {
  NOT_ANSWERED_YET,
  REVIEW_ASSISTANCE,
  REVIEW_DEDUCTIONS,
  REVIEW_ENTRIES,
  REVIEW_HOUSEHOLD_COUNT,
  REVIEW_LINE_3,
  REVIEW_NO_ENTRIES,
  REVIEW_NOW_DIFFERENT,
  REVIEW_SPOUSE_ASSISTANCE,
  REVIEW_SPOUSE_DEDUCTIONS,
  REVIEW_SPOUSE_ENTRIES,
  REVIEW_SPOUSE_NOW_DIFFERENT,
  REVIEW_YES_NO,
} from '../../../constants/copy';
import { WIZARD_STEPS } from '../../../constants/wizardSteps';
import { deductionsTotal, takeHomePayNotEntered } from '../../../utils/takeHomePay';
import { MARRIAGE_ANSWER_WORDS, MARRIED_NOT_FILING } from '../../../constants/formText';
import type {
  DebtorInfo,
  IncomeInfo,
  ExpenseInfo,
  AssetInfo,
  DebtInfo,
  ExecutoryContract,
  Codebtor,
  IncomeEntry,
  SpouseIncome,
  YesNo,
} from '../../../types/api';

interface ReviewStepProps {
  debtorData: Partial<DebtorInfo>;
  incomeData: Partial<IncomeInfo>;
  spouseIncomeData: SpouseIncome;
  /** The business and rental list as the Income step sends it: null while unanswered */
  entries: IncomeEntry[] | null;
  /** The spouse's list, the same way */
  spouseEntries: IncomeEntry[] | null;
  expenseData: Partial<ExpenseInfo>;
  assetsData: Partial<AssetInfo>[];
  debtsData: Partial<DebtInfo>[];
  contractsData: ExecutoryContract[];
  codebtorsData: Codebtor[];
  /** Form 122A-1 line 13's count, or null while the server can't work it out */
  householdCount: number | null;
  county: string | null;
  onValidationChange: (isValid: boolean) => void;
  /** Each thing Complete found missing, with the wizard step that fixes it when there is one */
  completionReasons?: { message: string; step?: { number: number; label: string } }[];
  /** Moves to a wizard step, the way Go Back does */
  onGoToStep?: (stepNumber: number) => void;
}

export function ReviewStep({
  debtorData,
  incomeData,
  spouseIncomeData,
  entries,
  spouseEntries,
  expenseData,
  assetsData,
  debtsData,
  contractsData,
  codebtorsData,
  householdCount,
  county,
  onValidationChange,
  completionReasons = [],
  onGoToStep,
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

  const marriage = incomeData.marital_status
    ? incomeData.marital_status === 'not_married' ||
      incomeData.marital_status === 'married_spouse_filing'
      ? MARRIAGE_ANSWER_WORDS[incomeData.marital_status]
      : `${MARRIED_NOT_FILING} ${MARRIAGE_ANSWER_WORDS[incomeData.marital_status]}`
    : NOT_ANSWERED_YET;

  const spouseAtHome = incomeData.marital_status === 'married_together';

  const yesNo = (answer?: YesNo | null) => (answer ? REVIEW_YES_NO[answer] : NOT_ANSWERED_YET);

  const entriesText = (list: IncomeEntry[] | null) => {
    if (list === null) return NOT_ANSWERED_YET;
    if (list.length === 0) return REVIEW_NO_ENTRIES;
    return list.map((entry) => entry.description?.trim() || NOT_ANSWERED_YET).join('; ');
  };

  const deductionsText = (data: Partial<IncomeInfo> | SpouseIncome) =>
    takeHomePayNotEntered(data) ? NOT_ANSWERED_YET : formatCurrency(deductionsTotal(data));

  const takeHomePayLabel = WIZARD_STEPS.find((step) => step.key === 'take_home_pay')?.label;

  return (
    <div className="review-step">
      {/* Below the wizard's alert, which keeps Complete's general message (step 3a1 spec §4.4).
          A polite live region from the start, so a screen reader reads out the reasons a
          refused Complete adds to it. */}
      <div className="review-reasons" aria-live="polite">
        {completionReasons.length > 0 && (
          <section className="review-section">
            <ul className="review-list">
              {completionReasons.map(({ message, step }, index) => (
                <li key={index} className="review-list-item">
                  <span>{message}</span>
                  {step && (
                    <Button variant="outline" size="sm" onClick={() => onGoToStep?.(step.number)}>
                      Go to {step.label}
                    </Button>
                  )}
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>

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

      {/* Household Summary */}
      <section className="review-section">
        <h4 className="review-section-title">Your household</h4>
        <div className="review-grid">
          <div className="review-field">
            <span className="review-field-label">County</span>
            <span className="review-field-value">{county ?? NOT_ANSWERED_YET}</span>
          </div>
          <div className="review-field">
            <span className="review-field-label">Your marriage</span>
            <span className="review-field-value">{marriage}</span>
          </div>
          <div className="review-field">
            <span className="review-field-label">{REVIEW_HOUSEHOLD_COUNT}</span>
            <span className="review-field-value">{householdCount ?? NOT_ANSWERED_YET}</span>
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
          <div className="review-field">
            <span className="review-field-label">{REVIEW_ENTRIES}</span>
            <span className="review-field-value">{entriesText(entries)}</span>
          </div>
          <div className="review-field">
            <span className="review-field-label">{REVIEW_NOW_DIFFERENT}</span>
            <span className="review-field-value">{yesNo(incomeData.income_now_different)}</span>
          </div>
          <div className="review-field">
            <span className="review-field-label">{REVIEW_ASSISTANCE}</span>
            <span className="review-field-value">{yesNo(incomeData.assistance_answer)}</span>
          </div>
          {spouseAtHome && (
            <>
              <div className="review-field">
                <span className="review-field-label">{REVIEW_SPOUSE_ENTRIES}</span>
                <span className="review-field-value">{entriesText(spouseEntries)}</span>
              </div>
              <div className="review-field">
                <span className="review-field-label">{REVIEW_SPOUSE_NOW_DIFFERENT}</span>
                <span className="review-field-value">
                  {yesNo(spouseIncomeData.income_now_different)}
                </span>
              </div>
              <div className="review-field">
                <span className="review-field-label">{REVIEW_SPOUSE_ASSISTANCE}</span>
                <span className="review-field-value">
                  {yesNo(spouseIncomeData.assistance_answer)}
                </span>
              </div>
            </>
          )}
        </div>
      </section>

      {/* Take-home pay Summary */}
      <section className="review-section">
        <h4 className="review-section-title">{takeHomePayLabel}</h4>
        <div className="review-grid">
          <div className="review-field">
            <span className="review-field-label">{REVIEW_DEDUCTIONS}</span>
            <span className="review-field-value">{deductionsText(incomeData)}</span>
          </div>
          {spouseAtHome && (
            <div className="review-field">
              <span className="review-field-label">{REVIEW_SPOUSE_DEDUCTIONS}</span>
              <span className="review-field-value">{deductionsText(spouseIncomeData)}</span>
            </div>
          )}
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
          <div className="review-field">
            <span className="review-field-label">{REVIEW_LINE_3}</span>
            <span className="review-field-value">{yesNo(expenseData.expenses_include_others)}</span>
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
