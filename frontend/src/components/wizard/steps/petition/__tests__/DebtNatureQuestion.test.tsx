import { useState } from 'react';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';
import { DebtNatureQuestion } from '../DebtNatureQuestion';
import { debtNatureGap, supplementLineThreeReached } from '../petitionGaps';
import {
  DEBT_NATURE_KIND_NOT_CHOSEN,
  DEBT_NATURE_LIST_EMPTY,
  DEBT_NATURE_LIST_HEADING,
  DEBT_NATURE_LIST_NOTE,
  DELETE_HIDDEN,
  DUTY_CATEGORY_NONE,
  HIDDEN_ANSWERS,
  MILITARY_540_DAYS,
  MILITARY_FRAMING,
  NOT_ANSWERED_YET,
  PETITION_GATE_DEBT_NATURE,
  PETITION_GATE_DISABLED_VETERAN,
  PETITION_GATE_RESERVIST,
  SHOW_HIDDEN,
  WHAT_DOES_DISABLED_VETERAN_MEAN,
  WHAT_DOES_HOMELAND_DEFENSE_MEAN,
} from '../../../../../constants/copy';
import { DEBT_TYPE_WORDS } from '../../../../../constants/claims';
import {
  FORM_101_LINE_16,
  FORM_101_LINE_16A,
  FORM_101_LINE_16B,
  FORM_101_LINE_16C,
  FORM_122A1SUPP_CATEGORIES,
  FORM_122A1SUPP_LINE_2,
  FORM_122A1SUPP_LINE_2_FOLLOW_UP,
  FORM_122A1SUPP_LINE_3,
  FORM_122A1SUPP_LINE_3_FOLLOW_UP,
  STATUTE_DISABLED_VETERAN,
  STATUTE_DISABLED_VETERAN_CITATION,
  STATUTE_HOMELAND_DEFENSE,
  STATUTE_HOMELAND_DEFENSE_CITATION,
} from '../../../../../constants/formText';
import { PETITION_TEXT_LIMITS } from '../../../../../constants/petitionLimits';
import type { DebtRow, PetitionAnswers } from '../../../../../types/api';

function Harness({
  initial = {},
  touched = false,
  onChange,
  rows = [],
}: {
  initial?: PetitionAnswers;
  touched?: boolean;
  onChange?: (next: PetitionAnswers) => void;
  rows?: DebtRow[];
}) {
  const [answers, setAnswers] = useState<PetitionAnswers>(initial);
  const [left, setLeft] = useState(false);
  return (
    <main>
      <DebtNatureQuestion
        answers={answers}
        onChange={(next) => {
          onChange?.(next);
          setAnswers(next);
        }}
        rows={rows}
        touched={touched || left}
        onLeave={() => setLeft(true)}
      />
      <button type="button">Somewhere else</button>
    </main>
  );
}

const radio = (name: string, value: string) =>
  document.querySelector(`input[name="${name}"][value="${value}"]`) as HTMLInputElement | null;
const radiosNamed = (name: string) =>
  Array.from(
    document.querySelectorAll(`input[type="radio"][name="${name}"]`)
  ) as HTMLInputElement[];
const field = (name: string) =>
  document.querySelector(`input[type="text"][name="${name}"]`) as HTMLInputElement | null;

// A filer whose debts are consumer debts, who isn't a disabled veteran and was called to duty
const CALLED: PetitionAnswers = {
  debt_nature: 'consumer',
  disabled_veteran: 'no',
  reservist: 'yes',
  called_to_duty: 'yes',
};

const startsWith = (words: string) => (name: string) => name.startsWith(words);

const debt = (overrides: Partial<DebtRow>): DebtRow => ({
  _key: `k-${Math.random()}`,
  ...overrides,
});

