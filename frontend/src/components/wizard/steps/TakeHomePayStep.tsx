/**
 * Take-home pay step (wizard step 3): Schedule I lines 5a-5h, what is taken out of pay each
 * month, for the filer and for a spouse who lives with them. Lines 4, 6 and 7 are worked out
 * from the wizard's state and shown only; the server works the forms' figures out itself.
 *
 * Controlled: the step keeps no copy, so the Income step and this one show what the other
 * last changed (3e2 spec §7.2).
 */

import { useEffect, useMemo } from 'react';
import { FormField } from '../../common';
import { amountError, parseAmount } from '../../../utils/parseAmount';
import { deductionsTotal, scheduleILine4, takeHomePay } from '../../../utils/takeHomePay';
import {
  DEDUCTIONS_HEADING,
  OTHER_DEDUCTIONS_SPECIFY_LABEL,
  PAY_PERIOD_HELP,
  RETIREMENT_HELP,
  SPOUSE_DEDUCTIONS_HEADING,
  SPOUSE_DEDUCTION_LABEL_PREFIX,
  SPOUSE_OTHER_DEDUCTIONS_SPECIFY_LABEL,
  TAKE_HOME_PAY_INTRO,
} from '../../../constants/copy';
import {
  DEDUCTION_WORDS,
  SCHEDULE_I_LINE_4,
  SCHEDULE_I_LINE_6,
  SCHEDULE_I_LINE_7,
} from '../../../constants/formText';
import { DEDUCTION_FIELDS } from '../../../types/api';
import type { DeductionField, IncomeInfo, MaritalStatus, SpouseIncome } from '../../../types/api';

interface TakeHomePayStepProps {
  incomeData: Partial<IncomeInfo>;
  onIncomeDataChange: (data: Partial<IncomeInfo>) => void;
  spouseIncomeData: SpouseIncome;
  onSpouseIncomeDataChange: (data: SpouseIncome) => void;
  maritalStatus: MaritalStatus | null | undefined;
  onValidationChange: (isValid: boolean) => void;
}

/** A month's figure in dollars and cents, with a leading minus below $0 */
function formatLine(total: number) {
  const dollars = `$${Math.abs(total).toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
  return total < 0 ? `-${dollars}` : dollars;
}

// 5b and 5c are the two retirement lines the help text speaks to
const RETIREMENT_FIELDS: readonly DeductionField[] = [
  'payroll_mandatory_retirement',
  'payroll_voluntary_retirement',
];

export function TakeHomePayStep({
  incomeData,
  onIncomeDataChange,
  spouseIncomeData,
  onSpouseIncomeDataChange,
  maritalStatus,
  onValidationChange,
}: TakeHomePayStepProps) {
  const livingTogether = maritalStatus === 'married_together';

  // Each amount as the server stores it. The spouse's boxes only while they show.
  const errors = useMemo(() => {
    const found: Record<string, string> = {};
    for (const field of DEDUCTION_FIELDS) {
      const message = amountError(incomeData[field] ?? undefined, 10);
      if (message) found[field] = message;
      if (livingTogether) {
        const spouseMessage = amountError(spouseIncomeData[field] ?? undefined, 10);
        if (spouseMessage) found[`spouse_${field}`] = spouseMessage;
      }
    }
    return found;
  }, [incomeData, spouseIncomeData, livingTogether]);

  // Reports on mount too, so Continue is on while every box is blank
  const valid = Object.keys(errors).length === 0;
  useEffect(() => {
    onValidationChange(valid);
    // onValidationChange is a fresh closure each render; listing it would loop
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [valid]);

  const person = (spouse: boolean) => {
    const prefix = spouse ? 'spouse_' : '';
    const data: Partial<IncomeInfo> = spouse ? spouseIncomeData : incomeData;
    const update = (patch: Partial<IncomeInfo>) =>
      spouse
        ? onSpouseIncomeDataChange({ ...spouseIncomeData, ...patch })
        : onIncomeDataChange({ ...incomeData, ...patch });
    const label = (words: string) => (spouse ? `${SPOUSE_DEDUCTION_LABEL_PREFIX} ${words}` : words);
    const dlLabel = spouse ? "Your spouse's pay" : 'Your pay';

    return (
      <section className="form-section">
        <h3 className="section-title">{spouse ? SPOUSE_DEDUCTIONS_HEADING : DEDUCTIONS_HEADING}</h3>
        {/* The help speaks to the filer; under a spouse's boxes it is left out (§7.1) */}
        {!spouse && <p className="section-description">{PAY_PERIOD_HELP}</p>}
        {DEDUCTION_FIELDS.map((field) => (
          <FormField
            key={field}
            label={label(DEDUCTION_WORDS[field])}
            name={`${prefix}${field}`}
            type="number"
            min="0"
            step="0.01"
            value={data[field] ?? ''}
            onChange={(e) => update({ [field]: parseAmount(e.target.value) ?? null })}
            error={errors[`${prefix}${field}`]}
            helpText={!spouse && RETIREMENT_FIELDS.includes(field) ? RETIREMENT_HELP : undefined}
            placeholder="0.00"
          />
        ))}
        <FormField
          label={spouse ? SPOUSE_OTHER_DEDUCTIONS_SPECIFY_LABEL : OTHER_DEDUCTIONS_SPECIFY_LABEL}
          name={`${prefix}payroll_other_specify`}
          type="text"
          maxLength={100}
          value={data.payroll_other_specify ?? ''}
          onChange={(e) => update({ payroll_other_specify: e.target.value })}
        />
        <dl className="income-total" aria-label={dlLabel}>
          <div>
            <dt className="total-label">{SCHEDULE_I_LINE_4}</dt>
            <dd className="total-amount">{formatLine(scheduleILine4(data))}</dd>
          </div>
          <div>
            <dt className="total-label">{SCHEDULE_I_LINE_6}</dt>
            <dd className="total-amount">{formatLine(deductionsTotal(data))}</dd>
          </div>
          <div>
            <dt className="total-label">{SCHEDULE_I_LINE_7}</dt>
            <dd className="total-amount">{formatLine(takeHomePay(data))}</dd>
          </div>
        </dl>
      </section>
    );
  };

  return (
    <div className="wizard-step">
      <p className="section-description">{TAKE_HOME_PAY_INTRO}</p>
      {person(false)}
      {livingTogether && person(true)}
    </div>
  );
}
