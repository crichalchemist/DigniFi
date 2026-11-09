import { describe, expect, it } from 'vitest';
import {
  addressMissing,
  assetLabel,
  asksWho,
  claimRowName,
  inIdOrder,
  linkIsLive,
  type AddressValue,
} from '../claimNames';
import type { AssetInfo, WizardRow } from '../../../../../types/api';

const complete: AddressValue = {
  street_address: '12 Demo Street',
  street_2: '',
  city: 'Demo City',
  state: 'IL',
  zip_code: '60601',
  outside_us: false,
};

describe('an address the court can use', () => {
  it.each<[string, Partial<AddressValue>]>([
    ['a blank street', { street_address: ' ' }],
    ['no city', { city: '' }],
    ['a one-letter state', { state: 'I' }],
    ['a three-letter state', { state: 'ILL' }],
    ['a state with a digit', { state: '1L' }],
    ['no ZIP', { zip_code: '' }],
  ])(
    'counts an address missing until its street, city, two-letter state and ZIP are given: %s',
    (_name, change) => {
      expect(addressMissing({ ...complete, ...change })).toBe(true);
    }
  );

  it('counts a complete address, a lower-case state included, as given', () => {
    expect(addressMissing(complete)).toBe(false);
    expect(addressMissing({ ...complete, state: 'il' })).toBe(false);
  });

  it('needs no state or ZIP once the address is ticked outside the US, but still needs a city', () => {
    const outside = { ...complete, outside_us: true, state: '', zip_code: '' };
    expect(addressMissing(outside)).toBe(false);
    expect(addressMissing({ ...outside, city: '' })).toBe(true);
  });
});

describe('the order the server checks rows in', () => {
  it('puts new rows after stored ones in inIdOrder', () => {
    const rows = [{ k: 'new' }, { id: 9, k: 'nine' }, { id: 4, k: 'four' }, { k: 'new2' }];
    expect(inIdOrder(rows).map((row) => row.k)).toEqual(['four', 'nine', 'new', 'new2']);
  });
});

describe('a link to a row on the Assets step', () => {
  it('reads a link as live only when its row is held', () => {
    expect(linkIsLive(3, [{ id: 3 }])).toBe(true);
    expect(linkIsLive(3, [{ id: 4 }])).toBe(false);
    expect(linkIsLive(null, [{ id: 3 }])).toBe(false);
    expect(linkIsLive(undefined, [])).toBe(false);
  });
});

describe('what a row is called in a sentence', () => {
  it('names a row with no name by the fallback, and a named one by its trimmed name', () => {
    expect(claimRowName('  ', 'one amount owed')).toBe('one amount owed');
    expect(claimRowName(undefined, 'one amount owed')).toBe('one amount owed');
    expect(claimRowName(' Demo Card Services ', 'one amount owed')).toBe('Demo Card Services');
  });
});

describe('who a property question asks', () => {
  it.each([
    ['place', true],
    ['vehicle', true],
    ['vehicle_no_mileage', true],
    ['item', false],
    ['cash', false],
    [undefined, false],
  ] as const)(
    '%s asks: %s (an old row with no line asks no who, as on the server)',
    (shape, asks) => {
      expect(asksWho(shape)).toBe(asks);
    }
  );
});

describe('a property in the picker', () => {
  const row = (fields: Partial<AssetInfo>): WizardRow<AssetInfo> => ({
    _key: 'x',
    id: 3,
    ...fields,
  });

  it('tells two Hondas apart by year, make and model', () => {
    expect(
      assetLabel(row({ ab_line: '3', details: { year: '2019', make: 'Honda', model: 'CR-V EX' } }))
    ).toBe('Line 3: 2019 Honda CR-V EX');
    expect(
      assetLabel(row({ ab_line: '3', details: { year: '', make: 'Honda', model: 'CR-V EX' } }))
    ).toBe('Line 3: Honda CR-V EX');
    expect(assetLabel(row({ ab_line: '4', details: { make: 'Keystone' } }))).toBe(
      'Line 4: Keystone'
    );
  });

  it('falls back to the row’s own name when a vehicle has no year, make or model', () => {
    expect(assetLabel(row({ ab_line: '3', details: {}, description: '2019 Demo Corolla' }))).toBe(
      'Line 3: 2019 Demo Corolla'
    );
  });

  it('names a home by its street', () => {
    expect(assetLabel(row({ ab_line: '1', details: { street: '12 Demo Street' } }))).toBe(
      'Line 1: 12 Demo Street'
    );
  });
});