describe('DebtNatureQuestion', () => {
  it('asks line 16 with nothing chosen', () => {
    render(<Harness touched />);
    expect(screen.getByRole('group', { name: startsWith(FORM_101_LINE_16) })).toBeVisible();
    const choices = radiosNamed('debt_nature');
    expect(choices.map((choice) => choice.value)).toEqual(['consumer', 'business', 'neither']);
    expect(choices.every((choice) => !choice.checked)).toBe(true);
    expect(screen.getByRole('radio', { name: FORM_101_LINE_16A })).toBe(choices[0]);
    expect(screen.getByRole('radio', { name: FORM_101_LINE_16B })).toBe(choices[1]);
    expect(screen.getByRole('radio', { name: FORM_101_LINE_16C })).toBe(choices[2]);
    // An unanswered gate says so once the filer has passed it, and nothing under it is asked yet
    expect(screen.getByText(NOT_ANSWERED_YET)).toBeVisible();
    expect(field('debt_nature_text')).toBeNull();
    expect(radiosNamed('disabled_veteran')).toHaveLength(0);
  });

  it("asks line 16c's words only under neither, within its box's cap", async () => {
    render(<Harness />);
    await userEvent.click(radio('debt_nature', 'neither')!);
    const box = field('debt_nature_text')!;
    expect(box).toHaveAttribute('maxLength', String(PETITION_TEXT_LIMITS.debt_nature_text));
    expect(radiosNamed('disabled_veteran')).toHaveLength(0);
  });

  it('asks the military questions only under consumer', async () => {
    render(<Harness />);
    expect(screen.queryByText(MILITARY_FRAMING)).not.toBeInTheDocument();
    await userEvent.click(radio('debt_nature', 'consumer')!);
    expect(screen.getByText(MILITARY_FRAMING)).toBeVisible();
    expect(screen.getByRole('group', { name: startsWith(FORM_122A1SUPP_LINE_2) })).toBeVisible();
    expect(radiosNamed('disabled_veteran')).toHaveLength(2);
    expect(radiosNamed('disabled_veteran').every((choice) => !choice.checked)).toBe(true);
    expect(radiosNamed('reservist')).toHaveLength(2);
    await userEvent.click(radio('debt_nature', 'business')!);
    expect(screen.queryByText(MILITARY_FRAMING)).not.toBeInTheDocument();
    expect(radiosNamed('disabled_veteran')).toHaveLength(0);
    expect(radiosNamed('reservist')).toHaveLength(0);
  });

  it('hides line 3 under line 2 Yes and Yes and keeps its answers behind one line', async () => {
    // The Supp sends a disabled veteran whose debts began on duty straight to box 1 (R-D2), so
    // line 3 isn't asked, and a Reservist answer given earlier stays stored but hidden
    render(
      <Harness
        initial={{
          debt_nature: 'consumer',
          disabled_veteran: 'yes',
          debts_on_duty: 'yes',
          reservist: 'yes',
          called_to_duty: 'no',
        }}
      />
    );
    expect(radiosNamed('reservist')).toHaveLength(0);
    expect(radiosNamed('called_to_duty')).toHaveLength(0);
    expect(screen.queryByRole('group', { name: startsWith(FORM_122A1SUPP_LINE_3) })).toBeNull();
    expect(screen.getAllByText(HIDDEN_ANSWERS)).toHaveLength(1);
    // Line 2's follow-up answered No reaches line 3 again, with the stored answers in place
    await userEvent.click(radio('debts_on_duty', 'no')!);
    expect(radio('reservist', 'yes')).toBeChecked();
    expect(screen.queryByText(HIDDEN_ANSWERS)).not.toBeInTheDocument();
  });

  it("asks line 3 while line 2's follow-up is unanswered", () => {
    render(<Harness initial={{ debt_nature: 'consumer', disabled_veteran: 'yes' }} />);
    expect(radiosNamed('debts_on_duty')).toHaveLength(2);
    expect(radiosNamed('reservist')).toHaveLength(2);
  });

  it('lists the debts by kind with no sum or count', () => {
    const rows = [
      debt({ id: 1, creditor_name: 'Demo Card Co', debt_type: 'credit_card', amount_owed: 1200 }),
      debt({ id: 2, creditor_name: 'Demo Clinic', debt_type: 'medical', amount_owed: 300.5 }),
      debt({ id: 3, creditor_name: 'Demo Store Card', debt_type: 'credit_card', amount_owed: 80 }),
      debt({ creditor_name: 'Demo Lender', amount_owed: 40 }),
      // An empty new row stays in the browser, as the step's save leaves it out
      debt({}),
    ];
    render(<Harness rows={rows} />);
    const list = screen.getByRole('region', { name: DEBT_NATURE_LIST_HEADING });
    expect(within(list).getByText(DEBT_NATURE_LIST_NOTE)).toBeVisible();
    const headings = within(list)
      .getAllByRole('heading')
      .map((heading) => heading.textContent);
    expect(headings).toEqual([
      DEBT_NATURE_LIST_HEADING,
      DEBT_TYPE_WORDS.credit_card,
      DEBT_TYPE_WORDS.medical,
      DEBT_NATURE_KIND_NOT_CHOSEN,
    ]);
    for (const heading of headings) expect(heading).not.toMatch(/\d/);
    const items = within(list)
      .getAllByRole('listitem')
      .map((item) => item.textContent);
    expect(items).toEqual([
      'Demo Card Co: 1,200.00',
      'Demo Store Card: 80.00',
      'Demo Clinic: 300.50',
      'Demo Lender: 40.00',
    ]);
    // No total, no dollar sign, no count of rows or kinds
    expect(list.textContent).not.toMatch(/\$/);
    expect(list.textContent).not.toContain('1,620.50');
    expect(list.textContent).not.toContain('1,280.00');
  });

  it('lists a stored 0 with no figure, since 0 means not given yet', () => {
    // B29 (T8-R3): the amount box shows a stored 0 as empty, so the list shows no "0.00" either
    const rows = [
      debt({ id: 1, creditor_name: 'Demo Card Co', debt_type: 'credit_card', amount_owed: 0 }),
      debt({ id: 2, creditor_name: 'Demo Clinic', debt_type: 'credit_card', amount_owed: 25 }),
    ];
    render(<Harness rows={rows} />);
    const list = screen.getByRole('region', { name: DEBT_NATURE_LIST_HEADING });
    const items = within(list)
      .getAllByRole('listitem')
      .map((item) => item.textContent);
    expect(items).toEqual(['Demo Card Co', 'Demo Clinic: 25.00']);
    expect(list.textContent).not.toMatch(/(^|[^,\d])0\.00/);
  });

  it('says no amounts are listed when there are none', () => {
    render(<Harness rows={[debt({})]} />);
    const list = screen.getByRole('region', { name: DEBT_NATURE_LIST_HEADING });
    expect(within(list).getByText(DEBT_NATURE_LIST_EMPTY)).toBeVisible();
    expect(within(list).queryAllByRole('listitem')).toHaveLength(0);
  });

  it('names each definition by its term', async () => {
    render(<Harness initial={{ debt_nature: 'consumer', disabled_veteran: 'yes' }} />);
    const veteran = screen.getByText(WHAT_DOES_DISABLED_VETERAN_MEAN);
    const homeland = screen.getByText(WHAT_DOES_HOMELAND_DEFENSE_MEAN);
    expect(veteran.tagName).toBe('SUMMARY');
    expect(homeland.tagName).toBe('SUMMARY');
    expect(WHAT_DOES_DISABLED_VETERAN_MEAN).not.toBe(WHAT_DOES_HOMELAND_DEFENSE_MEAN);
    await userEvent.click(veteran);
    expect(screen.getByText(STATUTE_DISABLED_VETERAN)).toBeVisible();
    expect(screen.getByText(STATUTE_DISABLED_VETERAN_CITATION)).toBeVisible();
    await userEvent.click(homeland);
    expect(screen.getByText(STATUTE_HOMELAND_DEFENSE)).toBeVisible();
    expect(screen.getByText(STATUTE_HOMELAND_DEFENSE_CITATION)).toBeVisible();
  });

  it('explains homeland defense activity under each follow-up that names it', () => {
    // T8-R2: line 2's follow-up and line 3's both name "homeland defense activity"
    const { unmount } = render(<Harness initial={CALLED} />);
    const calledGroup = screen.getByRole('group', {
      name: startsWith(FORM_122A1SUPP_LINE_3_FOLLOW_UP),
    });
    expect(within(calledGroup).getByText(WHAT_DOES_HOMELAND_DEFENSE_MEAN).tagName).toBe('SUMMARY');
    expect(screen.getAllByText(WHAT_DOES_HOMELAND_DEFENSE_MEAN)).toHaveLength(1);
    unmount();

    render(<Harness initial={{ ...CALLED, disabled_veteran: 'yes', debts_on_duty: 'no' }} />);
    const onDutyGroup = screen.getByRole('group', {
      name: startsWith(FORM_122A1SUPP_LINE_2_FOLLOW_UP),
    });
    expect(within(onDutyGroup).getByText(WHAT_DOES_HOMELAND_DEFENSE_MEAN)).toBeInTheDocument();
    expect(screen.getAllByText(WHAT_DOES_HOMELAND_DEFENSE_MEAN)).toHaveLength(2);
  });

  it("names each box by its own words first, then the line's question", async () => {
    // T8-R1: the accessible name starts with the visible label, verbatim (WCAG 2.5.3)
    const { unmount } = render(<Harness initial={{ debt_nature: 'neither' }} />);
    expect(screen.getByRole('textbox', { name: `${FORM_101_LINE_16C} ${FORM_101_LINE_16}` })).toBe(
      field('debt_nature_text')
    );
    unmount();

    render(<Harness initial={{ ...CALLED, duty_category: '2' }} />);
    expect(
      screen.getByRole('textbox', {
        name: `${FORM_122A1SUPP_CATEGORIES['2']} ${FORM_122A1SUPP_LINE_3_FOLLOW_UP}`,
      })
    ).toBe(field('duty_released_on'));
    await userEvent.click(radio('duty_category', '4')!);
    expect(
      screen.getByRole('textbox', {
        name: `${FORM_122A1SUPP_CATEGORIES['4']} ${FORM_122A1SUPP_LINE_3_FOLLOW_UP}`,
      })
    ).toBe(field('duty_ended_on'));
  });

  it("Delete clears a hidden block's answers", async () => {
    // A filer who answered the military questions, then chose business debts: the answers stay
    // stored behind one line, and Delete clears every one of them
    const onChange = vi.fn();
    render(
      <Harness
        onChange={onChange}
        initial={{
          debt_nature: 'business',
          debt_nature_text: '',
          disabled_veteran: 'no',
          reservist: 'yes',
          called_to_duty: 'yes',
          duty_category: '2',
          duty_released_on: '01/02/2026',
        }}
      />
    );
    expect(radiosNamed('disabled_veteran')).toHaveLength(0);
    expect(screen.getAllByText(HIDDEN_ANSWERS)).toHaveLength(1);
    await userEvent.click(screen.getByRole('button', { name: DELETE_HIDDEN }));
    expect(onChange).toHaveBeenLastCalledWith({
      debt_nature: 'business',
      debt_nature_text: '',
      disabled_veteran: null,
      debts_on_duty: null,
      reservist: null,
      called_to_duty: null,
      duty_category: null,
      duty_released_on: null,
      duty_ended_on: null,
    });
    expect(screen.queryByText(HIDDEN_ANSWERS)).not.toBeInTheDocument();
  });

  it("keeps line 16c's words behind one line under consumer", async () => {
    render(<Harness initial={{ debt_nature: 'consumer', debt_nature_text: 'Demo words' }} />);
    expect(field('debt_nature_text')).toBeNull();
    await userEvent.click(screen.getAllByRole('button', { name: SHOW_HIDDEN })[0]);
    expect(field('debt_nature_text')).toHaveValue('Demo words');
  });

  it("keeps line 2's follow-up behind one line under No", async () => {
    const onChange = vi.fn();
    render(
      <Harness
        onChange={onChange}
        initial={{ debt_nature: 'consumer', disabled_veteran: 'no', debts_on_duty: 'yes' }}
      />
    );
    expect(radiosNamed('debts_on_duty')).toHaveLength(0);
    expect(screen.getAllByText(HIDDEN_ANSWERS)).toHaveLength(1);
    await userEvent.click(screen.getByRole('button', { name: SHOW_HIDDEN }));
    expect(radio('debts_on_duty', 'yes')).toBeChecked();
    // A new answer to line 2 hides it again; Delete then clears it alone
    await userEvent.click(radio('disabled_veteran', 'yes')!);
    await userEvent.click(radio('disabled_veteran', 'no')!);
    expect(radiosNamed('debts_on_duty')).toHaveLength(0);
    await userEvent.click(screen.getByRole('button', { name: DELETE_HIDDEN }));
    expect(onChange).toHaveBeenLastCalledWith({
      debt_nature: 'consumer',
      disabled_veteran: 'no',
      debts_on_duty: null,
    });
  });

  it("keeps line 3's follow-ups behind one line under No, and Delete clears only them", async () => {
    // A Reservist answer changed to No: the duty answers stay stored and in reach (4d-R15)
    const onChange = vi.fn();
    render(
      <Harness
        onChange={onChange}
        initial={{
          debt_nature: 'consumer',
          disabled_veteran: 'no',
          reservist: 'no',
          called_to_duty: 'yes',
          duty_category: '2',
          duty_released_on: '01/02/2026',
        }}
      />
    );
    expect(radiosNamed('called_to_duty')).toHaveLength(0);
    expect(radiosNamed('duty_category')).toHaveLength(0);
    expect(screen.getAllByText(HIDDEN_ANSWERS)).toHaveLength(1);
    await userEvent.click(screen.getByRole('button', { name: SHOW_HIDDEN }));
    expect(radio('called_to_duty', 'yes')).toBeChecked();
    expect(radio('duty_category', '2')).toBeChecked();
    expect(field('duty_released_on')).toHaveValue('01/02/2026');
    // A new answer to line 3 hides them again
    await userEvent.click(radio('reservist', 'yes')!);
    await userEvent.click(radio('reservist', 'no')!);
    expect(radiosNamed('called_to_duty')).toHaveLength(0);
    expect(screen.getAllByText(HIDDEN_ANSWERS)).toHaveLength(1);
    await userEvent.click(screen.getByRole('button', { name: DELETE_HIDDEN }));
    expect(onChange).toHaveBeenLastCalledWith({
      debt_nature: 'consumer',
      disabled_veteran: 'no',
      reservist: 'no',
      called_to_duty: null,
      duty_category: null,
      duty_released_on: null,
      duty_ended_on: null,
    });
    expect(screen.queryByText(HIDDEN_ANSWERS)).not.toBeInTheDocument();
  });

  it('keeps the duty categories behind one line under No, and Delete clears only them', async () => {
    // Called to duty changed to No: the category and its date stay stored and in reach (4d-R15)
    const onChange = vi.fn();
    render(
      <Harness
        onChange={onChange}
        initial={{
          ...CALLED,
          called_to_duty: 'no',
          duty_category: '4',
          duty_ended_on: '03/04/2026',
        }}
      />
    );
    expect(radiosNamed('called_to_duty')).toHaveLength(2);
    expect(radiosNamed('duty_category')).toHaveLength(0);
    expect(screen.getAllByText(HIDDEN_ANSWERS)).toHaveLength(1);
    await userEvent.click(screen.getByRole('button', { name: SHOW_HIDDEN }));
    expect(radio('duty_category', '4')).toBeChecked();
    expect(field('duty_ended_on')).toHaveValue('03/04/2026');
    // A new answer to the follow-up hides them again
    await userEvent.click(radio('called_to_duty', 'yes')!);
    await userEvent.click(radio('called_to_duty', 'no')!);
    expect(radiosNamed('duty_category')).toHaveLength(0);
    expect(screen.getAllByText(HIDDEN_ANSWERS)).toHaveLength(1);
    await userEvent.click(screen.getByRole('button', { name: DELETE_HIDDEN }));
    expect(onChange).toHaveBeenLastCalledWith({
      debt_nature: 'consumer',
      disabled_veteran: 'no',
      reservist: 'yes',
      called_to_duty: 'no',
      duty_category: null,
      duty_released_on: null,
      duty_ended_on: null,
    });
    expect(screen.queryByText(HIDDEN_ANSWERS)).not.toBeInTheDocument();
  });

  it("Delete under line 2 Yes and Yes clears line 3's answers and keeps line 2's", async () => {
    // Line 2's answers send the filer to box 1, so Delete must never reopen one of them
    const onChange = vi.fn();
    render(
      <Harness
        onChange={onChange}
        initial={{
          debt_nature: 'consumer',
          disabled_veteran: 'yes',
          debts_on_duty: 'yes',
          reservist: 'yes',
          called_to_duty: 'yes',
          duty_category: '2',
          duty_released_on: '01/02/2026',
        }}
      />
    );
    expect(screen.getAllByText(HIDDEN_ANSWERS)).toHaveLength(1);
    await userEvent.click(screen.getByRole('button', { name: DELETE_HIDDEN }));
    expect(onChange).toHaveBeenLastCalledWith({
      debt_nature: 'consumer',
      disabled_veteran: 'yes',
      debts_on_duty: 'yes',
      reservist: null,
      called_to_duty: null,
      duty_category: null,
      duty_released_on: null,
      duty_ended_on: null,
    });
    expect(screen.queryByText(HIDDEN_ANSWERS)).not.toBeInTheDocument();
  });

  it('hides a block Show opened again once an outer answer hides the block around it', async () => {
    // Show opened line 3's follow-up under a Reservist No; line 2 Yes and Yes then hides line 3,
    // and its No brings line 3 back with the follow-up behind its line again, not open (4d-R15)
    render(
      <Harness
        initial={{
          debt_nature: 'consumer',
          disabled_veteran: 'no',
          reservist: 'no',
          called_to_duty: 'yes',
        }}
      />
    );
    await userEvent.click(screen.getByRole('button', { name: SHOW_HIDDEN }));
    expect(radio('called_to_duty', 'yes')).toBeChecked();

    await userEvent.click(radio('disabled_veteran', 'yes')!);
    await userEvent.click(radio('debts_on_duty', 'yes')!);
    expect(radiosNamed('reservist')).toHaveLength(0);
    await userEvent.click(radio('debts_on_duty', 'no')!);

    expect(radio('reservist', 'no')).toBeChecked();
    expect(radiosNamed('called_to_duty')).toHaveLength(0);
    expect(screen.getAllByText(HIDDEN_ANSWERS)).toHaveLength(1);
    expect(screen.getByRole('button', { name: SHOW_HIDDEN })).toBeVisible();
  });

  it('marks line 3 required only where the Supp reaches it', async () => {
    // Under line 2 Yes and Yes, Show opens line 3 to be read or changed: Continue doesn't hold it,
    // so it carries no required mark and no "Not answered yet"
    render(
      <Harness
        touched
        initial={{
          debt_nature: 'consumer',
          disabled_veteran: 'yes',
          debts_on_duty: 'yes',
          called_to_duty: 'no',
        }}
      />
    );
    await userEvent.click(screen.getByRole('button', { name: SHOW_HIDDEN }));
    const lineThree = screen.getByRole('group', { name: startsWith(FORM_122A1SUPP_LINE_3) });
    expect(within(lineThree).getByRole('radio', { name: 'No' })).not.toHaveAttribute(
      'aria-required'
    );
    // The legend is the question alone, with no required mark after it
    expect(lineThree.querySelector('legend')!.textContent).toBe(FORM_122A1SUPP_LINE_3);
    expect(screen.queryByText(NOT_ANSWERED_YET)).not.toBeInTheDocument();
  });

  it('offers "none applies" after the four categories and asks no date under it', async () => {
    render(<Harness initial={CALLED} />);
    const categories = radiosNamed('duty_category');
    expect(categories.map((choice) => choice.value)).toEqual(['1', '2', '3', '4', 'none']);
    expect(categories.every((choice) => !choice.checked)).toBe(true);
    expect(screen.getByRole('radio', { name: DUTY_CATEGORY_NONE })).toBe(categories[4]);
    expect(screen.getByRole('radio', { name: FORM_122A1SUPP_CATEGORIES['1'] })).toBe(categories[0]);
    expect(screen.getByText(MILITARY_540_DAYS)).toBeVisible();
    expect(field('duty_released_on')).toBeNull();
    expect(field('duty_ended_on')).toBeNull();

    await userEvent.click(radio('duty_category', '2')!);
    const released = field('duty_released_on')!;
    await userEvent.type(released, '01022026');
    expect(released).toHaveValue('01/02/2026');
    expect(field('duty_ended_on')).toBeNull();

    await userEvent.click(radio('duty_category', '4')!);
    expect(field('duty_ended_on')).toBeVisible();

    await userEvent.click(radio('duty_category', 'none')!);
    expect(field('duty_released_on')).toBeNull();
    expect(field('duty_ended_on')).toBeNull();
    // The date typed under category 2 stays stored, behind one line
    expect(screen.getAllByText(HIDDEN_ANSWERS)).toHaveLength(1);
  });

  it('has no accessibility violations with every question shown', async () => {
    const { container } = render(
      <Harness
        touched
        initial={{ ...CALLED, disabled_veteran: 'yes', debts_on_duty: 'no', duty_category: '2' }}
        rows={[debt({ id: 1, creditor_name: 'Demo Card Co', debt_type: 'credit_card' })]}
      />
    );
    const results = await axe(container, { rules: { 'color-contrast': { enabled: false } } });
    expect(results).toHaveNoViolations();
  });
});

