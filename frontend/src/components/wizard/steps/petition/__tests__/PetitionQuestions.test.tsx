import { useState } from 'react';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import { axe } from 'vitest-axe';
import { PetitionQuestions } from '../PetitionQuestions';
import { firstPetitionGap } from '../petitionGaps';
import {
  CLERK_PHONE_WESTERN,
  HIDDEN_ANSWERS,
  HIDDEN_ROWS_MANY,
  HIDDEN_ROWS_ONE,
  ITIN_SAVED,
  LINE_12_FEEDS_107,
  OTHER_SSN_SAVED,
  PETITION_ADD_OTHER_NAME,
  PETITION_ADD_PRIOR_CASE,
  PETITION_DETAIL_ITIN,
  PETITION_DETAIL_ITIN_NINE,
  PETITION_GATE_ITIN,
  PETITION_GATE_OTHER_NAMES,
  PUBLIC_RECORD_NOTICE,
  REPLACE_SAVED,
  VENUE_DIVISION_EASTERN,
  VENUE_DIVISION_WESTERN,
} from '../../../../../constants/copy';
import {
  FORM_101_LINE_12_NAME,
  FORM_101_LINE_2_INSTRUCTIONS,
  FORM_101_VENUE_CHOICES,
} from '../../../../../constants/formText';
import {
  PETITION_ROW_CELL_MAX_LENGTH,
  PETITION_TEXT_LIMITS,
} from '../../../../../constants/petitionLimits';
import type { PetitionAnswers } from '../../../../../types/api';

const GATES = [
  'other_names_answer',
  'itin_answer',
  'other_ssn_answer',
  'mailing_answer',
  'prior_bankruptcy_answer',
  'pending_case_answer',
  'sole_proprietor_answer',
] as const;

const EVERY_YES: PetitionAnswers = Object.fromEntries(GATES.map((gate) => [gate, 'yes']));

/** The block with the wizard's state around it, so typing and pressing behave as on step 1 */
function Harness({
  initial = {},
  division = null,
  onChange,
  onSecretChange,
}: {
  initial?: PetitionAnswers;
  division?: 'Eastern' | 'Western' | null;
  onChange?: (next: PetitionAnswers) => void;
  onSecretChange?: (key: 'itin' | 'other_ssn', value: string) => void;
}) {
  const [answers, setAnswers] = useState<PetitionAnswers>(initial);
  const [secrets, setSecrets] = useState<{ itin?: string; other_ssn?: string }>({});
  return (
    <main>
      <PetitionQuestions
        answers={answers}
        onChange={(next) => {
          onChange?.(next);
          setAnswers(next);
        }}
        pendingSecrets={secrets}
        onSecretChange={(key, value) => {
          onSecretChange?.(key, value);
          setSecrets((current) => ({ ...current, [key]: value }));
        }}
        division={division}
      />
    </main>
  );
}

const radio = (name: string, value: string) =>
  document.querySelector(`input[name="${name}"][value="${value}"]`) as HTMLInputElement;

