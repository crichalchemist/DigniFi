import { describe, expect, it } from 'vitest';
import type { ContractRow } from '../../../../../types/api';
import { landlordFromLease, residentialLeases } from '../landlord';

const lease = (changes: Partial<ContractRow> = {}): ContractRow => ({
  _key: 'new-1',
  counterparty_name: 'Gold Coast Example Residential LLC',
  contract_type: 'lease',
  description: 'Residential lease',
  street_address: '850 N State St',
  street_2: 'c/o Management Office',
  city: 'Chicago',
  state: 'IL',
  zip_code: '60610',
  outside_us: false,
  lease_kind: 'residential',
  ...changes,
});

describe("the landlord copied from a lease (Form 101A's five boxes)", () => {
  it('a pick copies every landlord box from the lease, the second street line joined', () => {
    expect(landlordFromLease(lease())).toEqual({
      landlord_name: 'Gold Coast Example Residential LLC',
      landlord_street: '850 N State St, c/o Management Office',
      landlord_city: 'Chicago',
      landlord_state: 'IL',
      landlord_zip: '60610',
    });
  });

  it('a lease outside the US copies no state or ZIP', () => {
    const landlord = landlordFromLease(lease({ outside_us: true, state: 'IL', zip_code: '60610' }));
    expect(landlord.landlord_state).toBeNull();
    expect(landlord.landlord_zip).toBeNull();
    expect(landlord.landlord_city).toBe('Chicago');
  });

  it("a lease's state is copied in capitals and only when the state list has it", () => {
    expect(landlordFromLease(lease({ state: 'il' })).landlord_state).toBe('IL');
    expect(landlordFromLease(lease({ state: 'ZZ' })).landlord_state).toBeNull();
  });

  it("a pick overwrites a typed box with the lease's blank", () => {
    const landlord = landlordFromLease(lease({ city: '  ', street_2: '', zip_code: '' }));
    expect(landlord.landlord_city).toBeNull();
    expect(landlord.landlord_zip).toBeNull();
    expect(landlord.landlord_street).toBe('850 N State St');
  });

  it('only residential leases with a name or a street are offered', () => {
    const rows = [
      lease({ _key: 'a' }),
      lease({ _key: 'b', lease_kind: 'vehicle' }),
      lease({ _key: 'c', contract_type: 'other' }),
      lease({ _key: 'd', counterparty_name: ' ', street_address: ' 1 Demo St ' }),
      lease({ _key: 'e', counterparty_name: '', street_address: '' }),
    ];
    expect(residentialLeases(rows).map(({ key, label }) => [key, label])).toEqual([
      ['a', 'Gold Coast Example Residential LLC'],
      ['d', '1 Demo St'],
    ]);
  });
});
