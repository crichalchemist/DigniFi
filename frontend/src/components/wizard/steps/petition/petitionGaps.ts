/**
 * Continue's copy of the gates in `petition_step_gaps` (apps/intake/petition.py): the first yes/no
 * a step asks that is still unanswered, in the server's words and order (step 1's seven, the Assets
 * step's hazard, Contracts & Leases' rent and eviction). Details never hold
 * Continue (spec §5.7), so only the gates are copied; Review lists the details from the server.
 * test_petition_frontend_copy.py pins the sentences and the row nouns.
 */
import {
  PETITION_GATE_EVICTION,
  PETITION_GATE_HAZARD,
  PETITION_GATE_ITIN,
  PETITION_GATE_MAILING,
  PETITION_GATE_OTHER_NAMES,
  PETITION_GATE_OTHER_SSN,
  PETITION_GATE_PENDING_CASE,
  PETITION_GATE_PRIOR_BANKRUPTCY,
  PETITION_GATE_RENTS,
  PETITION_GATE_SOLE_PROPRIETOR,
} from '../../../../constants/copy';
import type { PetitionAnswers } from '../../../../types/api';

// petition.py's STEP_1_GATES, in its order, each with its sentence
const STEP_1_GATES: [keyof PetitionAnswers, string][] = [
  ['other_names_answer', PETITION_GATE_OTHER_NAMES],
  ['itin_answer', PETITION_GATE_ITIN],
  ['other_ssn_answer', PETITION_GATE_OTHER_SSN],
  ['mailing_answer', PETITION_GATE_MAILING],
  ['prior_bankruptcy_answer', PETITION_GATE_PRIOR_BANKRUPTCY],
  ['pending_case_answer', PETITION_GATE_PENDING_CASE],
  ['sole_proprietor_answer', PETITION_GATE_SOLE_PROPRIETOR],
];

// What the filer calls a row of each list, which the server's too-long row sentence names (Q5)
type PetitionList = 'other_names' | 'other_business_names' | 'prior_cases' | 'pending_cases';
export const PETITION_ROW_NOUNS: Record<PetitionList, string> = {
  other_names: 'name',
  other_business_names: 'name',
  prior_cases: 'case',
  pending_cases: 'case',
};

/** The first of step 1's gates still unanswered, in the server's words, or null */
export function firstPetitionGap(answers: PetitionAnswers): string | null {
  for (const [key, sentence] of STEP_1_GATES) {
    if (answers[key] !== 'yes' && answers[key] !== 'no') return sentence;
  }
  return null;
}

// The keys each later step's block asks and its body sends, in PetitionAnswers' order: the Assets
// step's Form 101 line 14 and Contracts & Leases' line 11 (spec §6.5, §6.7)
export const HAZARD_KEYS = [
  'hazard_answer',
  'hazard_what',
  'hazard_why',
  'hazard_street',
  'hazard_city',
  'hazard_state',
  'hazard_zip',
] as const;
export const RENT_KEYS = ['rents_residence', 'eviction_judgment'] as const;

/** Any of a block's keys holds an answer: the block counts as touched (PF2-T8-10) */
export function anyAnswerIn(
  answers: PetitionAnswers,
  keys: readonly (keyof PetitionAnswers)[]
): boolean {
  return keys.some((key) => {
    const value = answers[key];
    return typeof value === 'string' ? value !== '' : value !== null && value !== undefined;
  });
}

const answered = (value: unknown) => value === 'yes' || value === 'no';

/** The Assets step's gate (petition.py's GATE_HAZARD), in the server's words, or null */
export function hazardGap(answers: PetitionAnswers): string | null {
  return answered(answers.hazard_answer) ? null : PETITION_GATE_HAZARD;
}

/**
 * The first of Contracts & Leases' gates still unanswered (GATE_RENTS, then GATE_EVICTION, which
 * is asked only under a rent Yes), in the server's words, or null
 */
export function rentGap(answers: PetitionAnswers): string | null {
  if (!answered(answers.rents_residence)) return PETITION_GATE_RENTS;
  if (answers.rents_residence === 'yes' && !answered(answers.eviction_judgment)) {
    return PETITION_GATE_EVICTION;
  }
  return null;
}

/** A list row with nothing typed in any cell: it stays in the browser (PF2-T8-7) */
export function isBlankPetitionRow(row: object): boolean {
  return Object.entries(row).every(
    ([key, value]) => key.startsWith('_') || typeof value !== 'string' || value.trim() === ''
  );
}

/** The digits of what was typed, dashes and spaces dropped, as the server reads them */
export function digitsOf(value: string | null | undefined): string {
  return (value ?? '').replace(/\D/g, '');
}

/** Nine digits, however typed: the server's `is_nine_digits` */
export function isNineDigits(value: string | null | undefined): boolean {
  return digitsOf(value).length === 9;
}

/** Nine digits starting with 9: the server's `is_itin` (PF2-U2), so "saved" means it prints */
export function isItin(value: string | null | undefined): boolean {
  const digits = digitsOf(value);
  return digits.length === 9 && digits.startsWith('9');
}
