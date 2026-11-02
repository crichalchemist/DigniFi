/**
 * The household list's rows as the wizard holds and sends them (3e1 spec §4.2, §8.2). A row has
 * the server's shape plus the browser's own `_key`, which never reaches the server.
 */
import type { HouseholdMember, WizardRow } from '../types/api';

type MemberRow = WizardRow<HouseholdMember>;

// The last new row's key: unique while the page is open, and the prefix keeps it apart from a
// loaded row's key, which is its id
let lastKey = 0;

/** A row the filer or the wizard adds, every question unanswered unless given */
export function newHouseholdMember(answers: Partial<HouseholdMember> = {}): MemberRow {
  return {
    _key: `new-${++lastKey}`,
    relationship: null,
    age: null,
    lives_with_you: null,
    claimed_or_supported: null,
    ...answers,
  };
}

/** Whether the row is saved, or the filer (or the wizard) has answered anything on it */
export function isTouched(row: MemberRow): boolean {
  return (
    row.id !== undefined ||
    [row.relationship, row.age, row.lives_with_you, row.claimed_or_supported].some(
      (answer) => answer != null
    )
  );
}

/**
 * The row in the server's order, with null for a missing answer and the spouse's question on the
 * spouse's row only. Bodies and saved copies both pass through it, so an id a save writes into a
 * row (last, by `withSavedIds`) doesn't make the next body differ and save again.
 */
export function sentMember(row: MemberRow): MemberRow {
  const sent: MemberRow = { _key: row._key };
  if (row.id !== undefined) sent.id = row.id;
  sent.relationship = row.relationship ?? null;
  sent.age = row.age ?? null;
  sent.lives_with_you = row.lives_with_you ?? null;
  sent.claimed_or_supported = row.claimed_or_supported ?? null;
  if (row.relationship === 'spouse') sent.spouse_is_dependent = row.spouse_is_dependent ?? null;
  return sent;
}

/**
 * The list a save sends: every touched row, in order. With none, `[]` only when the filer said no
 * one else lives with them or depends on them, and null (unanswered) otherwise, so a save never
 * empties a list the filer didn't.
 */
export function membersToSend(rows: MemberRow[], noOneElse: boolean): MemberRow[] | null {
  const touched = rows.filter(isTouched).map(sentMember);
  if (touched.length > 0) return touched;
  return noOneElse ? [] : null;
}
