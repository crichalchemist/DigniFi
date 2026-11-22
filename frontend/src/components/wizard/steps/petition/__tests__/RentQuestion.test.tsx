import { useState } from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';
import { RentQuestion } from '../RentQuestion';
import { rentGap } from '../petitionGaps';
import {
  COURT_FORM_101A_URL,
  COURT_FORM_101B_URL,
  FORM_101A_LINK,
  FORM_101A_NOT_YET,
  DELETE_HIDDEN,
  FORM_101_LINE_11_LEAD,
  FORM_101A_SAYS,
  FORM_101B_LINK,
  FORM_101B_NOT_PREPARED,
  HIDDEN_ANSWERS,
  NOT_ANSWERED_YET,
  PETITION_GATE_EVICTION,
  PETITION_GATE_RENTS,
  SHOW_HIDDEN,
} from '../../../../../constants/copy';
import {
  FORM_101_LINE_11_EVICTION,
  FORM_101_LINE_11_NOTICE,
  FORM_101_LINE_11_RENT,
  FORM_101A_SERVICE_CONDITIONS,
  FORM_101A_SERVICE_SENTENCE,
  FORM_101A_STAY_HEADING_A,
  FORM_101A_STAY_HEADING_B,
  FORM_101A_STAY_SENTENCE_A,
  FORM_101B_STAY_SENTENCE,
} from '../../../../../constants/formText';
import type { PetitionAnswers } from '../../../../../types/api';

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
      <RentQuestion
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

const notice = () => document.querySelector('.eviction-notice');

