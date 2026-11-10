/**
 * UPL check on the claim steps' sentences (3c3 spec §7.5, R13)
 *
 * DigniFi gives legal information, never advice. A filer on Amounts Owed, Contracts and Codebtors
 * must never be told what will happen to a debt, or which figure to enter: the answers are theirs.
 * The list is PROHIBITED_PHRASES in docs/UPL_COMPLIANCE.md §4.2, plus the wording that predicts an
 * outcome or suggests a value. "$0" is allowed: it names the form's floor, never a value to enter.
 * Every sentence the claim steps say goes in CLAIM_SENTENCES, or in OTHER_CLAIM_SENTENCES (the
 * steps' own sentences, which Tasks 8-11 add).
 */

import { describe, expect, it } from 'vitest';
import * as copy from '../constants/copy';

const ADVICE: RegExp[] = [
  /\bshould\b/i,
  /\brecommend/i,
  /\bwe suggest\b/i,
  /\byou must\b/i,
  /\badvise/i,
  /\bwill be discharged\b/i,
  /\byou will keep\b/i,
  /\byou qualify\b/i,
  /\$\s?(?!0(?!\d|[.,]\d))\d/, // "$0" is the form's floor, never a value to enter (R13)
  // PROHIBITED_PHRASES that the words above don't already catch
  /\byou will qualify\b/i,
  /\byou will probably\b/i,
  /\byou are eligible\b/i,
  /\bthis is the best option\b/i,
  /\byou need to file\b/i,
];

const CLAIM_NAMES = [
  'NAMELESS_DEBT',
  'NAMELESS_CONTRACT',
  'NAMELESS_CODEBTOR',
  'CLAIM_GAP_KIND',
  'CLAIM_GAP_ADDRESS',
  'CLAIM_GAP_STREET_CITY',
  'CLAIM_GAP_LEGACY_VEHICLE',
  'CLAIM_GAP_LEGACY_OTHER',
  'CLAIM_GAP_LINE_4',
  'DEBT_GAP_NO_ANSWER',
  'DEBT_GAP_NONE_BUT_LISTED',
  'DEBT_GAP_NO_NAME',
  'DEBT_GAP_AMOUNT',
  'DEBT_GAP_AMOUNT_NO_NAME',
  'DEBT_GAP_ADDRESS_NO_NAME',
  'DEBT_GAP_STREET_CITY_NO_NAME',
  'DEBT_GAP_PROPERTY',
  'DEBT_GAP_DESCRIBE',
  'DEBT_GAP_LIEN',
  'DEBT_GAP_LIEN_OTHER',
  'DEBT_GAP_PAYMENT',
  'DEBT_GAP_HOME_LINE',
  'DEBT_GAP_WHO',
  'DEBT_GAP_STATUS',
  'DEBT_GAP_OFFSET',
  'DEBT_GAP_NOTICE',
  'DEBT_GAP_NOTICE_PARTY',
  'CONTRACT_GAP_NO_ANSWER',
  'CONTRACT_GAP_YES_BUT_NONE',
  'CONTRACT_GAP_NO_BUT_LISTED',
  'CONTRACT_GAP_NO_NAME',
  'CONTRACT_GAP_PURPOSE',
  'CONTRACT_GAP_LEASE_KIND',
  'CONTRACT_GAP_VEHICLE',
  'CONTRACT_GAP_PAYMENT',
  'CONTRACT_GAP_OWES_NOW',
  'CONTRACT_GAP_OWED_DEBT',
  'CONTRACT_GAP_SAME_VEHICLE',
  'CONTRACT_GAP_VEHICLE_NO_NAME',
  'CONTRACT_GAP_SAME_VEHICLE_NO_NAME',
  'CODEBTOR_GAP_NO_ANSWER',
  'CODEBTOR_GAP_YES_BUT_NONE',
  'CODEBTOR_GAP_NO_BUT_LISTED',
  'CODEBTOR_GAP_COMMUNITY',
  'CODEBTOR_GAP_SPOUSE_LIVED',
  'CODEBTOR_GAP_SPOUSE_DETAILS',
  'CODEBTOR_GAP_NO_NAME',
  'CODEBTOR_GAP_NO_LINK',
] as const;

