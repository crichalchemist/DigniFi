import { contractRowGaps, firstContractGap } from '../contractGaps';
import { fill } from '../claimNames';
import * as copy from '../../../../../constants/copy';
import type { AssetInfo, ContractRow, DebtRow, WizardRow } from '../../../../../types/api';

const assets: WizardRow<AssetInfo>[] = [
  {
    _key: '20',
    id: 20,
    ab_line: '3',
    description: '',
    details: { year: '2019', make: 'Demo', model: 'Corolla' },
  },
  {
    _key: '22',
    id: 22,
    ab_line: '4',
    description: 'Demo Park trailer',
    details: { lives_here: 'yes' },
  },
];
const debts: DebtRow[] = [
  {
    _key: '30',
    id: 30,
    creditor_name: 'Demo Auto Credit',
    is_secured: true,
    secured_by: 20,
    monthly_payment: 389,
  },
];
const lease: ContractRow = {
  _key: '4',
  id: 4,
  counterparty_name: 'Demo Motors',
  street_address: '1 Demo St',
  street_2: '',
  city: 'Chicago',
  state: 'IL',
  zip_code: '60601',
  outside_us: false,
  contract_type: 'lease',
  description: 'Car lease',
  lease_kind: 'vehicle',
  vehicle_asset: 20,
  monthly_payment: 389,
  owes_now: 'no',
  owed_debt: null,
};
const words = { name: 'Demo Motors' };
const gap = (rows: ContractRow[], answer: 'yes' | 'no' | null = 'yes') =>
  firstContractGap(rows, answer, debts, assets);

