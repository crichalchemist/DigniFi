/**
 * Expense Info Step - Monthly expense collection
 *
 * Asks Schedule J line 3 and every expense line in the form's order and words.
 *
 * Trauma-informed design:
 * - Non-judgmental language about expenses
 * - Real-time total calculation
 * - Plain language help text
 */

import { useState, useEffect, useMemo } from 'react';
import { Button, FormField } from '../../common';
import { amountError, parseAmount } from '../../../utils/parseAmount';
import { fill } from './claims/claimNames';
import { formatFigure } from './claims/linkedPayments';
import type { ExpenseField, ExpenseInfo, ExpenseSpecifyField, YesNo } from '../../../types/api';
import { EXPENSE_FIELDS } from '../../../types/api';
import {
  EXPENSES_HEADING,
  EXPENSE_LINE_WORDS,
  EXPENSE_SPECIFY_WORDS,
  LINE_3_QUESTION,
  LINE_4_GROUP_HEADING,
  LINE_15_GROUP_HEADING,
  LINE_20_GROUP_HEADING,
  NONCASH_EXPENSES_SENTENCE,
} from '../../../constants/formText';
import {
  CLAIM_GAP_LINE_4,
  DOUBLE_COUNT_EXPENSES_NOTE,
  EXPENSES_LINKED_NOTE,
  EXPENSE_HELP_HOME_MAINTENANCE,
  EXPENSE_HELP_OTHER,
  LINE_3_INFO,
  LINE_4_CLEAR,
  LINE_4_HELP,
  LINE_4_PAY_BOTH,
  NOT_ANSWERED_YET,
  NOT_SAVED_TRY_AGAIN,
} from '../../../constants/copy';

interface ExpenseInfoStepProps {
  initialData?: Partial<ExpenseInfo>;
  onDataChange: (data: Partial<ExpenseInfo>) => void;
  onValidationChange: (isValid: boolean) => void;
  /** What Amounts Owed and Contracts & Leases link to a first mortgage a month (3c4) */
  linkedFirstMortgage?: number;
  /** The rent the filer confirmed beside that mortgage, as the server holds it; null if none */
  line4Confirmed?: string | null;
  /** Saves "I pay both"; rejects when the save fails */
  onLine4Confirm?: (figure: string) => Promise<void>;
}

const toCents = (amount: number) => Math.round(amount * 100);

// The help text under each line, for the lines that have any. The other lines are asked in the
// form's words alone.
const EXPENSE_HELP: Partial<Record<ExpenseField, string>> = {
  rent_or_mortgage: LINE_4_HELP,
  utilities: 'Electric, gas, water, trash, internet, phone',
  home_maintenance: EXPENSE_HELP_HOME_MAINTENANCE,
  vehicle_insurance: 'Monthly auto insurance premium',
  vehicle_maintenance: 'Gas, public transit, parking, tolls',
  food_and_groceries: 'Groceries, dining out, household supplies',
  childcare: 'Daycare, after-school care, babysitting',
  medical_expenses: 'Doctor visits, prescriptions, co-pays not covered by insurance',
  insurance_not_deducted: 'Health, life, or disability insurance you pay directly',
  clothing: 'Clothes, shoes, laundry, and dry cleaning',
  child_support_paid: 'Court-ordered support you pay to someone else',
  other_expenses: EXPENSE_HELP_OTHER,
};

