/**
 * The household list's relationship words and limits (3e1 spec §4.2), as the server holds them in
 * `apps/intake/household.py`; `test_household_frontend_copy.py` pins the words.
 */
import type { Relationship } from '../types/api';

export const RELATIONSHIP_WORDS: Record<Relationship, string> = {
  spouse: 'Spouse',
  son: 'Son',
  daughter: 'Daughter',
  stepchild: 'Stepchild',
  grandchild: 'Grandchild',
  parent: 'Parent',
  sibling: 'Brother or sister',
  other_relative: 'Other relative',
  unmarried_partner: 'Unmarried partner',
  roommate: 'Roommate',
  other: 'Other',
};

export const MAX_HOUSEHOLD_ROWS = 20;

export const MAX_AGE = 120;
