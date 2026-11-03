import { describe, it, expect } from 'vitest';
import {
  deductionsBlank,
  deductionsTotal,
  scheduleILine4,
  takeHomePay,
  takeHomePayNotEntered,
} from '../takeHomePay';

describe('take-home pay not entered', () => {
  it('names take-home pay as not entered only for a person with pay who left all eight blank', () => {
    expect(takeHomePayNotEntered({ monthly_gross_wages: 3000 })).toBe(true);
    expect(takeHomePayNotEntered({ monthly_gross_wages: 3000, payroll_tax: 0 })).toBe(false);
    expect(takeHomePayNotEntered({ monthly_gross_wages: 0 })).toBe(false);
    // Schedule I's figures: under "now different" Yes with no current wage, line 4 is 0
    expect(takeHomePayNotEntered({ monthly_gross_wages: 3000, income_now_different: 'yes' })).toBe(
      false
    );
  });
});

describe('take-home pay arithmetic', () => {
  it('line 4 follows the figures Schedule I uses, averages while unanswered', () => {
    const avg = {
      monthly_gross_wages: 3000,
      monthly_tips: 200,
      monthly_overtime: 100,
      current_monthly_gross_wages: 2500,
      current_monthly_tips: null,
      current_monthly_overtime: null,
    };
    expect(scheduleILine4({ ...avg, income_now_different: null })).toBe(3300);
    expect(scheduleILine4({ ...avg, income_now_different: 'no' })).toBe(3300);
    expect(scheduleILine4({ ...avg, income_now_different: 'yes' })).toBe(2500);
    expect(deductionsTotal({ payroll_tax: 400, payroll_insurance: null })).toBe(400);
    expect(takeHomePay({ ...avg, income_now_different: null, payroll_tax: 3500 })).toBe(-200);
    expect(deductionsBlank({ payroll_tax: null })).toBe(true);
    expect(deductionsBlank({ payroll_union_dues: 0 })).toBe(false);
  });
});