export function ExpenseInfoStep({
  initialData,
  onDataChange,
  onValidationChange,
  linkedFirstMortgage = 0,
  line4Confirmed = null,
  onLine4Confirm,
}: ExpenseInfoStepProps) {
  // Fields start undefined (empty) rather than 0 so an untouched field reads
  // blank, while a deliberately entered 0 is preserved by parseAmount + `?? ''`.
  const [formData, setFormData] = useState<Partial<ExpenseInfo>>(initialData || {});

  // Calculate total monthly expenses
  const totalMonthlyExpenses = EXPENSE_FIELDS.reduce(
    (sum, field) => sum + (formData[field] || 0),
    0
  );

  const errors = useMemo<Record<string, string>>(() => {
    const newErrors: Record<string, string> = {};

    // No "at least one expense" gate: a blank or $0 expense is a valid answer
    // (the help text invites leaving categories blank or 0).

    // Each amount as the server stores it (amountError). Only the boxes: the total the step
    // last added up comes back in initialData, and no box shows it.
    for (const field of EXPENSE_FIELDS) {
      const message = amountError(formData[field] ?? undefined, 10);
      if (message) newErrors[field] = message;
    }

    return newErrors;
  }, [formData]);

  // Update parent when form data changes
  useEffect(() => {
    const dataWithTotal = {
      ...formData,
      total_monthly_expenses: totalMonthlyExpenses,
    };
    onDataChange(dataWithTotal);
    onValidationChange(Object.keys(errors).length === 0);
    // onDataChange/onValidationChange are fresh closures each render; including
    // them would loop. Matches the suppression on the sibling step effects.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [formData, totalMonthlyExpenses, errors]);

  const handleChange = (field: ExpenseField, value: string) => {
    if (field === 'rent_or_mortgage') setLine4Failed(false);
    setFormData((prev) => ({ ...prev, [field]: parseAmount(value) }));
  };

  // The Specify texts are kept as typed
  const handleTextChange = (field: ExpenseSpecifyField, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleLine3 = (answer: YesNo) => {
    setFormData((prev) => ({ ...prev, expenses_include_others: answer }));
  };

  // The line 4 question (R7): a typed rent beside a linked first mortgage, not yet confirmed as
  // the figure in the box. It is no gap: it never touches onValidationChange.
  const [line4Failed, setLine4Failed] = useState(false);
  const rent = formData.rent_or_mortgage ?? 0;
  const confirmedCents = line4Confirmed == null ? null : toCents(Number(line4Confirmed));
  const asksLine4 = rent > 0 && linkedFirstMortgage > 0 && confirmedCents !== toCents(rent);

  const payBoth = async () => {
    setLine4Failed(false);
    try {
      await onLine4Confirm?.(rent.toFixed(2));
    } catch {
      setLine4Failed(true);
    }
  };

  const clearRent = () => {
    setLine4Failed(false);
    setFormData((prev) => ({ ...prev, rent_or_mortgage: 0 }));
  };

  const line3Answer = formData.expenses_include_others;
  const line3NoteId = 'expenses_include_others-unanswered';
  const line3InfoId = 'expenses_include_others-info';

  const amountBox = (field: ExpenseField) => (
    <FormField
      key={field}
      label={EXPENSE_LINE_WORDS[field]}
      name={field}
      type="number"
      min="0"
      step="0.01"
      value={formData[field] ?? ''}
      onChange={(e) => handleChange(field, e.target.value)}
      error={errors[field]}
      helpText={EXPENSE_HELP[field]}
      placeholder="0.00"
    />
  );

  const specifyBox = (field: ExpenseSpecifyField) => (
    <FormField
      key={field}
      label={EXPENSE_SPECIFY_WORDS[field]}
      name={field}
      type="text"
      maxLength={100}
      value={formData[field] ?? ''}
      onChange={(e) => handleTextChange(field, e.target.value)}
    />
  );

  return (
    <div className="expense-info-step">
      {/* Explainer */}
      <div className="info-box">
        <svg className="info-icon" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
          <path
            fillRule="evenodd"
            d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
            clipRule="evenodd"
          />
        </svg>
        <div>
          <h3 className="info-title">Why we ask about expenses</h3>
          <p className="info-message">
            Monthly expenses help determine your financial situation. Enter your average monthly
            costs. If a category doesn't apply to you, you can leave it blank or enter $0.
          </p>
        </div>
      </div>

      {/* General error */}
      {errors.general && (
        <div className="form-error" role="alert">
          {errors.general}
        </div>
      )}

      {/* Schedule J line 3, in the form's words. Nothing is checked until the filer answers. */}
      <section className="form-section">
        <fieldset
          className="form-field fee-waiver-question"
          aria-describedby={line3Answer == null ? `${line3InfoId} ${line3NoteId}` : line3InfoId}
        >
          <legend className="form-label">{LINE_3_QUESTION}</legend>
          {(['no', 'yes'] as const).map((value) => (
            <label key={value} className="fee-waiver-checkbox">
              <input
                type="radio"
                name="expenses_include_others"
                value={value}
                checked={line3Answer === value}
                onChange={() => handleLine3(value)}
              />{' '}
              {value === 'yes' ? 'Yes' : 'No'}
            </label>
          ))}
          <p id={line3InfoId} className="form-help-text">
            {LINE_3_INFO}
          </p>
          {line3Answer == null && (
            <p id={line3NoteId} className="form-help-text">
              {NOT_ANSWERED_YET}
            </p>
          )}
        </fieldset>
        <p className="section-description">{DOUBLE_COUNT_EXPENSES_NOTE}</p>
      </section>

      {/* Lines 4 to 21, in Schedule J's order */}
      <section className="form-section">
        <h3 className="section-title">{EXPENSES_HEADING}</h3>
        <p className="section-description">{NONCASH_EXPENSES_SENTENCE}</p>

        {amountBox('rent_or_mortgage')}

        {asksLine4 && (
          <div className="form-field">
            <p className="form-help-text">
              {fill(CLAIM_GAP_LINE_4, {
                typed: formatFigure(rent),
                linked: formatFigure(linkedFirstMortgage),
              })}
            </p>
            <Button type="button" variant="outline" onClick={payBoth}>
              {LINE_4_PAY_BOTH}
            </Button>{' '}
            <Button type="button" variant="outline" onClick={clearRent}>
              {fill(LINE_4_CLEAR, { typed: formatFigure(rent) })}
            </Button>
            {line4Failed && (
              <p className="form-error" role="alert">
                {NOT_SAVED_TRY_AGAIN}
              </p>
            )}
          </div>
        )}

        <fieldset className="form-field">
          <legend className="form-label">{LINE_4_GROUP_HEADING}</legend>
          {amountBox('real_estate_taxes')}
          {amountBox('home_insurance')}
          {amountBox('home_maintenance')}
          {amountBox('hoa_dues')}
        </fieldset>

        {amountBox('utilities')}
        {amountBox('food_and_groceries')}
        {amountBox('childcare')}
        {amountBox('clothing')}
        {amountBox('personal_care')}
        {amountBox('medical_expenses')}
        {amountBox('vehicle_maintenance')}
        {amountBox('entertainment')}
        {amountBox('charitable_contributions')}

        <fieldset className="form-field">
          <legend className="form-label">{LINE_15_GROUP_HEADING}</legend>
          {amountBox('vehicle_insurance')}
          {amountBox('insurance_not_deducted')}
        </fieldset>

        {amountBox('taxes_not_deducted')}
        {specifyBox('taxes_specify')}
        {amountBox('child_support_paid')}
        {amountBox('support_others')}
        {specifyBox('support_others_specify')}

        <fieldset className="form-field">
          <legend className="form-label">{LINE_20_GROUP_HEADING}</legend>
          {amountBox('other_property_taxes')}
          {amountBox('other_property_insurance')}
          {amountBox('other_property_upkeep')}
          {amountBox('other_property_hoa_dues')}
        </fieldset>

        {amountBox('other_expenses')}
        {specifyBox('other_expenses_specify')}
      </section>

      {/* Total Summary */}
      <section className="form-section form-section--summary">
        <div className="expense-total">
          <h3 className="total-label">Total Monthly Expenses</h3>
          <p className="total-amount">
            $
            {totalMonthlyExpenses.toLocaleString('en-US', {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}
          </p>
          <p className="total-help-text">{EXPENSES_LINKED_NOTE}</p>
        </div>
      </section>
    </div>
  );
}

export default ExpenseInfoStep;