describe('RentQuestion', () => {
  it('asks the eviction question only under a rent Yes', async () => {
    const user = userEvent.setup();
    const changes: PetitionAnswers[] = [];
    render(<Harness onChange={(next) => changes.push(next)} />);
    expect(screen.getByRole('group', { name: new RegExp(FORM_101_LINE_11_RENT) })).toBeVisible();
    const rent = Array.from(
      document.querySelectorAll<HTMLInputElement>('input[name="rents_residence"]')
    );
    expect(rent.map((r) => r.value)).toEqual(['no', 'yes']);
    expect(rent.some((r) => r.checked)).toBe(false);
    expect(document.querySelector('input[name="eviction_judgment"]')).toBeNull();

    await user.click(radio('rents_residence', 'no'));
    expect(document.querySelector('input[name="eviction_judgment"]')).toBeNull();

    await user.click(radio('rents_residence', 'yes'));
    expect(
      screen.getByRole('group', { name: new RegExp(FORM_101_LINE_11_EVICTION) })
    ).toBeVisible();
    const eviction = Array.from(
      document.querySelectorAll<HTMLInputElement>('input[name="eviction_judgment"]')
    );
    expect(eviction.map((r) => r.value)).toEqual(['no', 'yes']);
    expect(eviction.some((r) => r.checked)).toBe(false);
    await user.click(radio('eviction_judgment', 'no'));
    expect(changes.at(-1)).toEqual({ rents_residence: 'yes', eviction_judgment: 'no' });
  });

  it("says what is still missing in the server's words", async () => {
    // The step's one status region shows this sentence (PF2-T9-6): the block has none of its own
    expect(rentGap({})).toBe(PETITION_GATE_RENTS);
    // A stored eviction Yes under an absent rent answer is still the rent gate (PF2-T9-2)
    expect(rentGap({ eviction_judgment: 'yes' })).toBe(PETITION_GATE_RENTS);
    expect(rentGap({ rents_residence: 'yes' })).toBe(PETITION_GATE_EVICTION);
    expect(rentGap({ rents_residence: 'yes', eviction_judgment: 'no' })).toBeNull();
    expect(rentGap({ rents_residence: 'no' })).toBeNull();
    expect(rentGap({ rents_residence: 'no', eviction_judgment: 'yes' })).toBeNull();

    render(<Harness initial={{ rents_residence: 'yes' }} touched />);
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
    // Touched, the unanswered eviction question says so under its radios
    expect(screen.getByText(NOT_ANSWERED_YET)).toBeInTheDocument();
  });

  it('the Form 101A notice shows only under rent Yes and eviction Yes', async () => {
    const user = userEvent.setup();
    // Rent No keeps a stored eviction Yes, which shows nothing: no radios, no notice (§6.7)
    const { unmount } = render(
      <Harness initial={{ rents_residence: 'no', eviction_judgment: 'yes' }} />
    );
    expect(notice()).toBeNull();
    expect(document.querySelector('input[name="eviction_judgment"]')).toBeNull();
    expect(screen.queryByText(FORM_101_LINE_11_NOTICE)).not.toBeInTheDocument();
    unmount();

    render(<Harness initial={{ rents_residence: 'yes' }} />);
    expect(notice()).toBeNull();
    await user.click(radio('eviction_judgment', 'no'));
    expect(notice()).toBeNull();
    await user.click(radio('eviction_judgment', 'yes'));
    const block = notice() as HTMLElement;
    expect(block).not.toBeNull();

    // In §6.7's order (PF2-T9-4): line 11's lead (owner ruling Q8) and Form 101's line; the lead
    // and Form 101A's opening sentence with its two conditions; DigniFi's 101A sentence; the 101A
    // link; the lead and the stay passage, paragraph (a) with its heading, then (b) with its heading
    // (owner ruling Q9, so "that 30-day period" has its start); DigniFi's 101B sentence; the 101B
    // link
    const pieces = Array.from(block.querySelectorAll('p, li')).map((el) => el.textContent);
    expect(pieces).toEqual([
      FORM_101_LINE_11_LEAD,
      FORM_101_LINE_11_NOTICE,
      FORM_101A_SAYS,
      FORM_101A_SERVICE_SENTENCE,
      ...FORM_101A_SERVICE_CONDITIONS,
      FORM_101A_NOT_YET,
      FORM_101A_LINK,
      FORM_101A_SAYS,
      FORM_101A_STAY_HEADING_A,
      FORM_101A_STAY_SENTENCE_A,
      FORM_101A_STAY_HEADING_B,
      FORM_101B_STAY_SENTENCE,
      FORM_101B_NOT_PREPARED,
      FORM_101B_LINK,
    ]);
    // The forms' own words are marked as quotations, and each lead sits outside its quotation
    const quotes = Array.from(block.querySelectorAll('blockquote'));
    expect(quotes).toHaveLength(3);
    expect(quotes[0].textContent).toBe(FORM_101_LINE_11_NOTICE);
    expect(quotes[2].textContent).toBe(
      FORM_101A_STAY_HEADING_A +
        FORM_101A_STAY_SENTENCE_A +
        FORM_101A_STAY_HEADING_B +
        FORM_101B_STAY_SENTENCE
    );
    // `.info-box` lays its children out as one flex row, so the notice's pieces sit in one child
    // and read top to bottom, not as side-by-side columns
    expect(block.children).toHaveLength(1);

    const link101A = screen.getByRole('link', { name: FORM_101A_LINK });
    expect(link101A).toHaveAttribute('href', COURT_FORM_101A_URL);
    expect(link101A).toHaveAttribute('target', '_blank');
    expect(link101A).toHaveAttribute('rel', 'noopener noreferrer');
    const link101B = screen.getByRole('link', { name: FORM_101B_LINK });
    expect(link101B).toHaveAttribute('href', COURT_FORM_101B_URL);
    expect(link101B).toHaveAttribute('target', '_blank');
    expect(link101B).toHaveAttribute('rel', 'noopener noreferrer');

    // No clerk's number in 4b (F-2): no telephone number anywhere in the block
    expect(block.textContent).not.toMatch(/\(?\d{3}\)?[\s.-]?\d{3}-\d{4}/);

    // Moving rent to No hides the notice and the eviction question, and keeps the answer stored
    await user.click(radio('rents_residence', 'no'));
    expect(notice()).toBeNull();
    expect(document.querySelector('input[name="eviction_judgment"]')).toBeNull();
    expect(screen.getByText(HIDDEN_ANSWERS)).toBeInTheDocument();
  });

  it('keeps an eviction answer under a rent No, hidden, with Show and Delete (T9-eviction-hidden)', async () => {
    const user = userEvent.setup();
    const changes: PetitionAnswers[] = [];
    const stored: PetitionAnswers = { rents_residence: 'no', eviction_judgment: 'yes' };
    // Nothing reappears unannounced (spec line 177): the stored answer is named, not shown
    const { unmount } = render(<Harness initial={stored} />);
    expect(screen.getByText(HIDDEN_ANSWERS)).toBeInTheDocument();
    expect(document.querySelector('input[name="eviction_judgment"]')).toBeNull();
    await user.click(screen.getByRole('button', { name: SHOW_HIDDEN }));
    expect(radio('eviction_judgment', 'yes')).toBeChecked();
    // Shown under the rent No, the answer is there to read or change; the notice stays off (§6.7)
    expect(notice()).toBeNull();
    unmount();

    render(<Harness initial={stored} onChange={(next) => changes.push(next)} />);
    await user.click(screen.getByRole('button', { name: DELETE_HIDDEN }));
    expect(screen.queryByText(HIDDEN_ANSWERS)).not.toBeInTheDocument();
    expect(changes.at(-1)).toEqual({ rents_residence: 'no', eviction_judgment: null });
  });

  it('a rent No with no eviction answer stored shows no hidden-answers line', async () => {
    const user = userEvent.setup();
    render(<Harness initial={{ rents_residence: 'no' }} />);
    expect(screen.queryByText(HIDDEN_ANSWERS)).not.toBeInTheDocument();
    // A rent answered No straight away leaves nothing to hide either
    await user.click(radio('rents_residence', 'yes'));
    await user.click(radio('rents_residence', 'no'));
    expect(screen.queryByText(HIDDEN_ANSWERS)).not.toBeInTheDocument();
  });

  it('has no accessibility violations with the notice open', async () => {
    const { container } = render(
      <Harness initial={{ rents_residence: 'yes', eviction_judgment: 'yes' }} touched />
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
