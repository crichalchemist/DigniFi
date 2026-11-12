import { describe, expect, it } from 'vitest';
import { debtRowGaps, firstDebtGap } from '../debtGaps';
import { fill } from '../claimNames';
import * as copy from '../../../../../constants/copy';
import type { AssetInfo, DebtRow, WizardRow } from '../../../../../types/api';

const NAME = { name: 'Demo Card Services' };

const complete: DebtRow = {
  _key: 'a',
  id: 1,
  debt_type: 'credit_card',
  creditor_name: 'Demo Card Services',
  amount_owed: 500,
  monthly_payment: null as unknown as undefined,
  is_secured: false,
  street_address: '12 Demo Street',
  street_2: '',
  city: 'Demo City',
  state: 'IL',
  zip_code: '60601',
  outside_us: false,
  claim_status: [],
  offset_answer: 'no',
  priority_answer: 'no',
  notice_parties: [],
  secured_by: null,
  lien: null,
  collateral_description: '',
};

const car: WizardRow<AssetInfo> = { _key: '3', id: 3, ab_line: '3', details: { make: 'Demo' } };

const secured: DebtRow = {
  ...complete,
  debt_type: 'auto_loan',
  is_secured: true,
  secured_by: 3,
  collateral_description: '2014 Demo Sedan',
  lien: { kinds: ['agreement'], other: '' },
  monthly_payment: 0,
  offset_answer: null,
};

const emptyParty = {
  name: '',
  street_address: '',
  street_2: '',
  city: '',
  state: '',
  zip_code: '',
  outside_us: false,
  last_4: '',
};

