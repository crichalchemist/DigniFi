/**
 * The words for the means test's result (forms step 3h1 spec §7.4 and §7.9).
 *
 * The server stores one of four outcomes and never a sentence: the browser composes the words
 * from `copy.ts`, so the sidebar and the dashboard say the same thing. The result is the form's
 * arithmetic, never a verdict. The closing sentence ("A court makes the final decision.") and
 * the link to line 43 under a presumption are never in the list: each caller renders the link,
 * then `UPL_MEANS_TEST_DISCLAIMER` once, after the list, and only when the list isn't empty.
 */

import {
  MEANS_OUTCOME_ABOVE,
  MEANS_OUTCOME_BELOW,
  MEANS_OUTCOME_ANSWER_PAGE,
  MEANS_OUTCOME_ANSWER_SIDEBAR,
  MEANS_OUTCOME_NO_PRESUMPTION,
  MEANS_OUTCOME_PRESUMPTION,
  MEANS_OUTCOME_REASSURANCE,
  MEANS_TABLE_MISSING,
} from '../constants/copy';
import { PRESUMPTION_INSTRUCTIONS } from '../constants/formText';
import type { MeansOutcome } from '../types/api';

/** Where the sentences are shown: the sidebar words its pointer to the page differently */
export type OutcomePlace = 'sidebar' | 'dashboard' | 'page';

/**
 * The sentences for an outcome, in the order they are shown. An outcome of null (no result yet,
 * or a row saved before 3h1) gives none, and so does one that names a household with no family
 * size, rather than "a household of null".
 */
export function meansOutcomeSentences(
  outcome: MeansOutcome | null,
  familySize: number | null,
  tablesGap: string | null,
  place: OutcomePlace
): string[] {
  const forHousehold = (sentence: string) => sentence.replace('{n}', String(familySize));

  switch (outcome) {
    case 'at_or_below_median':
      return familySize === null ? [] : [forHousehold(MEANS_OUTCOME_BELOW)];
    case 'cannot_work_out':
      // A missing table is this outcome too, so the reassurance follows it as well (plan R13)
      return familySize === null
        ? []
        : [
            forHousehold(MEANS_OUTCOME_ABOVE),
            tablesGap
              ? MEANS_TABLE_MISSING
              : place === 'sidebar'
                ? MEANS_OUTCOME_ANSWER_SIDEBAR
                : MEANS_OUTCOME_ANSWER_PAGE,
            MEANS_OUTCOME_REASSURANCE,
          ];
    case 'no_presumption':
      return [MEANS_OUTCOME_NO_PRESUMPTION];
    case 'presumption':
      return [MEANS_OUTCOME_PRESUMPTION, PRESUMPTION_INSTRUCTIONS];
    default:
      return [];
  }
}
