import { useState } from 'react';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'vitest-axe';
import { EmploymentBlock } from '../EmploymentBlock';
import {
  AB_ADDRESS_LINE_2_LABEL,
  DELETE_HIDDEN,
  HIDDEN_ANSWERS,
  PAYSTUB_EMPLOYER_HINT,
  SCHEDULE_I_ONE_EMPLOYER,
  SHOW_HIDDEN,
} from '../../../../../constants/copy';
import {
  AB_CITY_LABEL,
  AB_STATE_LABEL,
  AB_ZIP_LABEL,
  CLAIM_STREET_LABEL,
  FORM_106I_COLUMN_SPOUSE,
  FORM_106I_COLUMN_YOU,
  FORM_106I_EMPLOYER_ADDRESS,
  FORM_106I_EMPLOYER_NAME,
  FORM_106I_HOW_LONG,
  FORM_106I_LINE_1_NOTES,
  FORM_106I_OCCUPATION,
} from '../../../../../constants/formText';
import { SCHEDULE_I_TEXT_LIMITS } from '../../../../../constants/scheduleILimits';
import type { ScheduleIAnswers } from '../../../../../types/api';

/** The block with the step's state around it, so pressing and typing behave as on the Income step */
function Harness({
  initial = {},
  spouse = false,
  payStubName,
  onChange,
}: {
  initial?: ScheduleIAnswers;
  spouse?: boolean;
  payStubName?: string;
  onChange?: (next: ScheduleIAnswers) => void;
}) {
  const [answers, setAnswers] = useState<ScheduleIAnswers>(initial);
  return (
    <main>
      <EmploymentBlock
        answers={answers}
        onChange={(next) => {
          onChange?.(next);
          setAnswers(next);
        }}
        spouse={spouse}
        payStubName={payStubName}
      />
    </main>
  );
}

const radio = (name: string, value: string) =>
  document.querySelector(`input[name="${name}"][value="${value}"]`) as HTMLInputElement;
const box = (name: string) => document.querySelector(`[name="${name}"]`) as HTMLInputElement | null;

// What Employed asks beyond the occupation, by ScheduleIAnswers key (PF-4c-J)
const EMPLOYER_KEYS = [
  'employer_name',
  'employer_street',
  'employer_street_2',
  'employer_city',
  'employer_state',
  'employer_zip',
  'time_employed',
];
const HINT = PAYSTUB_EMPLOYER_HINT.replace('{name}', 'Demo Foods LLC');

