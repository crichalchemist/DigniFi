import { useState } from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';
import { LineQuestion } from '../LineQuestion';
import type { LineBox } from '../LineQuestion';
import {
  AMOUNT_DECIMALS,
  DELETE_HIDDEN,
  HIDDEN_ANSWERS,
  SCHEDULE_I_LINE_11_AMOUNT_LABEL,
  SCHEDULE_I_LINE_11_QUESTION,
  SHOW_HIDDEN,
} from '../../../../../constants/copy';
import {
  FORM_106I_LINE_11,
  FORM_106I_LINE_11_BOX_LABEL,
  FORM_106I_LINE_13_QUESTION,
  FORM_106I_LINE_13_YES,
} from '../../../../../constants/formText';
import { SCHEDULE_I_TEXT_LIMITS } from '../../../../../constants/scheduleILimits';
import type { ScheduleIAnswers } from '../../../../../types/api';

const LINE_11_BOXES: LineBox[] = [
  { key: 'line_11_text', label: FORM_106I_LINE_11_BOX_LABEL },
  { key: 'line_11_amount', label: SCHEDULE_I_LINE_11_AMOUNT_LABEL, amount: true },
];

/** Line 11 with the step's state around it, so pressing and typing behave as on the Income step */
function Harness({
  initial = {},
  onChange,
  boxes = LINE_11_BOXES,
}: {
  initial?: ScheduleIAnswers;
  onChange?: (next: ScheduleIAnswers) => void;
  boxes?: LineBox[];
}) {
  const [answers, setAnswers] = useState<ScheduleIAnswers>(initial);
  return (
    <main>
      <LineQuestion
        question={SCHEDULE_I_LINE_11_QUESTION}
        note={FORM_106I_LINE_11}
        name="line_11_answer"
        answers={answers}
        onChange={(next) => {
          onChange?.(next);
          setAnswers(next);
        }}
        boxes={boxes}
      />
    </main>
  );
}

const radio = (name: string, value: string) =>
  document.querySelector(`input[name="${name}"][value="${value}"]`) as HTMLInputElement;