describe('what the Amounts Owed step still lacks', () => {
  it('says nothing for a complete row, a no-debts answer with no rows, and a draft with every answer', () => {
    expect(firstDebtGap([complete], false, [])).toBeNull();
    expect(firstDebtGap([secured], false, [car])).toBeNull();
    expect(firstDebtGap([], true, [])).toBeNull();
    expect(firstDebtGap([{ ...complete, is_draft: true }], false, [])).toBeNull();
  });

  const L = (c: string) => c;
  it.each<[string, () => string | null, string]>([
    ['D1', () => firstDebtGap([], false, []), L(copy.DEBT_GAP_NO_ANSWER)],
    [
      'D1 counts only kept rows',
      () => firstDebtGap([{ _key: 'new-1' }], false, []),
      L(copy.DEBT_GAP_NO_ANSWER),
    ],
    ['D2', () => firstDebtGap([complete], true, []), L(copy.DEBT_GAP_NONE_BUT_LISTED)],
    [
      'D3',
      () => firstDebtGap([{ ...complete, creditor_name: '' }], false, []),
      copy.DEBT_GAP_NO_NAME,
    ],
    [
      'D4',
      () => firstDebtGap([{ ...complete, debt_type: undefined }], false, []),
      fill(copy.CLAIM_GAP_KIND, NAME),
    ],
    [
      'D5',
      () => firstDebtGap([{ ...complete, amount_owed: 0 }], false, []),
      fill(copy.DEBT_GAP_AMOUNT, NAME),
    ],
    [
      'D6',
      () => firstDebtGap([{ ...complete, street_address: '' }], false, []),
      fill(copy.CLAIM_GAP_ADDRESS, NAME),
    ],
    [
      'D6 outside the US',
      () =>
        firstDebtGap(
          [{ ...complete, outside_us: true, state: '', zip_code: '', city: '' }],
          false,
          []
        ),
      fill(copy.CLAIM_GAP_STREET_CITY, NAME),
    ],
    [
      'D7',
      () => firstDebtGap([{ ...secured, secured_by: 9 }], false, [car]),
      fill(copy.DEBT_GAP_PROPERTY, NAME),
    ],
    [
      'D8',
      () => firstDebtGap([{ ...secured, collateral_description: ' ' }], false, [car]),
      fill(copy.DEBT_GAP_DESCRIBE, NAME),
    ],
    [
      'D9',
      () => firstDebtGap([{ ...secured, lien: null }], false, [car]),
      fill(copy.DEBT_GAP_LIEN, NAME),
    ],
    [
      'D10',
      () => firstDebtGap([{ ...secured, lien: { kinds: ['other'], other: ' ' } }], false, [car]),
      fill(copy.DEBT_GAP_LIEN_OTHER, NAME),
    ],
    [
      'D11',
      () =>
        firstDebtGap([{ ...secured, monthly_payment: null as unknown as undefined }], false, [car]),
      fill(copy.DEBT_GAP_PAYMENT, NAME),
    ],
    [
      'D11 on an emptied payment box',
      () => firstDebtGap([{ ...secured, monthly_payment: undefined }], false, [car]),
      fill(copy.DEBT_GAP_PAYMENT, NAME),
    ],
    [
      'D12',
      () => firstDebtGap([secured], false, [{ ...car, details: { lives_here: 'yes' } }]),
      fill(copy.DEBT_GAP_HOME_LINE, NAME),
    ],
    [
      'D13 on an item',
      () =>
        firstDebtGap([secured], false, [
          { _key: '3', id: 3, ab_line: '6', description: 'Demo Piano' },
        ]),
      fill(copy.DEBT_GAP_WHO, NAME),
    ],
    [
      'D13 on an old row with no line',
      () => firstDebtGap([secured], false, [{ _key: '3', id: 3, description: 'Old couch' }]),
      fill(copy.DEBT_GAP_WHO, NAME),
    ],
    [
      'D14',
      () => firstDebtGap([{ ...complete, claim_status: null }], false, []),
      fill(copy.DEBT_GAP_STATUS, NAME),
    ],
    [
      'D15',
      () => firstDebtGap([{ ...complete, offset_answer: null }], false, []),
      fill(copy.DEBT_GAP_OFFSET, NAME),
    ],
    [
      'priority unanswered',
      () => firstDebtGap([{ ...complete, priority_answer: null }], false, []),
      fill(copy.DEBT_GAP_PRIORITY, NAME),
    ],
    [
      'priority Other with no words',
      () =>
        firstDebtGap(
          [{ ...complete, priority_answer: 'other', priority_other: ' ', past_due_amount: 0 }],
          false,
          []
        ),
      fill(copy.DEBT_GAP_PRIORITY_OTHER, NAME),
    ],
    [
      'priority kind with no past-due amount',
      () =>
        firstDebtGap(
          [{ ...complete, priority_answer: 'taxes', past_due_amount: undefined }],
          false,
          []
        ),
      fill(copy.DEBT_GAP_PAST_DUE, NAME),
    ],
    [
      'D16',
      () => firstDebtGap([{ ...complete, notice_parties: null }], false, []),
      fill(copy.DEBT_GAP_NOTICE, NAME),
    ],
    [
      'D17',
      () => firstDebtGap([{ ...complete, notice_parties: [emptyParty] }], false, []),
      fill(copy.DEBT_GAP_NOTICE_PARTY, NAME),
    ],
  ])('%s', (_label, run, expected) => {
    expect(run()).toBe(expected);
  });

  it('is satisfied once a home loan says first, since a home asks who itself', () => {
    const home = { ...car, ab_line: '1', details: { lives_here: 'yes' as const } };
    expect(firstDebtGap([{ ...secured, home_payment_line: 'first' }], false, [home])).toBeNull();
  });

  it('asks nothing about who on a vehicle, which asks it itself', () => {
    expect(firstDebtGap([secured], false, [car])).toBeNull();
  });

  it('does not ask offset of a secured row', () => {
    expect(debtRowGaps({ ...secured, offset_answer: null }, [car])).toEqual([]);
  });

  it.each<[string, Partial<DebtRow>]>([
    ['No', { priority_answer: 'no' }],
    ['Not sure', { priority_answer: 'not_sure', priority_other: ' ' }],
    [
      'a kind with a blank split and 0 past due',
      { priority_answer: 'domestic_support', past_due_amount: 0 },
    ],
  ])('asks nothing more after %s', (_name, change) => {
    expect(debtRowGaps({ ...complete, ...change }, [])).toEqual([]);
  });

  it('does not ask the priority question of a secured row', () => {
    expect(debtRowGaps({ ...secured, priority_answer: null }, [car])).toEqual([]);
  });

  it('says the priority gaps after offset and before the notice answer', () => {
    expect(
      debtRowGaps(
        {
          ...complete,
          offset_answer: null,
          priority_answer: 'other',
          priority_other: '',
          past_due_amount: undefined,
          notice_parties: null,
        },
        []
      )
    ).toEqual([
      fill(copy.DEBT_GAP_OFFSET, NAME),
      fill(copy.DEBT_GAP_PRIORITY_OTHER, NAME),
      fill(copy.DEBT_GAP_PAST_DUE, NAME),
      fill(copy.DEBT_GAP_NOTICE, NAME),
    ]);
  });

  it('lists a nameless row’s gaps in its own words', () => {
    expect(debtRowGaps({ ...complete, creditor_name: '', amount_owed: 0 }, [])).toEqual([
      copy.DEBT_GAP_NO_NAME,
      copy.DEBT_GAP_AMOUNT_NO_NAME,
    ]);
    expect(debtRowGaps({ ...complete, creditor_name: '', street_address: '' }, [])).toEqual([
      copy.DEBT_GAP_NO_NAME,
      copy.DEBT_GAP_ADDRESS_NO_NAME,
    ]);
    expect(
      debtRowGaps(
        { ...complete, creditor_name: '', outside_us: true, state: '', zip_code: '', city: '' },
        []
      )
    ).toEqual([copy.DEBT_GAP_NO_NAME, copy.DEBT_GAP_STREET_CITY_NO_NAME]);
  });

  it('reports the first gap of the first row before any gap of the next', () => {
    expect(
      firstDebtGap(
        [
          { ...complete, city: '' },
          { ...complete, id: 2, creditor_name: '' },
        ],
        false,
        []
      )
    ).toBe(fill(copy.CLAIM_GAP_ADDRESS, NAME));
  });

  it('ignores a new row with nothing in it', () => {
    expect(firstDebtGap([complete, { _key: 'new-2' }], false, [])).toBeNull();
  });

  it('treats a link to a row removed on Assets as no link', () => {
    expect(firstDebtGap([secured], false, [])).toBe(fill(copy.DEBT_GAP_PROPERTY, NAME));
  });
});