describe("Amounts Owed's gates in the browser", () => {
  it('debtNatureGap returns the three gates in order and ignores details', () => {
    expect(debtNatureGap({})).toBe(PETITION_GATE_DEBT_NATURE);
    expect(debtNatureGap({ debt_nature: 'consumer' })).toBe(PETITION_GATE_DISABLED_VETERAN);
    expect(debtNatureGap({ debt_nature: 'consumer', disabled_veteran: 'no' })).toBe(
      PETITION_GATE_RESERVIST
    );
    // Line 2's follow-up still open reaches line 3 (F2); Yes and Yes doesn't
    expect(debtNatureGap({ debt_nature: 'consumer', disabled_veteran: 'yes' })).toBe(
      PETITION_GATE_RESERVIST
    );
    expect(
      debtNatureGap({ debt_nature: 'consumer', disabled_veteran: 'yes', debts_on_duty: 'yes' })
    ).toBeNull();
    // Details never hold Continue: a blank 16c, an open follow-up, an unchosen category
    expect(debtNatureGap({ debt_nature: 'neither' })).toBeNull();
    expect(debtNatureGap({ debt_nature: 'business' })).toBeNull();
    expect(debtNatureGap({ ...CALLED, disabled_veteran: 'no' })).toBeNull();
    expect(
      debtNatureGap({ debt_nature: 'consumer', disabled_veteran: 'no', reservist: 'yes' })
    ).toBeNull();
  });

  it('supplementLineThreeReached follows the Supp: consumer, and not line 2 Yes and Yes', () => {
    expect(supplementLineThreeReached({})).toBe(false);
    expect(supplementLineThreeReached({ debt_nature: 'business' })).toBe(false);
    expect(supplementLineThreeReached({ debt_nature: 'consumer' })).toBe(true);
    expect(supplementLineThreeReached({ debt_nature: 'consumer', disabled_veteran: 'yes' })).toBe(
      true
    );
    expect(
      supplementLineThreeReached({
        debt_nature: 'consumer',
        disabled_veteran: 'yes',
        debts_on_duty: 'yes',
      })
    ).toBe(false);
  });
});

describe("the statutes' words under What does this mean?", () => {
  // Pinned word for word (owner-copy §6): there is no template to pin them to. Re-checked
  // against uscode.house.gov on 2026-11-24.
  it('quotes 38 U.S.C. § 3741(1) and 32 U.S.C. § 901(1) exactly', () => {
    expect(STATUTE_DISABLED_VETERAN_CITATION).toBe('38 U.S.C. § 3741(1)');
    expect(STATUTE_DISABLED_VETERAN).toBe(
      'The term “disabled veteran” means (A) a veteran who is entitled to compensation under laws administered by the Secretary for a disability rated at 30 percent or more, or (B) a veteran whose discharge or release from active duty was for a disability incurred or aggravated in line of duty.'
    );
    expect(STATUTE_HOMELAND_DEFENSE_CITATION).toBe('32 U.S.C. § 901(1)');
    expect(STATUTE_HOMELAND_DEFENSE).toBe(
      'The term “homeland defense activity” means an activity undertaken for the military protection of the territory or domestic population of the United States, or of infrastructure or other assets of the United States determined by the Secretary of Defense as being critical to national security, from a threat or aggression against the United States.'
    );
  });
});
