import { CLAIM_TEXT_LABELS, SCHEDULE_I_DETAIL_TOO_LONG } from './copy';
import type { ContractRow, DebtRow } from '../types/api';

/**
 * How long a claims text may be before its box on a form can't take it (forms step 4e, E4,
 * R-EXPLAIN): the browser's copy of form_108.limits.json's box caps and of ROW_BOXES and row_cap
 * in apps/intake/intentions.py. test_intention_frontend_copy.py pins the caps and boxes;
 * claimTextRowCases.json pins which list a row is measured in. A text over its cap is stored as
 * typed and gets a note beside its box, never a gap that holds Continue (DIG-542).
 */

/** The texts that print in a claims box, and the "[explain]" words */
export type ClaimTextKey =
  | 'creditor_name'
  | 'collateral_description'
  | 'counterparty_name'
  | 'description'
  | 'explain';

/** The list a row prints in: Schedule D's, E/F's two Parts, Form 108's leases, Schedule G's */
export type ClaimTextList = 'secured' | 'priority' | 'unsecured' | 'leases' | 'contracts';

/** Each box's cap in characters, keyed "<form>:<binding>" ("form_108:explain" for the pair) */
export const CLAIM_BOX_CAPS: Record<string, number> = {
  'form_108:claims.secured[].name': 57,
  'schedule_d:claims.secured[].name': 43,
  'schedule_e_f:claims.priority[].name': 49,
  'schedule_e_f:claims.unsecured[].name': 70,
  'form_108:claims.secured[].property': 190,
  'schedule_d:claims.secured[].property': 57,
  'schedule_g:claims.contracts[].name': 79,
  'form_108:claims.leases[].name': 98,
  'schedule_g:claims.contracts[].purpose': 301,
  'form_108:claims.leases[].purpose': 138,
  'form_108:explain': 62,
};

/** "<text>:<list>" to the boxes that print the text for a row of that list (4e-R4's table) */
export const ROW_BOXES: Record<string, string[]> = {
  'creditor_name:secured': ['form_108:claims.secured[].name', 'schedule_d:claims.secured[].name'],
  'creditor_name:priority': ['schedule_e_f:claims.priority[].name'],
  'creditor_name:unsecured': ['schedule_e_f:claims.unsecured[].name'],
  'collateral_description:secured': [
    'form_108:claims.secured[].property',
    'schedule_d:claims.secured[].property',
  ],
  'counterparty_name:leases': [
    'schedule_g:claims.contracts[].name',
    'form_108:claims.leases[].name',
  ],
  'counterparty_name:contracts': ['schedule_g:claims.contracts[].name'],
  'description:leases': [
    'schedule_g:claims.contracts[].purpose',
    'form_108:claims.leases[].purpose',
  ],
  'description:contracts': ['schedule_g:claims.contracts[].purpose'],
  'explain:secured': ['form_108:explain'],
};

/** The forms' names in a sentence, in packet order */
const FORM_WORDS: Record<string, string> = {
  form_108: 'Form 108',
  schedule_d: 'Schedule D',
  schedule_e_f: 'Schedule E/F',
  schedule_g: 'Schedule G',
};

// E/F Part 1's four kinds (PRIORITY_TYPES): the filer's answer alone moves a debt there
const PRIORITY_KINDS = ['domestic_support', 'taxes', 'intoxicated', 'other'];
// The lease kinds Form 108 asks about (FORM_108_LEASE_KINDS, 4e-R23): every kind but residential,
// and a lease with no kind
const FORM_108_LEASE_KINDS = ['vehicle', 'other_personal_property', 'other', null];

type DebtFields = Pick<DebtRow, 'is_secured' | 'priority_answer'>;
type ContractFields = Pick<ContractRow, 'contract_type' | 'lease_kind'>;

/**
 * The list a row's texts are measured in (claim_list_of, contract_text_list): a debt's Schedule D
 * or E/F Part; a lease Form 108 asks about, a residential lease (Schedule G only), or null for a
 * contract that isn't a lease
 */
export function rowList(row: DebtFields | ContractFields): ClaimTextList | null {
  if ('contract_type' in row) {
    if (row.contract_type !== 'lease') return null;
    return FORM_108_LEASE_KINDS.includes(row.lease_kind ?? null) ? 'leases' : 'contracts';
  }
  if (row.is_secured) return 'secured';
  return PRIORITY_KINDS.includes(row.priority_answer ?? '') ? 'priority' : 'unsecured';
}

/**
 * The smallest cap among the boxes of the row's own list, and the forms holding it in packet
 * order; null when the row's list prints no such text
 */
export function rowCap(
  text: ClaimTextKey,
  row: DebtFields | ContractFields
): { cap: number; forms: string[] } | null {
  const list = rowList(row);
  const keys = list === null ? undefined : ROW_BOXES[`${text}:${list}`];
  if (keys === undefined) return null;
  const cap = Math.min(...keys.map((key) => CLAIM_BOX_CAPS[key]));
  const holders = keys.filter((key) => CLAIM_BOX_CAPS[key] === cap).map((key) => key.split(':')[0]);
  return { cap, forms: Object.keys(FORM_WORDS).filter((form) => holders.includes(form)) };
}

/**
 * The note beside a box whose text is over its row's cap, in Review's words
 * (SCHEDULE_I_DETAIL_TOO_LONG), or null. Characters are counted as the server counts them (code
 * points), and the "[explain]" words trimmed, as they print (T5-R1).
 */
export function tooLongNote(
  text: ClaimTextKey,
  row: DebtFields | ContractFields,
  value: string | null | undefined
): string | null {
  const limit = rowCap(text, row);
  if (limit === null || !value) return null;
  const counted = text === 'explain' ? value.trim() : value;
  if (Array.from(counted).length <= limit.cap) return null;
  return SCHEDULE_I_DETAIL_TOO_LONG.replace('{label}', CLAIM_TEXT_LABELS[text]).replace(
    '{form}',
    limit.forms.map((form) => FORM_WORDS[form]).join(' and ')
  );
}