describe('firstContractGap', () => {
  it('has no gap on a complete vehicle lease', () => {
    expect(gap([lease])).toBeNull();
  });

  it.each([
    ['C1 no answer', [lease], null, copy.CONTRACT_GAP_NO_ANSWER],
    ['C2 yes with no rows', [], 'yes', copy.CONTRACT_GAP_YES_BUT_NONE],
    ['C3 no with rows', [lease], 'no', copy.CONTRACT_GAP_NO_BUT_LISTED],
    ['C4 no name', [{ ...lease, counterparty_name: ' ' }], 'yes', copy.CONTRACT_GAP_NO_NAME],
    ['C5 no city', [{ ...lease, city: '' }], 'yes', fill(copy.CLAIM_GAP_ADDRESS, words)],
    [
      'C5 outside the US with no city',
      [{ ...lease, outside_us: true, state: '', zip_code: '', city: '' }],
      'yes',
      fill(copy.CLAIM_GAP_STREET_CITY, words),
    ],
    [
      'C5 outside the US, state and ZIP empty',
      [{ ...lease, outside_us: true, state: '', zip_code: '' }],
      'yes',
      null,
    ],
    [
      'C6 no kind',
      [{ ...lease, contract_type: '' as const }],
      'yes',
      fill(copy.CLAIM_GAP_KIND, words),
    ],
    [
      'C7 no purpose',
      [{ ...lease, description: ' ' }],
      'yes',
      fill(copy.CONTRACT_GAP_PURPOSE, words),
    ],
    [
      'C8 no lease kind',
      [{ ...lease, lease_kind: null }],
      'yes',
      fill(copy.CONTRACT_GAP_LEASE_KIND, words),
    ],
    [
      'C9 no vehicle',
      [{ ...lease, vehicle_asset: null }],
      'yes',
      fill(copy.CONTRACT_GAP_VEHICLE, words),
    ],
    [
      'C9 a removed vehicle',
      [{ ...lease, vehicle_asset: 99 }],
      'yes',
      fill(copy.CONTRACT_GAP_VEHICLE, words),
    ],
    [
      'C10 no payment',
      [{ ...lease, monthly_payment: null }],
      'yes',
      fill(copy.CONTRACT_GAP_PAYMENT, words),
    ],
    ['C10 a payment of 0', [{ ...lease, monthly_payment: 0 }], 'yes', null],
    [
      'C11 no owes-now answer',
      [{ ...lease, owes_now: null }],
      'yes',
      fill(copy.CONTRACT_GAP_OWES_NOW, words),
    ],
    [
      'C12 owes now, no amount owed',
      [{ ...lease, owes_now: 'yes' as const, owed_debt: null }],
      'yes',
      fill(copy.CONTRACT_GAP_OWED_DEBT, words),
    ],
    [
      'C12 owes now, a removed amount owed',
      [{ ...lease, owes_now: 'yes' as const, owed_debt: 99 }],
      'yes',
      fill(copy.CONTRACT_GAP_OWED_DEBT, words),
    ],
    [
      'C13 the same vehicle with two payments',
      [{ ...lease, owes_now: 'yes' as const, owed_debt: 30 }],
      'yes',
      fill(copy.CONTRACT_GAP_SAME_VEHICLE, { name: 'Demo Motors', debt: 'Demo Auto Credit' }),
    ],
    [
      'C13 clears when the lease payment is 0',
      [{ ...lease, owes_now: 'yes' as const, owed_debt: 30, monthly_payment: 0 }],
      'yes',
      null,
    ],
  ])('%s', (_name, rows, answer, expected) => {
    expect(gap(rows as ContractRow[], answer as 'yes' | 'no' | null)).toBe(expected);
  });

  it('does not raise C13 when the debt is not secured', () => {
    const unsecured: DebtRow[] = [{ ...debts[0], is_secured: false }];
    const row = { ...lease, owes_now: 'yes' as const, owed_debt: 30 };
    expect(firstContractGap([row], 'yes', unsecured, assets)).toBeNull();
  });

  it("names the first gap in the table's order, not the last", () => {
    expect(gap([{ ...lease, counterparty_name: '', city: '' }])).toBe(copy.CONTRACT_GAP_NO_NAME);
  });

  it('skips a new row with nothing in it, as the body leaves it out', () => {
    const blankRow: ContractRow = {
      _key: 'new-1',
      counterparty_name: '',
      contract_type: '',
      description: '',
      street_address: '',
      street_2: '',
      city: '',
      state: '',
      zip_code: '',
      outside_us: false,
      lease_kind: null,
      monthly_payment: null,
      vehicle_asset: null,
      owes_now: null,
      owed_debt: null,
    };
    expect(gap([blankRow], 'no')).toBeNull();
    expect(gap([blankRow], 'yes')).toBe(copy.CONTRACT_GAP_YES_BUT_NONE);
  });

  it('checks rows in id order, a new row last', () => {
    const nine = { ...lease, _key: '9', id: 9, counterparty_name: 'Nine Co', city: '' };
    const four = { ...lease, _key: '4', id: 4, counterparty_name: 'Four Co', description: '' };
    expect(gap([nine, four])).toBe(fill(copy.CONTRACT_GAP_PURPOSE, { name: 'Four Co' }));
  });

  it('keeps a stored row that has been cleared of every answer, since the save sends it under its id', () => {
    const cleared = { _key: '4', id: 4 } as ContractRow;
    expect(gap([cleared], 'no')).toBe(copy.CONTRACT_GAP_NO_BUT_LISTED);
    expect(gap([cleared], 'yes')).toBe(copy.CONTRACT_GAP_NO_NAME);
  });

  it('words the vehicle sentences for a lease with no name', () => {
    const nameless = { ...lease, counterparty_name: '' };
    const noVehicle = contractRowGaps({ ...nameless, vehicle_asset: null }, debts, assets);
    const sameVehicle = contractRowGaps(
      { ...nameless, owes_now: 'yes' as const, owed_debt: 30 },
      debts,
      assets
    );
    const debt = 'Demo Auto Credit';
    expect(noVehicle).toContain(copy.CONTRACT_GAP_VEHICLE_NO_NAME);
    expect(sameVehicle).toContain(fill(copy.CONTRACT_GAP_SAME_VEHICLE_NO_NAME, { debt }));
    expect(noVehicle).not.toContain(
      fill(copy.CONTRACT_GAP_VEHICLE, { name: copy.NAMELESS_CONTRACT })
    );
    expect(sameVehicle).not.toContain(
      fill(copy.CONTRACT_GAP_SAME_VEHICLE, { name: copy.NAMELESS_CONTRACT, debt })
    );
  });
});