const CLAIM_SENTENCES: Record<string, string> = Object.fromEntries(
  CLAIM_NAMES.map((name) => [name, (copy as Record<string, string>)[name]])
);

// The claim steps' own sentences: each of Tasks 8-11 adds its `copy.ts` sentences here as
// `NAME: copy.NAME,`
export const OTHER_CLAIM_SENTENCES: Record<string, string> = {
  ADDRESS_HELP: copy.ADDRESS_HELP,
  LEGACY_REMOVE: copy.LEGACY_REMOVE,
  AMOUNT_HELP: copy.AMOUNT_HELP,
  CLAIM_STATUS_HELP: copy.CLAIM_STATUS_HELP,
  OFFSET_HELP: copy.OFFSET_HELP,
  SECURED_QUESTION: copy.SECURED_QUESTION,
  LIEN_HELP: copy.LIEN_HELP,
  CO_OWNED_NOTE: copy.CO_OWNED_NOTE,
  NOTICE_QUESTION: copy.NOTICE_QUESTION,
  NOTICE_HELP: copy.NOTICE_HELP,
  NO_DEBTS_BUTTON: copy.NO_DEBTS_BUTTON,
  CLAIM_STATUS_NONE: copy.CLAIM_STATUS_NONE,
  OUTSIDE_US_LABEL: copy.OUTSIDE_US_LABEL,
  OUTSIDE_US_HELP: copy.OUTSIDE_US_HELP,
  SECURING_PROPERTY_LABEL: copy.SECURING_PROPERTY_LABEL,
  SECURING_PROPERTY_NONE: copy.SECURING_PROPERTY_NONE,
  LIEN_OTHER_LABEL: copy.LIEN_OTHER_LABEL,
  HOME_LINE_QUESTION: copy.HOME_LINE_QUESTION,
  PAYMENT_SECURED_HELP: copy.PAYMENT_SECURED_HELP,
  DATE_INCURRED_HELP: copy.DATE_INCURRED_HELP,
  ACCOUNT_SAVED: copy.ACCOUNT_SAVED,
  NOTICE_PARTY_HEADING: copy.NOTICE_PARTY_HEADING,
  ADD_ANOTHER_PARTY: copy.ADD_ANOTHER_PARTY,
  REMOVE_PARTY: copy.REMOVE_PARTY,
  HOME_LINE_FIRST: copy.HOME_LINE_FIRST,
  HOME_LINE_ADDITIONAL: copy.HOME_LINE_ADDITIONAL,
  SECURED_PREFILLED_NOTE: copy.SECURED_PREFILLED_NOTE,
  DEBTS_STEP_WHY: copy.DEBTS_STEP_WHY,
  LEASE_KIND_LABEL: copy.LEASE_KIND_LABEL,
  VEHICLE_LEASE_LABEL: copy.VEHICLE_LEASE_LABEL,
  VEHICLE_LEASE_HELP: copy.VEHICLE_LEASE_HELP,
  LEASE_PAYMENT_LABEL: copy.LEASE_PAYMENT_LABEL,
  OWES_NOW_QUESTION: copy.OWES_NOW_QUESTION,
  OWES_NOW_PICK_LABEL: copy.OWES_NOW_PICK_LABEL,
  OWES_NOW_ADD_HELP: copy.OWES_NOW_ADD_HELP,
  GO_TO_AMOUNTS_OWED: copy.GO_TO_AMOUNTS_OWED,
  CONTRACTS_STEP_WHY: copy.CONTRACTS_STEP_WHY,
  CONTRACT_ADDRESS_HELP: copy.CONTRACT_ADDRESS_HELP,
  REVIEW_NO_DEBTS: copy.REVIEW_NO_DEBTS,
  REVIEW_RENT_OR_LOT_RENT: copy.REVIEW_RENT_OR_LOT_RENT,
  REVIEW_TYPED_TOTAL: copy.REVIEW_TYPED_TOTAL,
  REVIEW_LINKED_PAYMENTS: copy.REVIEW_LINKED_PAYMENTS,
  REVIEW_MONTHLY_TOTAL: copy.REVIEW_MONTHLY_TOTAL,
  REVIEW_NO_CONTRACTS: copy.REVIEW_NO_CONTRACTS,
  REVIEW_NO_CODEBTORS: copy.REVIEW_NO_CODEBTORS,
  REVIEW_UNNAMED_CONTRACT: copy.REVIEW_UNNAMED_CONTRACT,
  REVIEW_UNNAMED_CODEBTOR: copy.REVIEW_UNNAMED_CODEBTOR,
  CODEBTOR_LINKS_HELP: copy.CODEBTOR_LINKS_HELP,
  CODEBTOR_LINKS_DEBTS: copy.CODEBTOR_LINKS_DEBTS,
  CODEBTOR_LINKS_CONTRACTS: copy.CODEBTOR_LINKS_CONTRACTS,
  CODEBTOR_LINKS_NONE: copy.CODEBTOR_LINKS_NONE,
  CODEBTORS_STEP_WHY: copy.CODEBTORS_STEP_WHY,
  CODEBTOR_ADDRESS_HELP: copy.CODEBTOR_ADDRESS_HELP,
  LINE_4_HELP: copy.LINE_4_HELP,
  EXPENSES_LINKED_NOTE: copy.EXPENSES_LINKED_NOTE,
  LINE_4_PAY_BOTH: copy.LINE_4_PAY_BOTH,
  LINE_4_CLEAR: copy.LINE_4_CLEAR,
  NOT_SAVED_TRY_AGAIN: copy.NOT_SAVED_TRY_AGAIN,
};