describe('EmploymentBlock', () => {
  it('Employed shows the occupation, employer, address and how long', async () => {
    const user = userEvent.setup();
    const { container } = render(<Harness />);
    // Nothing starts checked, and nothing below shows until an answer is given
    const statuses = Array.from(
      document.querySelectorAll<HTMLInputElement>('input[name="employment_status"]')
    );
    expect(statuses.map((r) => r.value)).toEqual(['employed', 'not_employed']);
    expect(statuses.some((r) => r.checked)).toBe(false);
    expect(box('occupation')).toBeNull();

    await user.click(radio('employment_status', 'employed'));
    expect(screen.getByLabelText(FORM_106I_OCCUPATION)).toHaveAttribute('name', 'occupation');
    expect(screen.getByLabelText(FORM_106I_EMPLOYER_NAME)).toHaveAttribute('name', 'employer_name');
    // The address boxes are one group named by the form's words, in the reused labels
    const address = screen.getByRole('group', { name: FORM_106I_EMPLOYER_ADDRESS });
    expect(within(address).getByLabelText(CLAIM_STREET_LABEL)).toHaveAttribute(
      'name',
      'employer_street'
    );
    expect(within(address).getByLabelText(AB_ADDRESS_LINE_2_LABEL)).toHaveAttribute(
      'name',
      'employer_street_2'
    );
    expect(within(address).getByLabelText(AB_CITY_LABEL)).toHaveAttribute('name', 'employer_city');
    const state = within(address).getByLabelText(AB_STATE_LABEL);
    expect(state.tagName).toBe('SELECT');
    expect(state).toHaveAttribute('name', 'employer_state');
    expect(within(address).getByLabelText(AB_ZIP_LABEL)).toHaveAttribute('name', 'employer_zip');
    expect(screen.getByLabelText(FORM_106I_HOW_LONG)).toHaveAttribute('name', 'time_employed');
    // DigniFi prints one employer, beside the form's own note about other jobs
    expect(screen.getByText(FORM_106I_LINE_1_NOTES[0])).toBeInTheDocument();
    expect(screen.getByText(SCHEDULE_I_ONE_EMPLOYER)).toBeInTheDocument();
    expect(screen.queryByText(HIDDEN_ANSWERS)).not.toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();
  });

  it('Not employed shows the occupation only', async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await user.click(radio('employment_status', 'not_employed'));
    expect(screen.getByLabelText(FORM_106I_OCCUPATION)).toBeInTheDocument();
    // Occupation may be student or homemaker, the form's own note says
    expect(screen.getByText(FORM_106I_LINE_1_NOTES[1])).toBeInTheDocument();
    for (const key of EMPLOYER_KEYS) expect(box(key), key).toBeNull();
    expect(screen.queryByText(SCHEDULE_I_ONE_EMPLOYER)).not.toBeInTheDocument();
    expect(screen.queryByText(HIDDEN_ANSWERS)).not.toBeInTheDocument();
  });

  it('an employer kept under Not employed hides behind one line that offers Show and Delete', async () => {
    const user = userEvent.setup();
    render(
      <Harness
        initial={{
          employment_status: 'not_employed',
          occupation: 'Cook',
          employer_name: 'Demo Diner',
          time_employed: '2 years',
        }}
      />
    );
    // The occupation still shows; the employer stays stored and unshown, behind exactly one line
    expect(screen.getByLabelText(FORM_106I_OCCUPATION)).toHaveValue('Cook');
    for (const key of EMPLOYER_KEYS) expect(box(key), key).toBeNull();
    expect(screen.getAllByText(HIDDEN_ANSWERS)).toHaveLength(1);
    expect(screen.getByRole('button', { name: DELETE_HIDDEN })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: SHOW_HIDDEN }));
    expect(screen.getByLabelText(FORM_106I_EMPLOYER_NAME)).toHaveValue('Demo Diner');
    expect(screen.getByLabelText(FORM_106I_HOW_LONG)).toHaveValue('2 years');
    expect(screen.queryByText(HIDDEN_ANSWERS)).not.toBeInTheDocument();
  });

  it('an answer kept with no employment status hides behind one line', async () => {
    const user = userEvent.setup();
    const changes: ScheduleIAnswers[] = [];
    render(
      <Harness
        initial={{ occupation: 'Cook', employer_city: 'Chicago' }}
        onChange={(next) => changes.push(next)}
      />
    );
    expect(box('occupation')).toBeNull();
    expect(screen.getAllByText(HIDDEN_ANSWERS)).toHaveLength(1);
    // Delete with no answer clears the occupation and every employer box (4c-R6)
    await user.click(screen.getByRole('button', { name: DELETE_HIDDEN }));
    expect(changes.at(-1)).toEqual({
      occupation: null,
      employer_name: null,
      employer_street: null,
      employer_street_2: null,
      employer_city: null,
      employer_state: null,
      employer_zip: null,
      time_employed: null,
    });
    expect(screen.queryByText(HIDDEN_ANSWERS)).not.toBeInTheDocument();
  });

  it('Delete clears the employer boxes and how long', async () => {
    const user = userEvent.setup();
    const changes: ScheduleIAnswers[] = [];
    render(
      <Harness
        initial={{
          employment_status: 'not_employed',
          occupation: 'Cook',
          employer_name: 'Demo Diner',
          employer_state: 'IL',
          time_employed: '2 years',
        }}
        onChange={(next) => changes.push(next)}
      />
    );
    await user.click(screen.getByRole('button', { name: DELETE_HIDDEN }));
    // The occupation stays: Not employed still asks it
    expect(changes.at(-1)).toEqual({
      employment_status: 'not_employed',
      occupation: 'Cook',
      employer_name: null,
      employer_street: null,
      employer_street_2: null,
      employer_city: null,
      employer_state: null,
      employer_zip: null,
      time_employed: null,
    });
    expect(screen.queryByText(HIDDEN_ANSWERS)).not.toBeInTheDocument();
    expect(screen.getByLabelText(FORM_106I_OCCUPATION)).toHaveValue('Cook');
  });

  it("the spouse's block is named apart from yours", async () => {
    const answers: ScheduleIAnswers = {
      employment_status: 'employed',
      spouse_employment_status: 'employed',
    };
    const { container } = render(
      <main>
        <EmploymentBlock answers={answers} onChange={() => {}} spouse={false} />
        <EmploymentBlock answers={answers} onChange={() => {}} spouse />
      </main>
    );
    const yours = screen.getByRole('group', { name: FORM_106I_COLUMN_YOU });
    const theirs = screen.getByRole('group', { name: FORM_106I_COLUMN_SPOUSE });
    expect(within(yours).getByLabelText(FORM_106I_EMPLOYER_NAME)).toHaveAttribute(
      'name',
      'employer_name'
    );
    // The spouse's boxes carry the spouse_ keys, so the two columns never share a box
    expect(within(theirs).getByLabelText(FORM_106I_EMPLOYER_NAME)).toHaveAttribute(
      'name',
      'spouse_employer_name'
    );
    for (const key of ['employment_status', 'occupation', ...EMPLOYER_KEYS]) {
      expect(theirs.querySelector(`[name="spouse_${key}"]`), key).not.toBeNull();
      expect(theirs.querySelector(`[name="${key}"]`), key).toBeNull();
    }
    expect(await axe(container)).toHaveNoViolations();
  });

  it('Show keeps the block open while the last box is cleared', async () => {
    const user = userEvent.setup();
    render(
      <Harness initial={{ employment_status: 'not_employed', employer_name: 'Demo Diner' }} />
    );
    await user.click(screen.getByRole('button', { name: SHOW_HIDDEN }));
    await user.clear(screen.getByLabelText(FORM_106I_EMPLOYER_NAME));
    // Nothing is stored below any more, yet the boxes stay for the visit (FR-W4)
    expect(screen.getByLabelText(FORM_106I_EMPLOYER_NAME)).toHaveValue('');
    expect(screen.queryByText(HIDDEN_ANSWERS)).not.toBeInTheDocument();
  });

  it('the pay stub hint shows beside your employer box only when a name was read', async () => {
    const { unmount } = render(
      <Harness initial={{ employment_status: 'employed' }} payStubName="Demo Foods LLC" />
    );
    const name = screen.getByLabelText(FORM_106I_EMPLOYER_NAME);
    expect(name).toHaveAccessibleDescription(HINT);
    unmount();

    render(<Harness initial={{ employment_status: 'employed' }} payStubName="" />);
    expect(screen.queryByText(/Your pay stub says/)).not.toBeInTheDocument();
  });

  it('the hint never fills the box', async () => {
    const user = userEvent.setup();
    const changes: ScheduleIAnswers[] = [];
    render(<Harness payStubName="Demo Foods LLC" onChange={(next) => changes.push(next)} />);
    await user.click(radio('employment_status', 'employed'));
    expect(screen.getByLabelText(FORM_106I_EMPLOYER_NAME)).toHaveValue('');
    expect(screen.getByText(HINT)).toBeInTheDocument();
    expect(changes.some((next) => 'employer_name' in next)).toBe(false);
  });

  it('the spouse block has no hint', () => {
    render(
      <Harness spouse initial={{ spouse_employment_status: 'employed' }} payStubName="Demo Foods" />
    );
    expect(screen.getByLabelText(FORM_106I_EMPLOYER_NAME)).toHaveAttribute(
      'name',
      'spouse_employer_name'
    );
    expect(screen.queryByText(/Your pay stub says/)).not.toBeInTheDocument();
  });

  it('each box stops at its cap', async () => {
    const user = userEvent.setup();
    render(<Harness initial={{ employment_status: 'employed' }} />);
    for (const key of [
      'occupation',
      'employer_name',
      'employer_street',
      'employer_street_2',
      'employer_city',
      'time_employed',
    ] as const) {
      expect(box(key), key).toHaveAttribute('maxLength', String(SCHEDULE_I_TEXT_LIMITS[key]));
    }
    const occupation = screen.getByLabelText(FORM_106I_OCCUPATION);
    await user.type(occupation, 'x'.repeat(SCHEDULE_I_TEXT_LIMITS.occupation + 5));
    expect(occupation).toHaveValue('x'.repeat(SCHEDULE_I_TEXT_LIMITS.occupation));
    // The ZIP keeps digits only, five or nine of them; the state is chosen from a list
    const zip = screen.getByLabelText(AB_ZIP_LABEL);
    await user.type(zip, '60601-1234-99');
    expect(zip).toHaveValue('606011234');
  });
});
