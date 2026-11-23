/**
 * Continue's copy of the gates in `schedule_i_step_gaps` (apps/intake/schedule_i.py): the first
 * yes/no a step asks that is still unanswered, in the server's words and order. Step 2 asks lines
 * 11 and 13 and step 4 asks Schedule J's line 24, so each step has its own function. Details never
 * hold Continue (spec §5.7), so only the gates are copied; Review lists the details from the
 * server. test_schedule_i_frontend_copy.py pins the sentences and the keys.
 */
import {
  SCHEDULE_I_GATE_J24,
  SCHEDULE_I_GATE_LINE_11,
  SCHEDULE_I_GATE_LINE_13,
} from '../../../../constants/copy';
import type { ScheduleIAnswers } from '../../../../types/api';

// The keys each step's block asks and its body sends, in ScheduleIAnswers.KEYS' order (4c-R7):
// step 2 asks lines 1, 11 and 13, step 4 asks Schedule J's line 24. The nine spouse_ keys go only
// while the filer is married with the spouse at home, not filing (`married_together`), which the
// wizard decides.
export const STEP_2_SCHEDULE_I_KEYS = [
  'employment_status',
  'occupation',
  'employer_name',
  'employer_street',
  'employer_street_2',
  'employer_city',
  'employer_state',
  'employer_zip',
  'time_employed',
  'spouse_employment_status',
  'spouse_occupation',
  'spouse_employer_name',
  'spouse_employer_street',
  'spouse_employer_street_2',
  'spouse_employer_city',
  'spouse_employer_state',
  'spouse_employer_zip',
  'spouse_time_employed',
  'line_11_answer',
  'line_11_text',
  'line_11_amount',
  'line_13_answer',
  'line_13_text',
] as const;

export const STEP_4_SCHEDULE_I_KEYS = [
  'schedule_j_line_24_answer',
  'schedule_j_line_24_text',
] as const;

const answered = (value: unknown): boolean => value === 'yes' || value === 'no';

/** The first of step 2's gates (line 11, then line 13) still unanswered, in the server's words, or null */
export function scheduleIGate(answers: ScheduleIAnswers): string | null {
  if (!answered(answers.line_11_answer)) return SCHEDULE_I_GATE_LINE_11;
  if (!answered(answers.line_13_answer)) return SCHEDULE_I_GATE_LINE_13;
  return null;
}

/** Step 4's one gate, Schedule J's line 24, in the server's words, or null once answered */
export function lineTwentyFourGate(answers: ScheduleIAnswers): string | null {
  return answered(answers.schedule_j_line_24_answer) ? null : SCHEDULE_I_GATE_J24;
}