function adviceIn(sentence: string) {
  return ADVICE.filter((pattern) => pattern.test(sentence)).map(String);
}

describe('the claim steps give information, never advice', () => {
  it.each(Object.entries({ ...CLAIM_SENTENCES, ...OTHER_CLAIM_SENTENCES }))(
    '%s predicts no outcome and suggests no value',
    (_name, sentence) => {
      // A missing constant fails here by name, not inside adviceIn
      expect(sentence).toEqual(expect.any(String));
      expect(adviceIn(sentence)).toEqual([]);
    }
  );

  it('lists every gap sentence copy.ts holds', () => {
    const held = Object.keys(copy).filter((key) =>
      /^(CLAIM|DEBT|CONTRACT|CODEBTOR)_GAP_|^NAMELESS_/.test(key)
    );
    expect(held.sort()).toEqual([...CLAIM_NAMES].sort());
  });

  // So a list that stopped matching can't pass by saying nothing
  it.each([
    'You should list this at $0.',
    'We recommend leaving it blank.',
    'We suggest a low value.',
    'You must list your car.',
    'We advise you to wait.',
    'This debt will be discharged.',
    'You will keep your home.',
    'You qualify for this exemption.',
    'Put $500 here.',
    'Enter $5.',
    'Enter $0.50.',
    'Enter $0,500.',
    'You are eligible for this.',
  ])('finds the advice in "%s"', (sentence) => {
    expect(adviceIn(sentence)).not.toEqual([]);
  });

  it('leaves the words that only sound like it alone', () => {
    expect(adviceIn('Put the shoulder bag on line 14.')).toEqual([]);
  });

  it('allows "$0", the form\'s floor', () => {
    expect(adviceIn('It must be above $0.')).toEqual([]);
    expect(adviceIn('Enter $0 on the other line.')).toEqual([]);
    expect(adviceIn('Enter $0')).toEqual([]);
  });
});
