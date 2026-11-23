import { useState } from 'react';
import type { ReactElement } from 'react';
import { render, screen, fireEvent, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import { ExpenseInfoStep } from '../ExpenseInfoStep';
import type { ExpenseInfo, ScheduleIAnswers } from '../../../../types/api';
import { EXPENSE_FIELDS } from '../../../../types/api';
import { SCHEDULE_I_TEXT_LIMITS } from '../../../../constants/scheduleILimits';
import {
  EXPENSE_LINE_WORDS,
  EXPENSE_SPECIFY_WORDS,
  FORM_106J_LINE_24_EXAMPLE,
  FORM_106J_LINE_24_QUESTION,
  FORM_106J_LINE_24_YES,
  LINE_3_QUESTION,
  LINE_4_GROUP_HEADING,
  LINE_6_GROUP_HEADING,
  LINE_15_GROUP_HEADING,
  LINE_20_GROUP_HEADING,
  NONCASH_EXPENSES_SENTENCE,
} from '../../../../constants/formText';
import {
  CLAIM_GAP_LINE_4,
  DOUBLE_COUNT_EXPENSES_NOTE,
  EXPENSES_LEGACY_INSURANCE,
  EXPENSES_LEGACY_UTILITIES,
  EXPENSES_LINKED_NOTE,
  HIDDEN_ANSWERS,
  LINE_3_INFO,
  LINE_4_CLEAR,
  LINE_4_HELP,
  LINE_4_PAY_BOTH,
  NOT_SAVED_TRY_AGAIN,
  SCHEDULE_I_GATE_J24,
  SHOW_HIDDEN,
} from '../../../../constants/copy';
import { fill } from '../claims/claimNames';

// Every Schedule J amount ExpenseInfo stores and the forms and the means test read. DRF
// drops any other name without an error, which is how car, food and other costs once
// saved as $0 (DIG-45).

interface StepProps {
  linkedFirstMortgage?: number;
  line4Confirmed?: string | null;
  onLine4Confirm?: (figure: string) => Promise<void>;
}

// The step's Schedule I answers are the wizard's; this holds them as the wizard does
function Holder({
  initialAnswers,
  onAnswers,
  children,
}: {
  initialAnswers: ScheduleIAnswers;
  onAnswers: (next: ScheduleIAnswers) => void;
  children: (answers: ScheduleIAnswers, change: (next: ScheduleIAnswers) => void) => ReactElement;
}) {
  const [answers, setAnswers] = useState(initialAnswers);
  return children(answers, (next) => {
    onAnswers(next);
    setAnswers(next);
  });
}

function renderStep(
  initialData: Partial<ExpenseInfo> = {},
  props: StepProps = {},
  scheduleI: ScheduleIAnswers = {}
) {
  const onDataChange = vi.fn();
  const onValidationChange = vi.fn();
  const onAnswers = vi.fn();
  const element = (next: StepProps) => (
    <Holder initialAnswers={scheduleI} onAnswers={onAnswers}>
      {(answers, change) => (
        <ExpenseInfoStep
          initialData={initialData}
          onDataChange={onDataChange}
          onValidationChange={onValidationChange}
          scheduleIAnswers={answers}
          onScheduleIAnswersChange={change}
          {...next}
        />
      )}
    </Holder>
  );
  const { container, rerender } = render(element(props));
  const inputNamed = (name: string) =>
    container.querySelector(`input[name="${name}"]`) as HTMLInputElement | null;
  const lastEmitted = () =>
    onDataChange.mock.calls[onDataChange.mock.calls.length - 1][0] as Record<string, unknown>;
  // Whether the wizard lets the filer press Continue
  const canContinue = () =>
    onValidationChange.mock.calls[onValidationChange.mock.calls.length - 1][0] as boolean;
  const withProps = (next: StepProps) => rerender(element(next));
  return { container, inputNamed, lastEmitted, canContinue, withProps, onAnswers };
}

describe('ExpenseInfoStep', () => {
  it('saves every expense under the name the court forms read', () => {
    const { inputNamed, lastEmitted } = renderStep();

    EXPENSE_FIELDS.forEach((name, index) => {
      const input = inputNamed(name);
      expect(input, `a box named ${name}`).not.toBeNull();
      fireEvent.change(input!, { target: { value: String((index + 1) * 10) } });
    });

    const emitted = lastEmitted();
    EXPENSE_FIELDS.forEach((name, index) => {
      expect(emitted[name], name).toBe((index + 1) * 10);
    });
    for (const unknownName of [
      'car_payment',
      'car_insurance',
      'gas_transportation',
      'food_groceries',
      'other_necessary_expenses',
    ]) {
      expect(emitted).not.toHaveProperty(unknownName);
    }
  });

  it('asks every Schedule J line in its order and in its words', () => {
    const { container, inputNamed } = renderStep();
    const amounts = Array.from(
      container.querySelectorAll<HTMLInputElement>('input[type="number"]')
    );
    expect(amounts.map((box) => box.name)).toEqual([...EXPENSE_FIELDS]);
    for (const field of EXPENSE_FIELDS) {
      // Lines 6d and 21 are both "Other" in the form's words, so every box is found by name
      expect(inputNamed(field)).toHaveAccessibleName(EXPENSE_LINE_WORDS[field]);
    }
    for (const words of [
      LINE_4_GROUP_HEADING,
      LINE_6_GROUP_HEADING,
      LINE_15_GROUP_HEADING,
      LINE_20_GROUP_HEADING,
      NONCASH_EXPENSES_SENTENCE,
      DOUBLE_COUNT_EXPENSES_NOTE,
      LINE_3_INFO,
    ]) {
      expect(screen.getByText(words)).toBeInTheDocument();
    }
  });

  it('never answers Schedule J line 3 for the filer, and asks it before every amount', () => {
    const { inputNamed, lastEmitted } = renderStep();
    const line3 = screen.getByRole('group', { name: LINE_3_QUESTION });
    const [no, yes] = within(line3).getAllByRole('radio') as HTMLInputElement[]; // No first, then Yes (§5.2)
    expect([no.checked, yes.checked]).toEqual([false, false]);
    expect(lastEmitted().expenses_include_others ?? null).toBeNull();
    expect(
      line3.compareDocumentPosition(inputNamed('rent_or_mortgage')!) &
        Node.DOCUMENT_POSITION_FOLLOWING
    ).toBeTruthy();
    fireEvent.click(yes);
    expect(lastEmitted().expenses_include_others).toBe('yes');
  });

  it('reads the sentence that explains line 3 with its question, answered or not', () => {
    renderStep();
    const line3 = screen.getByRole('group', { name: LINE_3_QUESTION });
    expect(line3).toHaveAccessibleDescription(expect.stringContaining(LINE_3_INFO));
    fireEvent.click(within(line3).getAllByRole('radio')[0]);
    expect(line3).toHaveAccessibleDescription(LINE_3_INFO);
  });

  it('asks 29 amounts and adds them into the monthly total', () => {
    const { inputNamed, lastEmitted } = renderStep();
    expect(EXPENSE_FIELDS).toHaveLength(29);
    for (const field of EXPENSE_FIELDS) {
      fireEvent.change(inputNamed(field)!, { target: { value: '1' } });
    }
    expect(screen.getByText('$29.00')).toBeInTheDocument();
    expect(lastEmitted().total_monthly_expenses).toBe(29);
  });

  it("line 6 asks each utility in the form's words inside its Utilities group", () => {
    const { inputNamed } = renderStep();
    const group = screen.getByRole('group', { name: LINE_6_GROUP_HEADING });
    const names = Array.from(group.querySelectorAll<HTMLInputElement>('input')).map((i) => i.name);
    expect(names).toEqual([
      'electricity_heat_gas',
      'water_sewer_garbage',
      'phone_internet_cable',
      'utilities',
      'utilities_specify',
    ]);
    // 6d is found by its name: line 21 is "Other" too
    expect(inputNamed('utilities')).toHaveAccessibleName('Other');
    expect(group.contains(inputNamed('utilities'))).toBe(true);
    expect(group.contains(inputNamed('utilities_specify'))).toBe(true);
    expect(inputNamed('utilities_specify')).toHaveAccessibleName(
      EXPENSE_SPECIFY_WORDS.utilities_specify
    );
  });

  it('line 15 asks life and health insurance before vehicle and other insurance', () => {
    renderStep();
    const group = screen.getByRole('group', { name: LINE_15_GROUP_HEADING });
    const names = Array.from(group.querySelectorAll<HTMLInputElement>('input')).map((i) => i.name);
    expect(names).toEqual([
      'life_insurance',
      'health_insurance',
      'vehicle_insurance',
      'insurance_not_deducted',
      'insurance_specify',
    ]);
  });

  it('the utilities and insurance help texts are gone', () => {
    renderStep();
    expect(screen.queryByText('Electric, gas, water, trash, internet, phone')).toBeNull();
    expect(screen.queryByText('Health, life, or disability insurance you pay directly')).toBeNull();
    expect(screen.getByText('Monthly auto insurance premium')).toBeInTheDocument();
  });

  describe.each([
    {
      group: 'utilities',
      other: 'utilities',
      specify: 'utilities_specify',
      words: 'Utilities (combined)',
      sentence: EXPENSES_LEGACY_UTILITIES,
      line: 'phone_internet_cable',
    },
    {
      group: 'insurance',
      other: 'insurance_not_deducted',
      specify: 'insurance_specify',
      words: 'Insurance (combined)',
      sentence: EXPENSES_LEGACY_INSURANCE,
      line: 'health_insurance',
    },
  ] as const)('the $group information line', ({ other, specify, words, sentence, line }) => {
    const saved = { [other]: 180, [specify]: words } as Partial<ExpenseInfo>;

    it('a total saved before the split shows its information line under the Specify box', () => {
      const { inputNamed } = renderStep(saved);
      expect(inputNamed(specify)).toHaveAccessibleDescription(sentence);
      expect(screen.getByText(sentence)).toBeInTheDocument();
      expect(screen.queryByRole('status', { name: sentence })).toBeNull();
    });

    it('the information line goes on the first keystroke in the words', () => {
      const { inputNamed } = renderStep(saved);
      fireEvent.change(inputNamed(specify)!, { target: { value: `${words}x` } });
      expect(screen.queryByText(sentence)).toBeNull();
    });

    it('the information line goes once a line of its group has an amount', () => {
      const { inputNamed } = renderStep(saved);
      fireEvent.change(inputNamed(line)!, { target: { value: '30' } });
      expect(screen.queryByText(sentence)).toBeNull();
    });

    it('the information line never shows for words the filer typed', () => {
      renderStep({ [other]: 180, [specify]: 'Septic tank pumping' } as Partial<ExpenseInfo>);
      expect(screen.queryByText(sentence)).toBeNull();
    });

    it('the information line never shows when the Other amount is $0', () => {
      renderStep({ [other]: 0, [specify]: words } as Partial<ExpenseInfo>);
      expect(screen.queryByText(sentence)).toBeNull();
    });

    it('the information line holds nothing back', () => {
      const { canContinue } = renderStep(saved);
      expect(screen.getByText(sentence)).toBeInTheDocument();
      expect(canContinue()).toBe(true);
    });
  });

  it('has no box for a car payment or a mortgage on other property', () => {
    const { container } = renderStep();
    expect(container.querySelector('input[name="vehicle_payment"]')).toBeNull();
    expect(container.querySelector('input[name="other_property_mortgages"]')).toBeNull();
  });

  it('says car and mortgage payments come from the claims steps', () => {
    renderStep();
    expect(screen.getByText(EXPENSES_LINKED_NOTE)).toBeInTheDocument();
    expect(screen.getByText(LINE_4_HELP)).toBeInTheDocument();
    expect(
      screen.queryByText('This is your total monthly expenses across all categories.')
    ).toBeNull();
  });

  describe('the line 4 question', () => {
    const sentence = fill(CLAIM_GAP_LINE_4, { typed: '1,200.00', linked: '1,200.00' });
    const rent1200 = { rent_or_mortgage: 1200 };

    it('shows only while a typed rent sits beside a linked first mortgage', () => {
      const { withProps } = renderStep(rent1200, { linkedFirstMortgage: 1200 });
      expect(screen.getByText(sentence)).toBeInTheDocument();
      // The total stays typed-only beside a linked figure
      expect(screen.getByText('$1,200.00')).toBeInTheDocument();

      withProps({ linkedFirstMortgage: 1200, line4Confirmed: '1200.00' });
      expect(screen.queryByText(sentence)).toBeNull();
      withProps({ linkedFirstMortgage: 1200, line4Confirmed: '1200' });
      expect(screen.queryByText(sentence)).toBeNull();
      withProps({ linkedFirstMortgage: 0, line4Confirmed: null });
      expect(screen.queryByText(sentence)).toBeNull();
      // A confirmed figure that is not the one in the box asks again
      withProps({ linkedFirstMortgage: 1200, line4Confirmed: '1100.00' });
      expect(screen.getByText(sentence)).toBeInTheDocument();
    });

    it('stays away while the rent is 0', () => {
      renderStep({ rent_or_mortgage: 0 }, { linkedFirstMortgage: 1200 });
      expect(screen.queryByText(/Do you pay both/)).toBeNull();
    });

    it('sends the typed figure when the filer says they pay both', () => {
      const onLine4Confirm = vi.fn().mockResolvedValue(undefined);
      renderStep(rent1200, { linkedFirstMortgage: 1200, onLine4Confirm });
      fireEvent.click(screen.getByRole('button', { name: LINE_4_PAY_BOTH }));
      expect(onLine4Confirm).toHaveBeenCalledTimes(1);
      expect(onLine4Confirm).toHaveBeenCalledWith('1200.00');
    });

    it('sets the rent to 0 when the filer says no', () => {
      const { lastEmitted } = renderStep(rent1200, { linkedFirstMortgage: 1200 });
      fireEvent.click(
        screen.getByRole('button', { name: fill(LINE_4_CLEAR, { typed: '1,200.00' }) })
      );
      expect(lastEmitted().rent_or_mortgage).toBe(0);
      expect(screen.queryByText(sentence)).toBeNull();
    });

    it('starts with neither button pressed and holds no status or alert region', () => {
      renderStep(rent1200, { linkedFirstMortgage: 1200 });
      for (const button of screen.getAllByRole('button')) {
        expect(button).not.toHaveAttribute('aria-pressed', 'true');
      }
      expect(screen.getByText(sentence).closest('[role="status"], [role="alert"]')).toBeNull();
    });

    it("reads as the buttons' description, so each is pressed knowing what it answers", () => {
      renderStep(rent1200, { linkedFirstMortgage: 1200 });
      for (const name of [LINE_4_PAY_BOTH, fill(LINE_4_CLEAR, { typed: '1,200.00' })]) {
        expect(screen.getByRole('button', { name })).toHaveAccessibleDescription(sentence);
      }
    });

    it('never holds Continue', () => {
      const { canContinue } = renderStep(rent1200, { linkedFirstMortgage: 1200 });
      expect(screen.getByText(sentence)).toBeInTheDocument();
      expect(canContinue()).toBe(true);
    });

    it('keeps the question and says so when the answer was not saved', async () => {
      const onLine4Confirm = vi.fn().mockRejectedValue(new Error('no'));
      renderStep(rent1200, { linkedFirstMortgage: 1200, onLine4Confirm });
      fireEvent.click(screen.getByRole('button', { name: LINE_4_PAY_BOTH }));
      const alert = await screen.findByRole('alert');
      expect(alert).toHaveTextContent(NOT_SAVED_TRY_AGAIN);
      expect(screen.getByText(sentence)).toBeInTheDocument();
    });

    it('drops the not-saved alert once the rent changes to another figure that still asks', async () => {
      const onLine4Confirm = vi.fn().mockRejectedValue(new Error('no'));
      const { inputNamed } = renderStep(rent1200, { linkedFirstMortgage: 1200, onLine4Confirm });
      fireEvent.click(screen.getByRole('button', { name: LINE_4_PAY_BOTH }));
      await screen.findByRole('alert');

      fireEvent.change(inputNamed('rent_or_mortgage')!, { target: { value: '1100' } });

      expect(screen.queryByRole('alert')).toBeNull();
      expect(
        screen.getByText(fill(CLAIM_GAP_LINE_4, { typed: '1,100.00', linked: '1,200.00' }))
      ).toBeInTheDocument();
    });
  });

  it.each([
    ['utilities', 'utilities_specify'],
    ['insurance_not_deducted', 'insurance_specify'],
    ['taxes_not_deducted', 'taxes_specify'],
    ['support_others', 'support_others_specify'],
    ['other_expenses', 'other_expenses_specify'],
  ] as const)(
    'puts the Specify box for %s right after its amount, taking 100 characters',
    (amount, specify) => {
      const { container, inputNamed, lastEmitted } = renderStep();
      const names = Array.from(container.querySelectorAll<HTMLInputElement>('input')).map(
        (i) => i.name
      );
      expect(names.indexOf(specify)).toBe(names.indexOf(amount) + 1);
      expect(inputNamed(specify)).toHaveAccessibleName(EXPENSE_SPECIFY_WORDS[specify]);
      expect(inputNamed(specify)).toHaveAttribute('maxlength', '100');
      fireEvent.change(inputNamed(specify)!, {
        target: { value: 'IRS installment agreement, 2025 tax' },
      });
      expect(lastEmitted()[specify]).toBe('IRS installment agreement, 2025 tax');
    }
  );

  it('counts clothing and child support paid in the monthly total', () => {
    const { inputNamed, lastEmitted } = renderStep();

    fireEvent.change(inputNamed('rent_or_mortgage')!, { target: { value: '1000' } });
    fireEvent.change(screen.getByLabelText(EXPENSE_LINE_WORDS.clothing), {
      target: { value: '60' },
    });
    fireEvent.change(screen.getByLabelText(EXPENSE_LINE_WORDS.child_support_paid), {
      target: { value: '200' },
    });

    expect(screen.getByText('$1,260.00')).toBeInTheDocument();
    expect(lastEmitted().total_monthly_expenses).toBe(1260);
  });

  // The server stores each amount as DecimalField(max_digits=10, decimal_places=2) and refuses
  // anything else, so the box says what is wrong before Continue saves it (W-9)
  it('asks for dollars and cents beside a box with a third decimal place, and blocks Continue', () => {
    const { canContinue } = renderStep();

    fireEvent.change(screen.getByLabelText(EXPENSE_LINE_WORDS.clothing), {
      target: { value: '12.345' },
    });

    expect(screen.getByLabelText(EXPENSE_LINE_WORDS.clothing)).toHaveAccessibleDescription(
      /^Please enter dollars and cents, like 1250\.50 /
    );
    expect(canContinue()).toBe(false);
  });

  it('says beside the box that an amount over $99,999,999.99 is too large, and blocks Continue', () => {
    const { canContinue } = renderStep();

    fireEvent.change(screen.getByLabelText(EXPENSE_LINE_WORDS.clothing), {
      target: { value: '100000000' },
    });

    expect(screen.getByLabelText(EXPENSE_LINE_WORDS.clothing)).toHaveAccessibleDescription(
      /^This amount is too large\. Please check it /
    );
    expect(canContinue()).toBe(false);
  });

  it('takes the largest amount the server stores, $99,999,999.99', () => {
    const { lastEmitted, canContinue } = renderStep();

    fireEvent.change(screen.getByLabelText(EXPENSE_LINE_WORDS.clothing), {
      target: { value: '99999999.99' },
    });

    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(canContinue()).toBe(true);
    expect(lastEmitted().clothing).toBe(99999999.99);
  });

  // Coming back to the step, the wizard hands it the total it last added up, which no box shows
  it('lets a returning filer continue when the total their amounts add up to is not a whole cent', () => {
    const { canContinue } = renderStep({
      clothing: 10.1,
      utilities: 20.2,
      total_monthly_expenses: 10.1 + 20.2,
    });

    expect(canContinue()).toBe(true);
  });

  // Schedule J line 24 (4c spec §6.2): the filer's own answer, in the form's words
  describe('Schedule J line 24', () => {
    const statusLine = () => document.querySelector('.expense-info-step > [role="status"]');
    const radio = (container: HTMLElement, value: string) =>
      container.querySelector<HTMLInputElement>(
        `input[name="schedule_j_line_24_answer"][value="${value}"]`
      )!;

    it("line 24 asks in Schedule J's words, with its example", async () => {
      const user = userEvent.setup();
      const { container, onAnswers } = renderStep();

      const legend = screen.getByText(FORM_106J_LINE_24_QUESTION, { exact: false });
      expect(legend.closest('fieldset')).toContainElement(
        screen.getByText(FORM_106J_LINE_24_EXAMPLE)
      );
      const radios = Array.from(
        container.querySelectorAll<HTMLInputElement>('input[name="schedule_j_line_24_answer"]')
      );
      // No, then Yes, with nothing checked
      expect(radios.map((box) => box.value)).toEqual(['no', 'yes']);
      expect(radios.some((box) => box.checked)).toBe(false);
      expect(container.querySelector('[name="schedule_j_line_24_text"]')).toBeNull();

      await user.click(radio(container, 'yes'));
      expect(onAnswers).toHaveBeenLastCalledWith({ schedule_j_line_24_answer: 'yes' });
      const box = screen.getByLabelText(FORM_106J_LINE_24_YES) as HTMLTextAreaElement;
      expect(box.name).toBe('schedule_j_line_24_text');
      expect(box.maxLength).toBe(SCHEDULE_I_TEXT_LIMITS.schedule_j_line_24_text);
      fireEvent.change(box, { target: { value: 'The car loan ends in May' } });
      expect(onAnswers).toHaveBeenLastCalledWith({
        schedule_j_line_24_answer: 'yes',
        schedule_j_line_24_text: 'The car loan ends in May',
      });
    });

    it('the step says why Continue waits for line 24', () => {
      // Every box valid: line 24 alone holds Continue, so the sentence shows at once (FR-1)
      renderStep();
      expect(statusLine()).toHaveTextContent(SCHEDULE_I_GATE_J24);
    });

    it('while a box holds Continue, the line 24 sentence waits until line 24 is touched', () => {
      // Mounted throughout, so a screen reader reads what arrives
      const { container } = renderStep({ utilities: -5 });
      expect(statusLine()).toBeEmptyDOMElement();

      fireEvent.blur(radio(container, 'no'), {
        relatedTarget: container.querySelector('input[name="clothing"]'),
      });
      expect(statusLine()).toHaveTextContent(SCHEDULE_I_GATE_J24);

      // Answering it clears the sentence
      fireEvent.click(radio(container, 'no'));
      expect(statusLine()).toBeEmptyDOMElement();
    });

    it('a text kept under No hides behind one line', async () => {
      const user = userEvent.setup();
      const { container, onAnswers } = renderStep(
        {},
        {},
        { schedule_j_line_24_answer: 'no', schedule_j_line_24_text: 'The car loan ends in May' }
      );
      expect(container.querySelector('[name="schedule_j_line_24_text"]')).toBeNull();
      expect(screen.getAllByText(HIDDEN_ANSWERS)).toHaveLength(1);
      // Showing the step changed nothing
      expect(onAnswers).not.toHaveBeenCalled();

      await user.click(screen.getByRole('button', { name: SHOW_HIDDEN }));
      expect(screen.getByLabelText(FORM_106J_LINE_24_YES)).toHaveValue('The car loan ends in May');
    });
  });
});
