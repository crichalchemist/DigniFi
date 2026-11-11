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
  GO_TO_STEP_FOR_ROW,
  NOT_ANSWERED_YET,
  OLD_ASSET_TYPE_WORDS,
  OLD_ROWS_HEADING,
  ONE_ITEM,
  PRIORITY_NO,
  PRIORITY_NOT_SURE,
  REVIEW_ASSET_PART,
  REVIEW_ASSET_ROW,
  REVIEW_ASSISTANCE,
  REVIEW_DEDUCTIONS,
  REVIEW_ENTRIES,
  REVIEW_HOUSEHOLD_COUNT,
  REVIEW_LINE_3,
  REVIEW_LINKED_PAYMENTS,
  REVIEW_MONTHLY_TOTAL,
  REVIEW_NO_CODEBTORS,
  REVIEW_NO_CONTRACTS,
  REVIEW_NO_DEBTS,
  REVIEW_NO_ENTRIES,
  REVIEW_NOW_DIFFERENT,
  REVIEW_PAST_DUE,
  REVIEW_RENT_OR_LOT_RENT,
  REVIEW_SPOUSE_ASSISTANCE,
  REVIEW_SPOUSE_DEDUCTIONS,
  REVIEW_SPOUSE_ENTRIES,
  REVIEW_SPOUSE_NOW_DIFFERENT,
  REVIEW_TYPED_TOTAL,
  REVIEW_UNNAMED_CODEBTOR,
  REVIEW_UNNAMED_CONTRACT,
  REVIEW_VALUE_NOT_KNOWN,
  REVIEW_YES_NO,
  VALUE_UNKNOWN_HEADING,
} from '../../../constants/copy';
import {
  CODEBTOR_RELATIONSHIP_WORDS,
  CONTRACT_TYPE_WORDS,
  DEBT_TYPE_WORDS,
} from '../../../constants/claims';
import { linkedSums } from './claims/linkedPayments';
import { WIZARD_STEPS } from '../../../constants/wizardSteps';
import { AB_PARTS, ASSET_LINES } from '../../../constants/assetLines';
import { deductionsTotal, takeHomePayNotEntered } from '../../../utils/takeHomePay';
import {
  AB_LINE_WORDS,
  AB_PART_TITLES,
  MARRIAGE_ANSWER_WORDS,
  MARRIED_NOT_FILING,
  NONPRIORITY_AMOUNT_LABEL,
  PRIORITY_AMOUNT_LABEL,
  PRIORITY_TYPE_WORDS,
} from '../../../constants/formText';
import type {
  DebtorInfo,
  IncomeInfo,
  ExpenseInfo,
  AssetInfo,
  DebtInfo,
  ExecutoryContract,
  ClaimAnswers,
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
  /** What the filer pressed on the claim steps, so an empty list says so */
  claimAnswers?: ClaimAnswers;
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
  claimAnswers = {},
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

  // The typed total never holds a linked payment; Review adds them in cents (3c4 R8)
  const linkedTotal = linkedSums(debtsData, contractsData, assetsData).allLinked;
  const monthlyTotal =
    (Math.round((expenseData.total_monthly_expenses || 0) * 100) + Math.round(linkedTotal * 100)) /
    100;

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

  // A row by what the filer typed, then its line's words: a line 16 row or a place has no description
  const assetLabel = (asset: Partial<AssetInfo>) => {
    const key = asset.ab_line as string;
    const name =
      asset.description?.trim() ||
      asset.details?.street?.trim() ||
      asset.details?.make?.trim() ||
      AB_LINE_WORDS[key].words;
    // A function, since a string replacement would read a $ the filer typed as a pattern
    return REVIEW_ASSET_ROW.replace('{key}', key).replace('{name}', () => name);
  };

  // A value the filer doesn't know is an answer and no $0, and a typed $0 is one too
  const assetValue = (asset: Partial<AssetInfo>) => {
    if (asset.current_value !== null && asset.current_value !== undefined) {
      return formatCurrency(asset.current_value);
    }
    return asset.details?.value_unknown ? REVIEW_VALUE_NOT_KNOWN : NOT_ANSWERED_YET;
  };

  const oldAssets = assetsData.filter(
    (asset) => asset.ab_line === null || asset.ab_line === undefined
  );
  // ordered_assets's order, as the form prints them: the catalog, then id, with a row not saved yet
  // last, where the id it gets will put it
  const assetsOnLines = ASSET_LINES.flatMap((line) =>
    assetsData
      .filter((asset) => asset.ab_line === line.key)
      .sort((a, b) => (a.id ?? Infinity) - (b.id ?? Infinity))
  );
  const assetParts = AB_PARTS.map((part) => ({
    part,
    rows: assetsOnLines.filter(
      (asset) => ASSET_LINES.find((line) => line.key === asset.ab_line)?.part === part
    ),
  })).filter(({ rows }) => rows.length > 0);
  const unknownAssets = assetsOnLines.filter(
    (asset) => asset.details?.value_unknown || asset.details?.entire_unknown
  );
  const assetsStep = WIZARD_STEPS.find((step) => step.key === 'assets');

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
            <span className="review-field-label">{REVIEW_RENT_OR_LOT_RENT}</span>
            <span className="review-field-value">
              {formatCurrency(expenseData.rent_or_mortgage)}
            </span>
          </div>
          <div className="review-field">
            <span className="review-field-label">{REVIEW_TYPED_TOTAL}</span>
            <span className="review-field-value">
              {formatCurrency(expenseData.total_monthly_expenses)}
            </span>
          </div>
          <div className="review-field">
            <span className="review-field-label">{REVIEW_LINKED_PAYMENTS}</span>
            <span className="review-field-value">{formatCurrency(linkedTotal)}</span>
          </div>
          <div className="review-field">
            <span className="review-field-label">{REVIEW_MONTHLY_TOTAL}</span>
            <span className="review-field-value">{formatCurrency(monthlyTotal)}</span>
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
          <>
            {oldAssets.length > 0 && (
              <>
                <h5 className="ab-subheading">{OLD_ROWS_HEADING}</h5>
                <ul className="review-list">
                  {oldAssets.map((asset, index) => (
                    <li key={asset.id ?? index} className="review-list-item">
                      <span>
                        {asset.description?.trim() || ONE_ITEM}
                        {asset.asset_type && OLD_ASSET_TYPE_WORDS[asset.asset_type]
                          ? ` (${OLD_ASSET_TYPE_WORDS[asset.asset_type]})`
                          : ''}
                      </span>
                      <span className="review-field-value">{assetValue(asset)}</span>
                    </li>
                  ))}
                </ul>
              </>
            )}
            {assetParts.map(({ part, rows }) => (
              <div key={part}>
                <h5 className="ab-subheading">
                  {REVIEW_ASSET_PART.replace('{n}', String(part)).replace(
                    '{title}',
                    AB_PART_TITLES[part]
                  )}
                </h5>
                <ul className="review-list">
                  {rows.map((asset, index) => (
                    <li key={asset.id ?? index} className="review-list-item">
                      <span>{assetLabel(asset)}</span>
                      <span className="review-field-value">{assetValue(asset)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
            {unknownAssets.length > 0 && (
              <>
                <h5 className="ab-subheading">{VALUE_UNKNOWN_HEADING}</h5>
                <ul className="review-list">
                  {unknownAssets.map((asset, index) => (
                    <li key={asset.id ?? index} className="review-list-item">
                      <span>{assetLabel(asset)}</span>
                      {assetsStep && (
                        <Button
                          variant="outline"
                          size="sm"
                          aria-label={GO_TO_STEP_FOR_ROW.replace(
                            '{step}',
                            assetsStep.label
                          ).replace('{row}', () => assetLabel(asset))}
                          onClick={() => onGoToStep?.(assetsStep.number)}
                        >
                          Go to {assetsStep.label}
                        </Button>
                      )}
                    </li>
                  ))}
                </ul>
              </>
            )}
          </>
        )}
      </section>

      {/* Debts Summary */}
      <section className="review-section">
        <h4 className="review-section-title">Amounts Owed ({debtsData.length})</h4>
        {debtsData.length === 0 ? (
          <p className="review-empty">
            {claimAnswers.no_debts === true ? REVIEW_NO_DEBTS : 'No amounts owed listed.'}
          </p>
        ) : (
          <ul className="review-list">
            {debtsData.map((debt, index) => (
              <li key={debt.id || index} className="review-list-item">
                <span>
                  {debt.creditor_name || 'Unnamed Creditor'}
                  {debt.debt_type && DEBT_TYPE_WORDS[debt.debt_type]
                    ? ` (${DEBT_TYPE_WORDS[debt.debt_type]})`
                    : ''}
                  {debt.priority_answer && (
                    <span style={{ display: 'block' }}>
                      {debt.priority_answer === 'no'
                        ? PRIORITY_NO
                        : debt.priority_answer === 'not_sure'
                          ? PRIORITY_NOT_SURE
                          : PRIORITY_TYPE_WORDS[debt.priority_answer]}
                    </span>
                  )}
                  {(
                    [
                      [PRIORITY_AMOUNT_LABEL, debt.priority_amount],
                      [NONPRIORITY_AMOUNT_LABEL, debt.nonpriority_amount],
                      [REVIEW_PAST_DUE, debt.past_due_amount],
                    ] as const
                  ).map(([label, figure]) =>
                    figure === null || figure === undefined ? null : (
                      <span key={label} style={{ display: 'block' }}>
                        {label}: {formatCurrency(figure)}
                      </span>
                    )
                  )}
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
          <p className="review-empty">
            {claimAnswers.contracts_answer === 'no'
              ? REVIEW_NO_CONTRACTS
              : 'No contracts or leases listed.'}
          </p>
        ) : (
          <ul className="review-list">
            {contractsData.map((contract, index) => (
              <li key={contract.id || index} className="review-list-item">
                <span>
                  {contract.counterparty_name || REVIEW_UNNAMED_CONTRACT}
                  {contract.contract_type && CONTRACT_TYPE_WORDS[contract.contract_type]
                    ? ` (${CONTRACT_TYPE_WORDS[contract.contract_type]})`
                    : ''}
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
          <p className="review-empty">
            {claimAnswers.codebtors_answer === 'no' ? REVIEW_NO_CODEBTORS : 'No codebtors listed.'}
          </p>
        ) : (
          <ul className="review-list">
            {codebtorsData.map((codebtor, index) => (
              <li key={codebtor.id || index} className="review-list-item">
                <span>
                  {codebtor.name || REVIEW_UNNAMED_CODEBTOR}
                  {codebtor.relationship && CODEBTOR_RELATIONSHIP_WORDS[codebtor.relationship]
                    ? ` (${CODEBTOR_RELATIONSHIP_WORDS[codebtor.relationship]})`
                    : ''}
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
