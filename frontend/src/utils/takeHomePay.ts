import { DEDUCTION_FIELDS } from '../types/api';
import type { IncomeInfo, SpouseIncome } from '../types/api';

/**
 * Schedule I line 4: wages + tips + overtime. It reads the current figures when the person's
 * income is now different ("yes"), the six-month averages otherwise, unanswered included, as
 * the server's schedule_i_field rule does. A blank box counts as 0.
 */
export function scheduleILine4(data: Partial<IncomeInfo>): number {
  if (data.income_now_different === 'yes') {
    return (
      (data.current_monthly_gross_wages ?? 0) +
      (data.current_monthly_tips ?? 0) +
      (data.current_monthly_overtime ?? 0)
    );
  }
  return (data.monthly_gross_wages ?? 0) + (data.monthly_tips ?? 0) + (data.monthly_overtime ?? 0);
}

/** Schedule I line 6: the eight deductions added up, a blank one as 0 */
export function deductionsTotal(data: Partial<IncomeInfo>): number {
  return DEDUCTION_FIELDS.reduce((sum, field) => sum + (data[field] ?? 0), 0);
}

/** Schedule I line 7: line 4 less line 6, below 0 when the deductions are larger */
export function takeHomePay(data: Partial<IncomeInfo>): number {
  return scheduleILine4(data) - deductionsTotal(data);
}

/** True when the person left all eight deductions blank */
export function deductionsBlank(data: Partial<IncomeInfo>): boolean {
  return DEDUCTION_FIELDS.every((field) => data[field] == null);
}

/** True when a person with pay on Schedule I line 4 left all eight deductions blank */
export function takeHomePayNotEntered(data: Partial<IncomeInfo> | SpouseIncome): boolean {
  return scheduleILine4(data) > 0 && deductionsBlank(data);
}
