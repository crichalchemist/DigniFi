/**
 * Form 101A's landlord, copied from a residential lease the filer listed on the same step (4b2-R7).
 * A pick writes all five boxes, so an old landlord's city never sits under a new landlord's street.
 */
import type { ContractRow, PetitionAnswers } from '../../../../types/api';
import { zipDigits } from './masks';
import type { LANDLORD_KEYS } from './petitionGaps';
import { US_STATES_AND_TERRITORIES } from './usStates';

type Landlord = Pick<PetitionAnswers, (typeof LANDLORD_KEYS)[number]>;

const orNull = (value: string | undefined | null): string | null => value?.trim() || null;

/** The lease's name, else its street, for the select; a row with neither is not offered */
const labelOf = (row: ContractRow): string =>
  row.counterparty_name.trim() || (row.street_address ?? '').trim();

/** The residential leases a landlord can be copied from */
export function residentialLeases(
  rows: ContractRow[]
): { key: string; label: string; row: ContractRow }[] {
  return rows
    .filter((row) => row.contract_type === 'lease' && row.lease_kind === 'residential')
    .map((row) => ({ key: row._key, label: labelOf(row), row }))
    .filter((lease) => lease.label !== '');
}

/** Every landlord box from one lease: a blank on the lease blanks the box (4b2-R7) */
export function landlordFromLease(row: ContractRow): Landlord {
  const street = [row.street_address, row.street_2]
    .map((part) => (part ?? '').trim())
    .filter((part) => part !== '')
    .join(', ');
  const state = (row.state ?? '').trim().toUpperCase();
  const known = US_STATES_AND_TERRITORIES.some((option) => option.value === state);
  const abroad = row.outside_us === true;
  return {
    landlord_name: orNull(row.counterparty_name),
    landlord_street: street || null,
    landlord_city: orNull(row.city),
    landlord_state: !abroad && known ? state : null,
    landlord_zip: abroad ? null : zipDigits(row.zip_code ?? '') || null,
  };
}
