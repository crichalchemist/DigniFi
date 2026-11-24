/**
 * The definitions on Your Plans (forms step 4e, E1, E2, 4e-R7): one collapsed panel per choice,
 * each holding its statute's provision whole and closing with the same neutral pointer to help.
 * They render once per Part, above its rows, in the form's order, all alike, so no choice is shown
 * more prominently than another.
 */
import { WhatDoesThisMean } from '../../WhatDoesThisMean';
import {
  PLANS_EFFECTS_HELP,
  WHAT_DOES_ASSUME_MEAN,
  WHAT_DOES_EXPLAIN_MEAN,
  WHAT_DOES_REAFFIRM_MEAN,
  WHAT_DOES_REDEEM_MEAN,
  WHAT_DOES_SURRENDER_MEAN,
} from '../../../../constants/copy';
import {
  STATUTE_365_P_2,
  STATUTE_365_P_2_CITATION,
  STATUTE_521_A_2_A,
  STATUTE_521_A_2_A_CITATION,
  STATUTE_524_C,
  STATUTE_524_C_CITATION,
  STATUTE_722,
  STATUTE_722_CITATION,
} from '../../../../constants/formText';

/** One panel: the statute's paragraphs, one line each, as the source sets them */
function Definition({ label, citation, text }: { label: string; citation: string; text: string }) {
  return (
    <WhatDoesThisMean label={label} citation={citation} note={PLANS_EFFECTS_HELP}>
      {text.split('\n').map((line, index) => (
        <p key={index}>{line}</p>
      ))}
    </WhatDoesThisMean>
  );
}

/** Part 1's four: surrender, redeem, reaffirm, then retain and explain */
export function SecuredDefinitions() {
  return (
    <>
      <Definition
        label={WHAT_DOES_SURRENDER_MEAN}
        citation={STATUTE_521_A_2_A_CITATION}
        text={STATUTE_521_A_2_A}
      />
      <Definition
        label={WHAT_DOES_REDEEM_MEAN}
        citation={STATUTE_722_CITATION}
        text={STATUTE_722}
      />
      <Definition
        label={WHAT_DOES_REAFFIRM_MEAN}
        citation={STATUTE_524_C_CITATION}
        text={STATUTE_524_C}
      />
      <Definition
        label={WHAT_DOES_EXPLAIN_MEAN}
        citation={STATUTE_521_A_2_A_CITATION}
        text={STATUTE_521_A_2_A}
      />
    </>
  );
}

/** Part 2's one: an assumed lease */
export function LeaseDefinition() {
  return (
    <Definition
      label={WHAT_DOES_ASSUME_MEAN}
      citation={STATUTE_365_P_2_CITATION}
      text={STATUTE_365_P_2}
    />
  );
}