describe('LineQuestion', () => {
  it('asks the question with the form sentence under it and nothing checked', async () => {
    const { container } = render(<Harness />);
    // Required: Complete waits for the answer (a gate, 4c-R1)
    expect(
      screen.getByRole('group', { name: `${SCHEDULE_I_LINE_11_QUESTION}required` })
    ).toBeInTheDocument();
    expect(screen.getByText(FORM_106I_LINE_11)).toBeInTheDocument();
    const radios = Array.from(
      document.querySelectorAll<HTMLInputElement>('input[name="line_11_answer"]')
    );
    // No before Yes, and neither starts checked: a No the filer didn't give is never printed
    expect(radios.map((r) => r.value)).toEqual(['no', 'yes']);
    expect(radios.some((r) => r.checked)).toBe(false);
    expect(document.querySelector('[name="line_11_text"]')).toBeNull();
    expect(await axe(container)).toHaveNoViolations();
  });

  it('Yes shows the boxes', async () => {
    const user = userEvent.setup();
    const changes: ScheduleIAnswers[] = [];
    render(<Harness onChange={(next) => changes.push(next)} />);

    await user.click(radio('line_11_answer', 'no'));
    expect(document.querySelector('[name="line_11_text"]')).toBeNull();

    await user.click(radio('line_11_answer', 'yes'));
    const text = screen.getByLabelText(FORM_106I_LINE_11_BOX_LABEL);
    const amount = screen.getByLabelText(SCHEDULE_I_LINE_11_AMOUNT_LABEL);
    // Each box is named by its ScheduleIAnswers key (PF-4c-J), and a text stops at its cap
    expect(text).toHaveAttribute('name', 'line_11_text');
    expect(text).toHaveAttribute('maxLength', String(SCHEDULE_I_TEXT_LIMITS.line_11_text));
    expect(amount).toHaveAttribute('name', 'line_11_amount');
    // The amount box holds what was typed, a stray letter included, so it can say why it is held
    await user.type(amount, '12.5x');
    expect(amount).toHaveValue('12.5x');
    expect(changes.at(-1)).toEqual({ line_11_answer: 'yes', line_11_amount: '12.5x' });
  });

  it('a text kept under No hides behind one line', async () => {
    const user = userEvent.setup();
    const changes: ScheduleIAnswers[] = [];
    render(
      <Harness
        initial={{ line_11_answer: 'no', line_11_text: 'My sister', line_11_amount: '200.00' }}
        onChange={(next) => changes.push(next)}
      />
    );
    // What was typed stays stored and unshown, behind exactly one line
    expect(document.querySelector('[name="line_11_text"]')).toBeNull();
    expect(screen.getAllByText(HIDDEN_ANSWERS)).toHaveLength(1);

    await user.click(screen.getByRole('button', { name: SHOW_HIDDEN }));
    expect(screen.getByLabelText(FORM_106I_LINE_11_BOX_LABEL)).toHaveValue('My sister');
    // Show fixes the boxes for the visit: clearing the last one keeps them open
    await user.clear(screen.getByLabelText(FORM_106I_LINE_11_BOX_LABEL));
    await user.clear(screen.getByLabelText(SCHEDULE_I_LINE_11_AMOUNT_LABEL));
    expect(screen.getByLabelText(FORM_106I_LINE_11_BOX_LABEL)).toBeInTheDocument();
    expect(screen.queryByText(HIDDEN_ANSWERS)).not.toBeInTheDocument();
  });

  it("Delete clears that line's boxes and nothing else", async () => {
    const user = userEvent.setup();
    const changes: ScheduleIAnswers[] = [];
    render(
      <Harness
        initial={{
          line_11_answer: 'no',
          line_11_text: 'My sister',
          line_11_amount: '200.00',
          line_13_answer: 'yes',
          line_13_text: 'A raise',
        }}
        onChange={(next) => changes.push(next)}
      />
    );
    await user.click(screen.getByRole('button', { name: DELETE_HIDDEN }));
    expect(changes.at(-1)).toEqual({
      line_11_answer: 'no',
      line_11_text: null,
      line_11_amount: null,
      line_13_answer: 'yes',
      line_13_text: 'A raise',
    });
    expect(screen.queryByText(HIDDEN_ANSWERS)).not.toBeInTheDocument();
  });

  it('a No with nothing stored shows the question alone', () => {
    render(<Harness initial={{ line_11_answer: 'no', line_11_text: '  ' }} />);
    expect(screen.queryByText(HIDDEN_ANSWERS)).not.toBeInTheDocument();
    expect(document.querySelector('[name="line_11_text"]')).toBeNull();
  });

  it('a box that says why it is held is never hidden', () => {
    // A refused amount kept under No still holds the save, so its box stays where it can be fixed
    render(
      <Harness
        initial={{ line_11_answer: 'no', line_11_amount: 'abc' }}
        boxes={[
          { key: 'line_11_text', label: FORM_106I_LINE_11_BOX_LABEL },
          {
            key: 'line_11_amount',
            label: SCHEDULE_I_LINE_11_AMOUNT_LABEL,
            amount: true,
            error: AMOUNT_DECIMALS,
          },
        ]}
      />
    );
    expect(screen.getByLabelText(SCHEDULE_I_LINE_11_AMOUNT_LABEL)).toHaveValue('abc');
    expect(screen.getByText(AMOUNT_DECIMALS)).toBeInTheDocument();
    expect(screen.queryByText(HIDDEN_ANSWERS)).not.toBeInTheDocument();
  });

  it('a long answer gets a box of several lines', () => {
    render(
      <main>
        <LineQuestion
          question={FORM_106I_LINE_13_QUESTION}
          name="line_13_answer"
          answers={{ line_13_answer: 'yes' }}
          onChange={() => {}}
          boxes={[{ key: 'line_13_text', label: FORM_106I_LINE_13_YES, long: true }]}
        />
      </main>
    );
    const box = screen.getByLabelText(FORM_106I_LINE_13_YES);
    expect(box.tagName).toBe('TEXTAREA');
    expect(box).toHaveAttribute('name', 'line_13_text');
    expect(box).toHaveAttribute('maxLength', String(SCHEDULE_I_TEXT_LIMITS.line_13_text));
  });
});
