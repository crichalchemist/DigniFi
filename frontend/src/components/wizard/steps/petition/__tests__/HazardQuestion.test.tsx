import { useState } from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';
import { HazardQuestion } from '../HazardQuestion';
import { hazardGap } from '../petitionGaps';
import {
  DELETE_HIDDEN,
  HIDDEN_ANSWERS,
  NOT_ANSWERED_YET,
  PETITION_GATE_HAZARD,
  SHOW_HIDDEN,
} from '../../../../../constants/copy';
import {
  FORM_101_LINE_14,
  FORM_101_LINE_14_EXAMPLE,
  FORM_101_LINE_14_PROMPTS,
} from '../../../../../constants/formText';
import { PETITION_TEXT_LIMITS } from '../../../../../constants/petitionLimits';
import type { PetitionAnswers } from '../../../../../types/api';

/** The block with the step's state around it, so pressing and typing behave as on Assets */
function Harness({
  initial = {},
  touched = false,
  onChange,
}: {
  initial?: PetitionAnswers;
  touched?: boolean;
  onChange?: (next: PetitionAnswers) => void;
}) {
  const [answers, setAnswers] = useState<PetitionAnswers>(initial);
  const [left, setLeft] = useState(false);
  return (
    <main>
      <HazardQuestion
        answers={answers}
        onChange={(next) => {
          onChange?.(next);
          setAnswers(next);
        }}
        touched={touched || left}
        onLeave={() => setLeft(true)}
      />
      <button type="button">Somewhere else</button>
    </main>
  );
}

const radio = (name: string, value: string) =>
  document.querySelector(`input[name="${name}"][value="${value}"]`) as HTMLInputElement;

const TEXT_KEYS = ['hazard_what', 'hazard_why', 'hazard_street', 'hazard_city', 'hazard_zip'];

describe('HazardQuestion', () => {
  it("asks the hazard in the form's words with nothing checked", () => {
    render(<Harness />);
    expect(
      screen.getByRole('group', { name: new RegExp(FORM_101_LINE_14.slice(0, 40)) })
    ).toBeInTheDocument();
    expect(screen.getByText(FORM_101_LINE_14_EXAMPLE)).toBeInTheDocument();
    const radios = Array.from(
      document.querySelectorAll<HTMLInputElement>('input[name="hazard_answer"]')
    );
    // No before Yes, and neither starts checked: a No the filer didn't give is never printed
    expect(radios.map((r) => r.value)).toEqual(['no', 'yes']);
    expect(radios.some((r) => r.checked)).toBe(false);
  });

  it('shows the three prompts and the address only under a Yes', async () => {
    const user = userEvent.setup();
    const changes: PetitionAnswers[] = [];
    render(<Harness onChange={(next) => changes.push(next)} />);
    expect(screen.queryByLabelText(FORM_101_LINE_14_PROMPTS.what)).not.toBeInTheDocument();

    await user.click(radio('hazard_answer', 'no'));
    expect(screen.queryByLabelText(FORM_101_LINE_14_PROMPTS.what)).not.toBeInTheDocument();
    expect(document.querySelector('input[name="hazard_street"]')).toBeNull();

    await user.click(radio('hazard_answer', 'yes'));
    expect(screen.getByLabelText(FORM_101_LINE_14_PROMPTS.what)).toBeInTheDocument();
    expect(screen.getByLabelText(FORM_101_LINE_14_PROMPTS.why)).toBeInTheDocument();
    // "Where is the property?" names the address boxes as one group, so a screen reader reads the
    // question with each box
    const where = screen.getByRole('group', { name: FORM_101_LINE_14_PROMPTS.where });
    expect(where.querySelector('input[name="hazard_street"]')).not.toBeNull();
    expect(where.querySelector('input[name="hazard_zip"]')).not.toBeNull();
    // Every box is named by its PetitionAnswers key (PF2-T8-5), and the address has no name box
    for (const key of [...TEXT_KEYS, 'hazard_state']) {
      expect(document.querySelector(`[name="${key}"]`), key).not.toBeNull();
    }
    // Each text stops at the cap the server measures (PF2-T9-7)
    expect(screen.getByLabelText(FORM_101_LINE_14_PROMPTS.what)).toHaveAttribute(
      'maxLength',
      String(PETITION_TEXT_LIMITS.hazard_what)
    );
    expect(screen.getByLabelText(FORM_101_LINE_14_PROMPTS.why)).toHaveAttribute(
      'maxLength',
      String(PETITION_TEXT_LIMITS.hazard_why)
    );
    await user.type(screen.getByLabelText(FORM_101_LINE_14_PROMPTS.what), 'Barn roof');
    expect(changes.at(-1)).toMatchObject({ hazard_answer: 'yes', hazard_what: 'Barn roof' });
  });

  it('keeps what was typed under a No, hidden, with Show and Delete (PF2-U1)', async () => {
    const user = userEvent.setup();
    const changes: PetitionAnswers[] = [];
    const stored: PetitionAnswers = {
      hazard_answer: 'no',
      hazard_what: 'Barn roof',
      hazard_city: 'Rockford',
    };
    const { unmount } = render(<Harness initial={stored} />);
    expect(screen.getByText(HIDDEN_ANSWERS)).toBeInTheDocument();
    expect(screen.queryByLabelText(FORM_101_LINE_14_PROMPTS.what)).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: SHOW_HIDDEN }));
    expect(screen.getByLabelText(FORM_101_LINE_14_PROMPTS.what)).toHaveValue('Barn roof');
    unmount();

    render(<Harness initial={stored} onChange={(next) => changes.push(next)} />);
    await user.click(screen.getByRole('button', { name: DELETE_HIDDEN }));
    expect(screen.queryByText(HIDDEN_ANSWERS)).not.toBeInTheDocument();
    const last = changes.at(-1)!;
    expect(last.hazard_answer).toBe('no');
    for (const key of [...TEXT_KEYS, 'hazard_state']) {
      expect(last[key as keyof PetitionAnswers], key).toBeNull();
    }
  });

  it('a No with nothing typed under it shows no hidden-answers line', async () => {
    render(<Harness initial={{ hazard_answer: 'no' }} />);
    expect(screen.queryByText(HIDDEN_ANSWERS)).not.toBeInTheDocument();
  });

  it("says what is still missing in the server's words", async () => {
    // The step's one status region shows this sentence (PF2-T9-6): the block has none of its own
    expect(hazardGap({})).toBe(PETITION_GATE_HAZARD);
    expect(hazardGap({ hazard_what: 'Barn roof' })).toBe(PETITION_GATE_HAZARD);
    expect(hazardGap({ hazard_answer: 'no' })).toBeNull();
    expect(hazardGap({ hazard_answer: 'yes' })).toBeNull();

    const user = userEvent.setup();
    render(<Harness />);
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
    // Nothing says "Not answered yet" until the filer has passed the block
    expect(screen.queryByText(NOT_ANSWERED_YET)).not.toBeInTheDocument();
    await user.click(radio('hazard_answer', 'no'));
    await user.tab();
    expect(screen.queryByText(NOT_ANSWERED_YET)).not.toBeInTheDocument();
  });

  it('says "Not answered yet" once focus has left the block unanswered', async () => {
    const user = userEvent.setup();
    render(<Harness />);
    radio('hazard_answer', 'no').focus();
    await user.click(screen.getByRole('button', { name: 'Somewhere else' }));
    expect(screen.getByText(NOT_ANSWERED_YET)).toBeInTheDocument();
  });

  it('has no accessibility violations with the details open', async () => {
    const { container } = render(<Harness initial={{ hazard_answer: 'yes' }} touched />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
