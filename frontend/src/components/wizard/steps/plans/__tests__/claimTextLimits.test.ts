import { rowCap, rowList, tooLongNote } from '../../../../../constants/claimTextLimits';
import * as copy from '../../../../../constants/copy';
import { fill } from '../../claims/claimNames';
import rowCases from '../claimTextRowCases.json';
import type { ContractRow, DebtRow } from '../../../../../types/api';

// A box note must count against the same box the server measures: the row's own list decides it,
// so an unsecured debt's long name never reads as too long for Schedule D (4e-R4).

describe('the list a row is measured in', () => {
  it.each(rowCases.debts)('a debt: $name', ({ debt, list }) => {
    expect(rowList(debt as Pick<DebtRow, 'is_secured' | 'priority_answer'>)).toBe(list);
  });

  it.each(rowCases.contracts)('a contract: $name', ({ contract, list }) => {
    expect(rowList(contract as Pick<ContractRow, 'contract_type' | 'lease_kind'>)).toBe(list);
  });
});

describe("each row's cap", () => {
  it("is the smallest of its own list's boxes, with the forms holding it", () => {
    expect(rowCap('creditor_name', { is_secured: true })).toEqual({
      cap: 43,
      forms: ['schedule_d'],
    });
    expect(rowCap('creditor_name', { is_secured: false, priority_answer: 'no' })).toEqual({
      cap: 70,
      forms: ['schedule_e_f'],
    });
    expect(rowCap('collateral_description', { is_secured: false })).toBeNull();
    expect(rowCap('description', { contract_type: 'contract', lease_kind: null })).toBeNull();
  });

  it('counts characters as the server does, one a code point', () => {
    const secured = { is_secured: true };
    expect(tooLongNote('creditor_name', secured, '😀'.repeat(43))).toBeNull();
    expect(tooLongNote('creditor_name', secured, '😀'.repeat(44))).toBe(
      fill(copy.SCHEDULE_I_DETAIL_TOO_LONG, {
        label: copy.CLAIM_TEXT_LABELS.creditor_name,
        form: 'Schedule D',
      })
    );
  });

  it("names the form holding the row's cap, and trims only the explanation", () => {
    const residential = { contract_type: 'lease' as const, lease_kind: 'residential' as const };
    expect(tooLongNote('description', residential, 'x'.repeat(302))).toBe(
      fill(copy.SCHEDULE_I_DETAIL_TOO_LONG, {
        label: copy.CLAIM_TEXT_LABELS.description,
        form: 'Schedule G',
      })
    );
    expect(tooLongNote('creditor_name', { is_secured: true }, ` ${'x'.repeat(43)}`)).not.toBeNull();
    expect(tooLongNote('explain', { is_secured: true }, ` ${'x'.repeat(62)} `)).toBeNull();
  });
});
