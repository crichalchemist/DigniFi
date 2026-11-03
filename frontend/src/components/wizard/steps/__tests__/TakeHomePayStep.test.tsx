import { useState } from 'react';
import { render, screen, fireEvent, within } from '@testing-library/react';
import { vi } from 'vitest';
import { TakeHomePayStep } from '../TakeHomePayStep';
import { DEDUCTION_FIELDS } from '../../../../types/api';
import type { IncomeInfo, SpouseIncome } from '../../../../types/api';
import { DEDUCTION_WORDS } from '../../../../constants/formText';
import { PAY_PERIOD_HELP, RETIREMENT_HELP } from '../../../../constants/copy';

/**
 * The step inside a stand-in for the wizard, which holds the filer's and the spouse's income as
 * the wizard does, so a change the step hands up comes back down to it.
 */
function renderStep(income: Partial<IncomeInfo> = {}, spouse: SpouseIncome = {}) {
  const onIncomeDataChange = vi.fn();
  const onSpouseIncomeDataChange = vi.fn();
  const onValidationChange = vi.fn();
  function Wizard() {
    const [incomeData, setIncomeData] = useState(income);
    const [spouseIncomeData, setSpouseIncomeData] = useState(spouse);
    return (
      <TakeHomePayStep
        incomeData={incomeData}
        onIncomeDataChange={(next) => {
          onIncomeDataChange(next);
          setIncomeData(next);
        }}
        spouseIncomeData={spouseIncomeData}
        onSpouseIncomeDataChange={(next) => {
          onSpouseIncomeDataChange(next);
          setSpouseIncomeData(next);
        }}
        maritalStatus={incomeData.marital_status}
        onValidationChange={onValidationChange}
      />
    );
  }
  render(<Wizard />);
  const last = <T,>(spy: ReturnType<typeof vi.fn>) =>
    spy.mock.calls[spy.mock.calls.length - 1][0] as T;
  return {
    lastIncome: () => last<Partial<IncomeInfo>>(onIncomeDataChange),
    lastSpouse: () => last<SpouseIncome>(onSpouseIncomeDataChange),
    lastValidity: () => last<boolean>(onValidationChange),
    validityCalls: () => onValidationChange.mock.calls.length,
  };
}

const type = (label: string, value: string) =>
  fireEvent.change(screen.getByLabelText(label), { target: { value } });

describe('TakeHomePayStep', () => {
  it("the step asks 5a-5h in the form's words for the filer", () => {
    renderStep({ marital_status: 'not_married' });

    for (const field of DEDUCTION_FIELDS) {
      const box = screen.getByLabelText(DEDUCTION_WORDS[field]);
      expect(box).toHaveAttribute('name', field);
    }
    expect(document.querySelector('input[name=payroll_other_specify]')).toHaveAttribute(
      'maxlength',
      '100'
    );
    expect(screen.getByText(PAY_PERIOD_HELP)).toBeInTheDocument();
    expect(screen.getAllByText(RETIREMENT_HELP).length).toBeGreaterThan(0);
    expect(document.querySelector('input[name=spouse_payroll_tax]')).toBeNull();
  });

  it("the spouse's deductions show under married_together only", () => {
    renderStep({ marital_status: 'married_together' });
    expect(screen.getByText("Your spouse's deductions")).toBeInTheDocument();
    expect(document.querySelector('input[name=spouse_payroll_tax]')).not.toBeNull();
  });

  it("the spouse's deductions stay hidden for a spouse who is not at home", () => {
    renderStep({ marital_status: 'married_separately' });
    expect(screen.queryByText("Your spouse's deductions")).toBeNull();
    expect(document.querySelector('input[name=spouse_payroll_tax]')).toBeNull();
  });

  it('lines 4, 6 and 7 are shown and never handed up as data', () => {
    const { lastIncome } = renderStep({
      marital_status: 'not_married',
      monthly_gross_wages: 3000,
    });

    type(DEDUCTION_WORDS.payroll_tax, '400');

    const pay = screen.getByLabelText('Your pay');
    const figure = (line: string) => within(pay).getByText(line).nextElementSibling?.textContent;
    expect(figure('4. Calculate gross income')).toBe('$3,000.00');
    expect(figure('6. Add the payroll deductions')).toBe('$400.00');
    expect(figure('7. Calculate total monthly take-home pay')).toBe('$2,600.00');

    const allowed = new Set<string>([
      ...DEDUCTION_FIELDS,
      'payroll_other_specify',
      'marital_status',
      'monthly_gross_wages',
    ]);
    expect(Object.keys(lastIncome()).filter((key) => !allowed.has(key))).toEqual([]);
  });

  it('a negative take-home pay shows with a leading minus', () => {
    renderStep({ marital_status: 'not_married', monthly_gross_wages: 100, payroll_tax: 300 });

    const pay = screen.getByLabelText('Your pay');
    expect(
      within(pay).getByText('7. Calculate total monthly take-home pay').nextElementSibling
    ).toHaveTextContent('-$200.00');
  });

  it('a blank deduction is null, a typed 0 is 0', () => {
    const { lastIncome } = renderStep({ marital_status: 'not_married', payroll_tax: 400 });

    type(DEDUCTION_WORDS.payroll_tax, '');
    expect(lastIncome().payroll_tax).toBeNull();

    type(DEDUCTION_WORDS.payroll_tax, '0');
    expect(lastIncome().payroll_tax).toBe(0);
  });

  it('the step reports itself valid as soon as it shows, with every box blank', () => {
    // Without this, handleNext's setCanProceed(false) would leave Continue disabled
    const { lastValidity, validityCalls } = renderStep({ marital_status: 'not_married' });

    expect(validityCalls()).toBeGreaterThan(0);
    expect(lastValidity()).toBe(true);
  });

  it('an invalid deduction blocks only this step', () => {
    const { lastValidity } = renderStep({ marital_status: 'not_married' });

    type(DEDUCTION_WORDS.payroll_tax, '12.345');

    expect(lastValidity()).toBe(false);
    expect(screen.getByText('Please enter dollars and cents, like 1250.50')).toBeInTheDocument();
  });

  it("the spouse's deductions are saved apart from the filer's", () => {
    const { lastSpouse } = renderStep({ marital_status: 'married_together', payroll_tax: 400 });

    type(`Spouse's ${DEDUCTION_WORDS.payroll_tax}`, '250');

    expect(lastSpouse().payroll_tax).toBe(250);
    expect(screen.getByLabelText(DEDUCTION_WORDS.payroll_tax)).toHaveValue(400);
  });
});
