import { describe, expect, it } from 'vitest';
import { firstCodebtorGap } from '../codebtorGaps';
import { fill } from '../claimNames';
import * as copy from '../../../../../constants/copy';
import type { ClaimAnswers, CodebtorRow, ContractRow, DebtRow } from '../../../../../types/api';

const debts = [{ _key: '30', id: 30, creditor_name: 'Demo Card Services' }] as DebtRow[];
const contracts = [{ _key: '4', id: 4, counterparty_name: 'Demo Motors' }] as ContractRow[];
const answers: ClaimAnswers = { codebtors_answer: 'yes', community_lived: 'no' };
const rohan: CodebtorRow = {
  _key: '3',
  id: 3,
  name: 'Rohan Demo',
  street_address: '2 Demo Ave',
  street_2: '',
  city: 'Chicago',
  state: 'IL',
  zip_code: '60602',
  outside_us: false,
  relationship: '',
  links: [{ kind: 'debt', id: 30 }],
};
const named = { name: 'Rohan Demo' };
const spouseAnswers: ClaimAnswers = {
  ...answers,
  community_lived: 'yes',
  community_spouse_lived_with: 'yes',
  community_state: 'Illinois',
  community_spouse_name: 'Demo Spouse',
  community_spouse_street_address: '1 Demo Way',
  community_spouse_city: 'Chicago',
  community_spouse_state: 'IL',
  community_spouse_zip_code: '60601',
};

const gap = (rows: CodebtorRow[], a: ClaimAnswers) => firstCodebtorGap(rows, a, debts, contracts);

describe('firstCodebtorGap', () => {
  it('has no gap on a complete codebtor and a community answer of No', () => {
    expect(gap([rohan], answers)).toBeNull();
  });

  it.each([
    ['H1: line 1 unanswered', [], {}, copy.CODEBTOR_GAP_NO_ANSWER],
    ['H2: Yes with no one listed', [], answers, copy.CODEBTOR_GAP_YES_BUT_NONE],
    [
      'H3: No with someone listed',
      [rohan],
      { ...answers, codebtors_answer: 'no' },
      copy.CODEBTOR_GAP_NO_BUT_LISTED,
    ],
    [
      'H4: community question unanswered',
      [rohan],
      { codebtors_answer: 'yes' },
      copy.CODEBTOR_GAP_COMMUNITY,
    ],
    [
      'H5: spouse question unanswered',
      [rohan],
      { ...answers, community_lived: 'yes' },
      copy.CODEBTOR_GAP_SPOUSE_LIVED,
    ],
    [
      'H6: community state blank',
      [rohan],
      { ...spouseAnswers, community_state: ' ' },
      copy.CODEBTOR_GAP_SPOUSE_DETAILS,
    ],
    [
      'H6: spouse name blank',
      [rohan],
      { ...spouseAnswers, community_spouse_name: '   ' },
      copy.CODEBTOR_GAP_SPOUSE_DETAILS,
    ],
    [
      'H6: spouse city missing',
      [rohan],
      { ...spouseAnswers, community_spouse_city: '' },
      copy.CODEBTOR_GAP_SPOUSE_DETAILS,
    ],
    ['H7: row with no name', [{ ...rohan, name: ' ' }], answers, copy.CODEBTOR_GAP_NO_NAME],
    [
      'H8: row with no city',
      [{ ...rohan, city: '' }],
      answers,
      fill(copy.CLAIM_GAP_ADDRESS, named),
    ],
    [
      'H8: outside the US with no city',
      [{ ...rohan, outside_us: true, city: '', state: '', zip_code: '' }],
      answers,
      fill(copy.CLAIM_GAP_STREET_CITY, named),
    ],
    ['H9: no links', [{ ...rohan, links: [] }], answers, fill(copy.CODEBTOR_GAP_NO_LINK, named)],
    [
      'H9: a link to a removed amount owed',
      [{ ...rohan, links: [{ kind: 'debt' as const, id: 99 }] }],
      answers,
      fill(copy.CODEBTOR_GAP_NO_LINK, named),
    ],
    [
      'H9: the right id under the wrong kind',
      [{ ...rohan, links: [{ kind: 'contract' as const, id: 30 }] }],
      answers,
      fill(copy.CODEBTOR_GAP_NO_LINK, named),
    ],
  ] as [string, CodebtorRow[], ClaimAnswers, string][])('%s', (_label, rows, a, expected) => {
    expect(gap(rows, a)).toBe(expected);
  });

  it('accepts line 2 answered Yes twice with the state, name and address given', () => {
    expect(gap([rohan], spouseAnswers)).toBeNull();
  });

  it('accepts a spouse address outside the US with no state or ZIP', () => {
    expect(
      gap([rohan], {
        ...spouseAnswers,
        community_spouse_outside_us: true,
        community_spouse_state: '',
        community_spouse_zip_code: '',
      })
    ).toBeNull();
  });

  it('accepts a row outside the US with no state or ZIP', () => {
    expect(gap([{ ...rohan, outside_us: true, state: '', zip_code: '' }], answers)).toBeNull();
  });

  it('puts the question and line 2 before any row', () => {
    expect(gap([{ ...rohan, name: '' }], { codebtors_answer: 'yes' })).toBe(
      copy.CODEBTOR_GAP_COMMUNITY
    );
  });

  it('skips a new row with nothing in it', () => {
    const blankRow = {
      _key: 'new-1',
      name: '',
      street_address: '',
      city: '',
      state: '',
      zip_code: '',
      relationship: '',
    } as CodebtorRow;
    expect(gap([blankRow], answers)).toBe(copy.CODEBTOR_GAP_YES_BUT_NONE);
    expect(gap([blankRow], { ...answers, codebtors_answer: 'no' })).toBeNull();
  });

  it('keeps a stored row that has been cleared of every answer, since the save sends it under its id', () => {
    const cleared = { _key: '3', id: 3 } as CodebtorRow;
    expect(gap([cleared], { ...answers, codebtors_answer: 'no' })).toBe(
      copy.CODEBTOR_GAP_NO_BUT_LISTED
    );
    expect(gap([cleared], answers)).toBe(copy.CODEBTOR_GAP_NO_NAME);
  });

  it('checks rows in id order, a new row last', () => {
    const added = { ...rohan, _key: 'new-2', id: undefined, name: 'Added Demo', city: '' };
    const early = { ...rohan, _key: '2', id: 2, name: 'Early Demo', links: [] };
    const late = { ...rohan, id: 9, _key: '9', name: 'Late Demo', city: '' };
    expect(gap([added, late, early], answers)).toBe(
      fill(copy.CODEBTOR_GAP_NO_LINK, { name: 'Early Demo' })
    );
    expect(gap([added, late], answers)).toBe(fill(copy.CLAIM_GAP_ADDRESS, { name: 'Late Demo' }));
  });

  it('says a nameless row is nameless in the sentence, never with a name', () => {
    expect(gap([{ ...rohan, name: '' }], answers)).toBe(copy.CODEBTOR_GAP_NO_NAME);
  });
});
