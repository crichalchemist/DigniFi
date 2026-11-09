/**
 * What the Codebtors step still lacks, in Complete's words: a copy of H1 to H9 of the claim gap
 * table (claim_step_gaps in apps/intake/claims.py), in the same order (3c3 Task 6, R8).
 */
import {
  CLAIM_GAP_ADDRESS,
  CLAIM_GAP_STREET_CITY,
  CODEBTOR_GAP_COMMUNITY,
  CODEBTOR_GAP_NO_ANSWER,
  CODEBTOR_GAP_NO_BUT_LISTED,
  CODEBTOR_GAP_NO_LINK,
  CODEBTOR_GAP_NO_NAME,
  CODEBTOR_GAP_SPOUSE_DETAILS,
  CODEBTOR_GAP_SPOUSE_LIVED,
  CODEBTOR_GAP_YES_BUT_NONE,
  NAMELESS_CODEBTOR,
} from '../../../../constants/copy';
import { isBlankCodebtor, keptRows } from '../../../../utils/claimRows';
import { addressMissing, claimRowName, fill, inIdOrder, linkIsLive } from './claimNames';
import type { ClaimAnswers, CodebtorRow, ContractRow, DebtRow } from '../../../../types/api';

const blank = (value: string | undefined | null) => (value ?? '').trim() === '';

/** The spouse's address as the answers hold it, in the shape the address check reads */
export function spouseAddress(answers: ClaimAnswers) {
  return {
    street_address: answers.community_spouse_street_address ?? '',
    street_2: answers.community_spouse_street_2 ?? '',
    city: answers.community_spouse_city ?? '',
    state: answers.community_spouse_state ?? '',
    zip_code: answers.community_spouse_zip_code ?? '',
    outside_us: answers.community_spouse_outside_us ?? false,
  };
}

/** Every gap of one codebtor, in the table's order H7 to H9, each in the row's own name */
export function codebtorRowGaps(
  row: CodebtorRow,
  debts: DebtRow[],
  contracts: ContractRow[]
): string[] {
  const gaps: string[] = [];
  const words = { name: claimRowName(row.name, NAMELESS_CODEBTOR) };
  if (blank(row.name)) gaps.push(CODEBTOR_GAP_NO_NAME);
  if (addressMissing(row)) {
    gaps.push(fill(row.outside_us ? CLAIM_GAP_STREET_CITY : CLAIM_GAP_ADDRESS, words));
  }
  const live = (row.links ?? []).filter((link) =>
    linkIsLive(link.id, link.kind === 'debt' ? debts : contracts)
  );
  if (live.length === 0) gaps.push(fill(CODEBTOR_GAP_NO_LINK, words));
  return gaps;
}

/** The first thing the step lacks, or null: H1 to H6, then the first row's first gap */
export function firstCodebtorGap(
  rows: CodebtorRow[],
  answers: ClaimAnswers,
  debts: DebtRow[],
  contracts: ContractRow[]
): string | null {
  const kept = inIdOrder(keptRows(rows, isBlankCodebtor));
  const answer = answers.codebtors_answer ?? null;
  if (answer === null) return CODEBTOR_GAP_NO_ANSWER;
  if (answer === 'yes' && kept.length === 0) return CODEBTOR_GAP_YES_BUT_NONE;
  if (answer === 'no' && kept.length > 0) return CODEBTOR_GAP_NO_BUT_LISTED;
  const lived = answers.community_lived ?? null;
  if (lived === null) return CODEBTOR_GAP_COMMUNITY;
  if (lived === 'yes') {
    const withYou = answers.community_spouse_lived_with ?? null;
    if (withYou === null) return CODEBTOR_GAP_SPOUSE_LIVED;
    if (
      withYou === 'yes' &&
      (blank(answers.community_state) ||
        blank(answers.community_spouse_name) ||
        addressMissing(spouseAddress(answers)))
    ) {
      return CODEBTOR_GAP_SPOUSE_DETAILS;
    }
  }
  for (const row of kept) {
    const [first] = codebtorRowGaps(row, debts, contracts);
    if (first !== undefined) return first;
  }
  return null;
}
