import { describe, it, expect } from 'vitest';
import {
  isBlankCodebtor,
  isBlankContract,
  isBlankDebt,
  keptRows,
  noDebtsToSend,
  sentDebt,
} from '../claimRows';
import type { CodebtorRow, ContractRow, DebtRow } from '../../types/api';

describe('which claim rows a save carries', () => {
  it.each<[string, Partial<DebtRow>, boolean]>([
    ['a name of spaces', { creditor_name: '  ' }, true],
    ['a name', { creditor_name: 'Demo Card Services' }, false],
    ['an amount of 0', { amount_owed: 0 }, true],
    ['an amount', { amount_owed: 12.5 }, false],
    ['a payment of 0', { monthly_payment: 0 }, false],
    ['a status list of none of these', { claim_status: [] }, false],
    ['an answer of no notice parties', { notice_parties: [] }, false],
    ['a lien with no kind', { lien: { kinds: [], other: '' } }, true],
    ['a lien with a kind', { lien: { kinds: ['judgment'], other: '' }, _key: 'new-1' }, false],
    ['the secured answer', { is_secured: true }, false],
    ['a pressed mark with no answer behind it', { is_secured: false, _securedPressed: true }, true],
    ['the outside-the-US tick', { outside_us: true }, false],
    ['a linked property', { secured_by: 3 }, false],
    ['a debt type', { debt_type: 'medical' }, false],
  ])('treats a new debt row with %s as expected', (_name, change, blank) => {
    expect(isBlankDebt({ _key: 'new-1', ...change })).toBe(blank);
  });

  it.each<[string, Partial<ContractRow>, boolean]>([
    ['a lease type', { contract_type: 'lease' }, false],
    ['a payment of 0', { monthly_payment: 0 }, false],
    ['an owes-now answer', { owes_now: 'no' }, false],
    ['a linked amount owed', { owed_debt: 4 }, false],
    ['the outside-the-US tick', { outside_us: true }, false],
    ['a description of spaces', { description: ' ' }, true],
  ])('treats a new contract row with %s as expected', (_name, change, blank) => {
    const row = {
      _key: 'new-1',
      counterparty_name: '',
      contract_type: '',
      description: '',
      ...change,
    } as ContractRow;
    expect(isBlankContract(row)).toBe(blank);
  });

  it.each<[string, Partial<CodebtorRow>, boolean]>([
    ['a relationship', { relationship: 'friend' }, false],
    ['a link', { links: [{ kind: 'debt', id: 7 }] }, false],
    ['a second address line', { street_2: '2B' }, false],
    ['no links', { links: [] }, true],
  ])('treats a new codebtor row with %s as expected', (_name, change, blank) => {
    const row = {
      _key: 'new-1',
      name: '',
      street_address: '',
      city: '',
      state: '',
      zip_code: '',
      relationship: '',
      ...change,
    } as CodebtorRow;
    expect(isBlankCodebtor(row)).toBe(blank);
  });

  it('keeps a stored row even when it is blank, since a save that left it out would delete it', () => {
    const kept = keptRows([{ _key: '7', id: 7 }, { _key: 'new-1' }], isBlankDebt);
    expect(kept).toEqual([{ _key: '7', id: 7 }]);
  });

  it('sends a blank amount as 0 and a blank payment as null, and never the pressed mark', () => {
    const sent = sentDebt({
      _key: '7',
      id: 7,
      amount_owed: undefined,
      monthly_payment: undefined,
      _securedPressed: true,
    });
    expect(sent).toEqual({
      _key: '7',
      id: 7,
      amount_owed: 0,
      monthly_payment: null,
      debt_type: '',
    });
    expect(sent).not.toHaveProperty('_securedPressed');
  });

  it('sends a blank type as an empty string, which JSON keeps and the server stores', () => {
    expect(sentDebt({ _key: '7', id: 7, debt_type: undefined }).debt_type).toBe('');
    expect(sentDebt({ _key: '7', id: 7, debt_type: 'medical' }).debt_type).toBe('medical');
  });

  it('says no amounts owed only while it is pressed and no row is kept', () => {
    expect(noDebtsToSend([], true)).toBe(true);
    expect(noDebtsToSend([], false)).toBeNull();
    expect(noDebtsToSend([{}], true)).toBeNull();
  });
});