describe('PetitionQuestions', () => {
  it('offers every yes/no unanswered with No before Yes and nothing checked', () => {
    render(<Harness />);
    for (const gate of GATES) {
      const radios = Array.from(
        document.querySelectorAll<HTMLInputElement>(`input[type="radio"][name="${gate}"]`)
      );
      expect(
        radios.map((r) => r.value),
        gate
      ).toEqual(['no', 'yes']);
      expect(
        radios.some((r) => r.checked),
        gate
      ).toBe(false);
    }
    // Line 6 and line 12's kind are choices, never pre-selected either
    expect(document.querySelectorAll('input[name="venue_choice"]:checked')).toHaveLength(0);
    // Nothing says "Not answered yet" before the filer has touched the block
    expect(screen.queryByText('Not answered yet')).not.toBeInTheDocument();
  });

  it('names every control by its PetitionAnswers key, and a row cell by list, place and cell', async () => {
    // Tasks 9 and 11 and E2E find the boxes by these names (PF2-T8-5)
    render(
      <Harness
        initial={{
          ...EVERY_YES,
          venue_choice: 'other',
          other_names: [{ _key: 'a', first: 'Demo' }],
          other_business_names: [{ _key: 'b', name: 'Demo Shop' }],
          prior_cases: [{ _key: 'c', district: 'Northern Illinois' }],
          pending_cases: [{ _key: 'd', debtor: 'Demo Partner' }],
        }}
      />
    );
    const names = Array.from(document.querySelectorAll('input, select'), (el) =>
      el.getAttribute('name')
    );
    expect(new Set(names)).toEqual(
      new Set([
        'name_suffix',
        ...GATES,
        'other_names_0_first',
        'other_names_0_middle',
        'other_names_0_last',
        'other_business_names_0_name',
        'itin',
        'other_ssn',
        'ein',
        'mailing_street',
        'mailing_po_box',
        'mailing_city',
        'mailing_state',
        'mailing_zip',
        'venue_choice',
        'venue_reason',
        'prior_cases_0_district',
        'prior_cases_0_filed_on',
        'prior_cases_0_case_number',
        'pending_cases_0_debtor',
        'pending_cases_0_relationship',
        'pending_cases_0_district',
        'pending_cases_0_filed_on',
        'pending_cases_0_case_number',
        'business_name',
        'business_street',
        'business_city',
        'business_state',
        'business_zip',
        'business_kind',
      ])
    );
  });

  it('shows the rows and texts only under a Yes and keeps them stored under a No', async () => {
    const onChange = vi.fn();
    render(
      <Harness
        initial={{
          other_names_answer: 'yes',
          other_names: [
            { _key: 'a', first: 'Demo', last: 'Maiden' },
            { _key: 'b', first: 'Demo', last: 'Former' },
          ],
        }}
        onChange={onChange}
      />
    );
    expect(screen.getByDisplayValue('Maiden')).toBeInTheDocument();

    await userEvent.click(radio('other_names_answer', 'no'));
    expect(screen.queryByDisplayValue('Maiden')).not.toBeInTheDocument();
    expect(screen.getByText(HIDDEN_ROWS_MANY.replace('{count}', '2'))).toBeInTheDocument();
    // The No never empties the list: the rows stay stored, and print nothing
    for (const [next] of onChange.mock.calls) {
      expect((next as PetitionAnswers).other_names).toHaveLength(2);
    }

    await userEvent.click(screen.getByRole('button', { name: 'Show' }));
    expect(screen.getByDisplayValue('Maiden')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Former')).toBeInTheDocument();
  });

  it('a single hidden row says so in the singular, and Delete removes it', async () => {
    const onChange = vi.fn();
    render(
      <Harness
        initial={{ prior_bankruptcy_answer: 'no', prior_cases: [{ _key: 'a', district: 'Demo' }] }}
        onChange={onChange}
      />
    );
    expect(screen.getByText(HIDDEN_ROWS_ONE)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Delete' }));
    expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({ prior_cases: null }));
    expect(screen.queryByText(HIDDEN_ROWS_ONE)).not.toBeInTheDocument();
  });

  it('a mailing address kept under a No is announced, and Show and Delete reach it', async () => {
    // PF2-U1: nothing reappears unannounced on a later Yes
    const onChange = vi.fn();
    render(
      <Harness
        initial={{ mailing_answer: 'no', mailing_street: '9 Demo Lane', mailing_city: 'Demoville' }}
        onChange={onChange}
      />
    );
    expect(screen.getByText(HIDDEN_ANSWERS)).toBeInTheDocument();
    expect(screen.queryByDisplayValue('9 Demo Lane')).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Show' }));
    expect(screen.getByDisplayValue('9 Demo Lane')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Demoville')).toBeInTheDocument();
    // Shown, not answered: the No stays the filer's
    expect(radio('mailing_answer', 'no')).toBeChecked();
    expect(onChange).not.toHaveBeenCalled();
  });

  it('Delete clears every hidden mailing answer', async () => {
    const onChange = vi.fn();
    render(
      <Harness
        initial={{ mailing_answer: 'no', mailing_street: '9 Demo Lane', mailing_zip: '60601' }}
        onChange={onChange}
      />
    );
    await userEvent.click(screen.getByRole('button', { name: 'Delete' }));
    expect(onChange).toHaveBeenLastCalledWith(
      expect.objectContaining({
        mailing_street: null,
        mailing_po_box: null,
        mailing_city: null,
        mailing_state: null,
        mailing_zip: null,
      })
    );
    expect(screen.queryByText(HIDDEN_ANSWERS)).not.toBeInTheDocument();
  });

  it("the first gate's sentence is the server's", async () => {
    expect(firstPetitionGap({})).toBe(PETITION_GATE_OTHER_NAMES);
    expect(firstPetitionGap({ other_names_answer: 'no' })).toBe(PETITION_GATE_ITIN);
    expect(firstPetitionGap(Object.fromEntries(GATES.map((gate) => [gate, 'no'])))).toBeNull();

    render(<Harness />);
    const status = screen.getByRole('status');
    // Mounted and empty until the filer touches the block (PF2-T8-10)
    expect(status).toBeEmptyDOMElement();
    await userEvent.click(radio('other_names_answer', 'no'));
    expect(status).toHaveTextContent(PETITION_GATE_ITIN);
    expect(screen.getAllByText('Not answered yet').length).toBe(GATES.length - 1);
  });

  it('leaving the block unanswered says what is missing, and moving within it does not', async () => {
    // PF2-T8-10: touched is an answer set or focus gone from the block, so a filer who tabs
    // through answering nothing sees why Continue waits
    render(
      <>
        <Harness />
        <button type="button">Outside</button>
      </>
    );
    const status = screen.getByRole('status');
    await userEvent.click(screen.getByRole('textbox', { name: /Suffix/ }));
    await userEvent.click(screen.getByRole('textbox', { name: /Employer Identification/ }));
    expect(status).toBeEmptyDOMElement();
    expect(screen.queryByText('Not answered yet')).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Outside' }));
    expect(status).toHaveTextContent(PETITION_GATE_OTHER_NAMES);
    expect(screen.getAllByText('Not answered yet')).toHaveLength(GATES.length);
  });

  it("line 2's instructions come with the question, before any answer", () => {
    // A maiden, married or trade name counts: the filer reads so before choosing No
    render(<Harness />);
    const question = radio('other_names_answer', 'no').closest('fieldset') as HTMLElement;
    expect(question).toHaveTextContent(FORM_101_LINE_2_INSTRUCTIONS);
    expect(question).toHaveTextContent(/married or maiden names/);
  });

  it('an ITIN is masked, sent through onSecretChange and shown as saved afterwards', async () => {
    const onSecretChange = vi.fn();
    const { unmount } = render(
      <Harness initial={{ itin_answer: 'yes' }} onSecretChange={onSecretChange} />
    );
    const box = screen.getByRole('textbox', { name: /ITIN/ });
    await userEvent.type(box, '900 70 1234');
    // Visible digits and dashes, sent as digits
    expect(box).toHaveValue('900-70-1234');
    expect(onSecretChange).toHaveBeenLastCalledWith('itin', '900701234');
    unmount();

    // Once saved, the server says only that one is saved (F-3): no digits come back
    render(<Harness initial={{ itin_answer: 'yes', itin_saved: true }} />);
    expect(screen.getByText(ITIN_SAVED)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: REPLACE_SAVED })).toBeInTheDocument();
    expect(screen.queryByRole('textbox', { name: /ITIN/ })).not.toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/\d{4}/);
    await userEvent.click(screen.getByRole('button', { name: REPLACE_SAVED }));
    expect(screen.getByRole('textbox', { name: /ITIN/ })).toHaveValue('');
  });

  it('another Social Security number is masked and sent through onSecretChange as digits', async () => {
    const onSecretChange = vi.fn();
    render(<Harness initial={{ other_ssn_answer: 'yes' }} onSecretChange={onSecretChange} />);
    const box = document.querySelector('input[name="other_ssn"]') as HTMLInputElement;
    await userEvent.type(box, '900 12 3456');
    expect(box).toHaveValue('900-12-3456');
    expect(onSecretChange).toHaveBeenLastCalledWith('other_ssn', '900123456');
  });

  it('a replaced number shows as saved again once the save takes it', async () => {
    // The wizard clears the typed digits when the save carrying them succeeds (PF2-T8-6)
    const props = {
      answers: { itin_answer: 'yes', itin_saved: true } as PetitionAnswers,
      onChange: vi.fn(),
      onSecretChange: vi.fn(),
      division: null,
    };
    const { rerender } = render(<PetitionQuestions {...props} pendingSecrets={{}} />);
    await userEvent.click(screen.getByRole('button', { name: REPLACE_SAVED }));
    await userEvent.type(screen.getByRole('textbox', { name: /ITIN/ }), '9');
    rerender(<PetitionQuestions {...props} pendingSecrets={{ itin: '900701234' }} />);
    expect(screen.getByRole('textbox', { name: /ITIN/ })).toHaveValue('900-70-1234');
    rerender(<PetitionQuestions {...props} pendingSecrets={{}} />);
    expect(screen.getByText(ITIN_SAVED)).toBeInTheDocument();
    expect(screen.queryByRole('textbox', { name: /ITIN/ })).not.toBeInTheDocument();
  });

  it('a box emptied after Replace stays open while the filer types', async () => {
    render(<Harness initial={{ itin_answer: 'yes', itin_saved: true }} />);
    await userEvent.click(screen.getByRole('button', { name: REPLACE_SAVED }));
    const box = screen.getByRole('textbox', { name: /ITIN/ });
    await userEvent.type(box, '90');
    await userEvent.clear(box);
    expect(screen.getByRole('textbox', { name: /ITIN/ })).toHaveValue('');
    expect(screen.queryByText(ITIN_SAVED)).not.toBeInTheDocument();
  });

  it('nine digits that are no ITIN stay in the box with the server sentence beside them', async () => {
    // PF2-U2: an ITIN starts with 9; any other number would print blank on Forms 101 and 121.
    // Owner ruling Q7: the sentence says why nine digits aren't one, not "type your 9-digit ITIN"
    render(<Harness initial={{ itin_answer: 'yes' }} />);
    const box = screen.getByRole('textbox', { name: /ITIN/ });
    await userEvent.type(box, '812345678');
    expect(box).toHaveValue('812-34-5678');
    expect(box).toHaveAccessibleDescription(PETITION_DETAIL_ITIN_NINE);
    expect(screen.queryByText(PETITION_DETAIL_ITIN)).not.toBeInTheDocument();
    await userEvent.clear(box);
    await userEvent.type(box, '912345678');
    expect(screen.queryByText(PETITION_DETAIL_ITIN_NINE)).not.toBeInTheDocument();
    expect(screen.queryByText(PETITION_DETAIL_ITIN)).not.toBeInTheDocument();
  });

  it('a saved number shows as saved only under its Yes', () => {
    // *_saved is judged on the stored value alone; under a No the box prints nothing
    render(
      <Harness
        initial={{
          itin_answer: 'no',
          itin_saved: true,
          other_ssn_answer: 'no',
          other_ssn_saved: true,
        }}
      />
    );
    expect(screen.queryByText(ITIN_SAVED)).not.toBeInTheDocument();
    expect(screen.queryByText(OTHER_SSN_SAVED)).not.toBeInTheDocument();
  });

  it('a text box stops at its measured cap', () => {
    render(<Harness initial={{ sole_proprietor_answer: 'yes', venue_choice: 'other' }} />);
    expect(screen.getByRole('textbox', { name: FORM_101_LINE_12_NAME })).toHaveAttribute(
      'maxLength',
      String(PETITION_TEXT_LIMITS.business_name)
    );
    expect(screen.getByRole('textbox', { name: FORM_101_VENUE_CHOICES.other })).toHaveAttribute(
      'maxLength',
      String(PETITION_TEXT_LIMITS.venue_reason)
    );
  });

  it('a row cell stops at the server ceiling and a date keeps MM/DD/YYYY', async () => {
    render(<Harness initial={{ prior_bankruptcy_answer: 'yes' }} />);
    await userEvent.click(screen.getByRole('button', { name: PETITION_ADD_PRIOR_CASE }));
    const district = document.querySelector('input[name="prior_cases_0_district"]');
    expect(district).toHaveAttribute('maxLength', String(PETITION_ROW_CELL_MAX_LENGTH));
    const when = document.querySelector('input[name="prior_cases_0_filed_on"]') as HTMLElement;
    await userEvent.type(when, '031420219');
    expect(when).toHaveValue('03/14/2021');
  });

  it('a pasted or typed date reaches the server as MM/DD/YYYY and nothing else', async () => {
    const onChange = vi.fn();
    render(<Harness initial={{ prior_bankruptcy_answer: 'yes' }} onChange={onChange} />);
    await userEvent.click(screen.getByRole('button', { name: PETITION_ADD_PRIOR_CASE }));
    const when = document.querySelector('input[name="prior_cases_0_filed_on"]') as HTMLElement;
    await userEvent.click(when);
    await userEvent.paste('03-14-2021 ');
    expect(when).toHaveValue('03/14/2021');
    const last = onChange.mock.calls.at(-1)![0] as PetitionAnswers;
    expect(last.prior_cases?.[0].filed_on).toBe('03/14/2021');
  });

  it('a mailing ZIP takes digits only, at most nine, typed or pasted', async () => {
    // Owner ruling Q1: no native maxLength, so a paste loses no digit to the box
    render(<Harness initial={{ mailing_answer: 'yes' }} />);
    const zip = screen.getByRole('textbox', { name: /zip code/i });
    expect(zip).not.toHaveAttribute('maxLength');
    await userEvent.type(zip, '60201-12345');
    expect(zip).toHaveValue('602011234');
    await userEvent.clear(zip);
    await userEvent.click(zip);
    await userEvent.paste('60201-1234');
    expect(zip).toHaveValue('602011234');
  });

  it('adds at most two other names and twenty earlier cases', async () => {
    // The form has boxes for two other names, and the server stores at most 20 rows (PF2-T8-7)
    const nineteen = Array.from({ length: 19 }, (_, i) => ({ _key: `c${i}`, district: 'Demo' }));
    render(
      <Harness
        initial={{
          other_names_answer: 'yes',
          prior_bankruptcy_answer: 'yes',
          prior_cases: nineteen,
        }}
      />
    );
    const addName = screen.getByRole('button', { name: PETITION_ADD_OTHER_NAME });
    await userEvent.click(addName);
    await userEvent.click(addName);
    expect(screen.queryByRole('button', { name: PETITION_ADD_OTHER_NAME })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: PETITION_ADD_PRIOR_CASE }));
    expect(document.querySelector('input[name="prior_cases_19_district"]')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: PETITION_ADD_PRIOR_CASE })).not.toBeInTheDocument();
  });

  it('the business block shows the line-27 information under a Yes', async () => {
    render(<Harness />);
    expect(screen.queryByText(LINE_12_FEEDS_107)).not.toBeInTheDocument();
    await userEvent.click(radio('sole_proprietor_answer', 'yes'));
    expect(screen.getByText(LINE_12_FEEDS_107)).toBeInTheDocument();
  });

  it('the division names the clerk', () => {
    const { unmount } = render(<Harness division="Western" />);
    for (const note of screen.getAllByRole('note')) {
      expect(note).toHaveTextContent(CLERK_PHONE_WESTERN);
    }
    unmount();
    render(<Harness division={null} />);
    const notes = screen.getAllByRole('note');
    // Above 1b and above 1f (spec §6.1)
    expect(notes).toHaveLength(2);
    for (const note of notes) {
      expect(note.textContent).toBe(PUBLIC_RECORD_NOTICE);
      expect(note.textContent).toMatch(/options exist\.$/);
    }
  });

  it('the venue line says which division the county is in', () => {
    const { unmount } = render(<Harness division="Western" />);
    const venue = screen.getByRole('group', { name: /Why you are choosing this district/ });
    expect(within(venue).getByText(VENUE_DIVISION_WESTERN)).toBeInTheDocument();
    unmount();
    render(<Harness division={null} />);
    expect(screen.queryByText(VENUE_DIVISION_EASTERN)).not.toBeInTheDocument();
    expect(screen.queryByText(VENUE_DIVISION_WESTERN)).not.toBeInTheDocument();
  });

  it('has no accessibility violations with every Yes open', async () => {
    const { container } = render(
      <Harness
        initial={{
          ...EVERY_YES,
          venue_choice: 'other',
          other_names: [{ _key: 'a', first: 'Demo' }],
          other_business_names: [{ _key: 'b', name: 'Demo Shop' }],
          prior_cases: [{ _key: 'c', district: 'Northern Illinois' }],
          pending_cases: [{ _key: 'd', debtor: 'Demo Partner' }],
        }}
        division="Eastern"
      />
    );
    const results = await axe(container, { rules: { 'color-contrast': { enabled: false } } });
    expect(results).toHaveNoViolations();
  });
});
