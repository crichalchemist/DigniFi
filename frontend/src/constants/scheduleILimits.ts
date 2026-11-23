import type { ScheduleITextKey } from '../types/api';

/**
 * Where each of Schedule I's and Schedule J's text boxes stops: the character caps
 * build_schedule_i_limits.py measures from the boxes at 6 pt (schedule_i.limits.json's `limits`).
 * test_schedule_i_frontend_copy.py pins this copy to that file and to the server's.
 */
export const SCHEDULE_I_TEXT_LIMITS: Record<ScheduleITextKey, number> = {
  occupation: 44,
  employer_name: 44,
  employer_street: 44,
  employer_street_2: 44,
  employer_city: 22,
  employer_state: 4,
  employer_zip: 10,
  time_employed: 20,
  spouse_occupation: 44,
  spouse_employer_name: 44,
  spouse_employer_street: 44,
  spouse_employer_street_2: 44,
  spouse_employer_city: 22,
  spouse_employer_state: 4,
  spouse_employer_zip: 10,
  spouse_time_employed: 20,
  line_11_text: 104,
  line_13_text: 210,
  schedule_j_line_24_text: 631,
};
