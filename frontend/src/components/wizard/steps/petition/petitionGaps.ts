/**
 * Continue's copy of the gates in `petition_step_gaps` (apps/intake/petition.py): the first yes/no
 * a step asks that is still unanswered, in the server's words and order (step 1's seven, the Assets
 * step's hazard, Amounts Owed's line 16 and Supp questions, Contracts & Leases' rent and eviction).
 * Details never hold
 * Continue (spec §5.7), so only the gates are copied; Review lists the details from the server.
 * test_petition_frontend_copy.py pins the sentences and the row nouns.
 */
import {
  PETITION_GATE_DEBT_NATURE,
  PETITION_GATE_DISABLED_VETERAN,
  PETITION_GATE_EVICTION,
  PETITION_GATE_HAZARD,
  PETITION_GATE_ITIN,
  PETITION_GATE_MAILING,
  PETITION_GATE_OTHER_NAMES,
  PETITION_GATE_OTHER_SSN,
  PETITION_GATE_PENDING_CASE,
  PETITION_GATE_PRIOR_BANKRUPTCY,
  PETITION_GATE_RENTS,
  PETITION_GATE_RESERVIST,
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
/** Form 101A's landlord block (4b2), asked under the rent and eviction pair; pinned to the server */
export const LANDLORD_KEYS = [
  'landlord_name',
  'landlord_street',
  'landlord_city',
  'landlord_state',
  'landlord_zip',
] as const;

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

/**
 * Amounts Owed's Form 101 line 16 and Form 122A-1Supp keys (4d), in PETITION_STEP_OF_KEY's order
 * (E16): the step's body sends these, pinned to the server
 */
export const DEBT_NATURE_KEYS = [
  'debt_nature',
  'debt_nature_text',
  'disabled_veteran',
  'debts_on_duty',
  'reservist',
  'called_to_duty',
  'duty_category',
  'duty_released_on',
  'duty_ended_on',
] as const;
/** Line 16's three answers, 16a, 16b and 16c, in the form's order; pinned to the server */
export const DEBT_NATURE_CHOICES = ['consumer', 'business', 'neither'] as const;

const open = (value: unknown) => value === null || value === undefined;

/**
 * Whether Form 122A-1Supp reaches line 3 (means_lines.py's supp_line_3_reached, R-D2): the debts
 * are primarily consumer debts and line 2 isn't Yes to both questions. Line 2 Yes with its
 * follow-up still open reaches it.
 */
export function supplementLineThreeReached(answers: PetitionAnswers): boolean {
  return (
    answers.debt_nature === 'consumer' &&
    !(answers.disabled_veteran === 'yes' && answers.debts_on_duty === 'yes')
  );
}

/**
 * The first of Amounts Owed's gates still unanswered (petition.py's debt_nature_gaps): line 16,
 * then line 2 under consumer debts, then line 3 where the Supp reaches it, in the server's words,
 * or null. The details never hold Continue.
 */
export function debtNatureGap(answers: PetitionAnswers): string | null {
  if (open(answers.debt_nature)) return PETITION_GATE_DEBT_NATURE;
  if (answers.debt_nature === 'consumer' && open(answers.disabled_veteran)) {
    return PETITION_GATE_DISABLED_VETERAN;
  }
  if (supplementLineThreeReached(answers) && open(answers.reservist))
    return PETITION_GATE_RESERVIST;
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
