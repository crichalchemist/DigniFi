import {
  intentionRowGap,
  leasePlanRows,
  leaseRowGap,
  openPlanRows,
  plansBody,
  securedPlanRows,
} from '../planRows';
import { fill } from '../../claims/claimNames';
import * as copy from '../../../../../constants/copy';
import gapCases from '../intentionGapCases.json';
import rowCases from '../claimTextRowCases.json';
import type { ContractRow, DebtRow, IntentionAnswers } from '../../../../../types/api';

// Which rows Your Plans asks about and what its save sends must match what the server keeps and
// judges: a row the step shows that the server prunes loses the filer's choice, and a body built
// differently from loaded answers than from typed ones saves on every visit (4e-R2, 4e-R3).

const car: DebtRow = { _key: '7', id: 7, creditor_name: 'Demo Auto Credit', is_secured: true };
const home: DebtRow = { _key: '8', id: 8, creditor_name: 'Demo Home Loans', is_secured: true };
const lease: ContractRow = {
  _key: '4',
  id: 4,
  counterparty_name: 'Demo Leasing',
  contract_type: 'lease',
  description: 'Car lease',
  lease_kind: 'vehicle',
};

describe('the step 9 body', () => {
  it('the body is the same built from loaded answers as from the same answers typed', () => {
    // Loaded: keys in the server's order, a stale id, the read-only date
    const loaded: IntentionAnswers = {
      leases: { 4: { assumed: 'no' } },
      secured: {
        99: { intention: 'surrender' },
        8: { explain: 'I keep paying.', intention: 'retain_explain' },
        7: { intention: 'retain_redeem' },
      },
      answered_on: '2026-11-24',
    };
    // Typed: the same choices, made row by row in the step
    let typed: IntentionAnswers = {};
    typed = { ...typed, secured: { ...typed.secured, 7: { intention: 'retain_redeem' } } };
    typed = { ...typed, secured: { ...typed.secured, 8: { intention: 'retain_explain' } } };
    typed = {
      ...typed,
      secured: { ...typed.secured, 8: { intention: 'retain_explain', explain: 'I keep paying.' } },
    };
    typed = { ...typed, leases: { 4: { assumed: 'no' } } };
    const fromLoaded = plansBody(loaded, [car, home], [lease]);
    expect(JSON.stringify(fromLoaded)).toBe(JSON.stringify(plansBody(typed, [car, home], [lease])));
    expect(fromLoaded).toEqual({
      secured: {
        7: { intention: 'retain_redeem' },
        8: { intention: 'retain_explain', explain: 'I keep paying.' },
      },
      leases: { 4: { assumed: 'no' } },
    });
  });

  it('the body leaves out empty entries, blank words and ids out of scope', () => {
    const answers: IntentionAnswers = {
      secured: {
        7: {},
        8: { intention: 'surrender', explain: '   ' },
        // a debt no longer secured, or gone
        9: { intention: 'retain_reaffirm' },
      },
      leases: { 4: {}, 5: { assumed: 'yes' } },
    };
    expect(plansBody(answers, [car, home], [lease])).toEqual({
      secured: { 8: { intention: 'surrender' } },
      leases: {},
    });
    // Words kept under another choice still go, as typed
    expect(
      plansBody({ secured: { 7: { intention: 'surrender', explain: ' Kept ' } } }, [car], [])
    ).toEqual({ secured: { 7: { intention: 'surrender', explain: ' Kept ' } }, leases: {} });
  });

  it('the body is null with no row in scope', () => {
    expect(plansBody({ secured: { 7: { intention: 'surrender' } } }, [], [])).toBeNull();
  });
});

describe('the rows Your Plans asks about', () => {
  it('a debt is in scope once saved, secured and confirmed', () => {
    const rows: DebtRow[] = [
      car,
      { ...car, _key: 'new-1', id: undefined },
      { ...car, _key: '10', id: 10, is_draft: true },
      { ...car, _key: '11', id: 11, is_secured: false },
      { ...car, _key: '12', id: 12, is_draft: false },
    ];
    expect(securedPlanRows(rows).map((row) => row.id)).toEqual([7, 12]);
  });

  it.each(rowCases.contracts)(
    'a lease of personal property is any lease but residential: $name',
    ({ contract, list }) => {
      const row = { ...lease, ...contract } as ContractRow;
      expect(leasePlanRows([row])).toHaveLength(list === 'leases' ? 1 : 0);
    }
  );

  it('a lease not saved yet is not asked about', () => {
    expect(leasePlanRows([{ ...lease, _key: 'new-1', id: undefined }])).toEqual([]);
  });
});

describe("the browser's gaps are the server's", () => {
  it.each(gapCases)('$name', ({ kind, row, entry, expect: expected }) => {
    const helper = kind === 'secured' ? intentionRowGap : leaseRowGap;
    const sentence = helper(row, entry as never);
    const words = expected === null ? null : (copy as Record<string, unknown>)[expected];
    expect(sentence).toBe(words === null ? null : fill(words as string, { name: row }));
  });

  it('lists each open row in the step order, named as Complete names it', () => {
    const nameless: DebtRow = { ...car, _key: '9', id: 9, creditor_name: '  ' };
    expect(
      openPlanRows({ secured: { 8: { intention: 'surrender' } } }, [car, home, nameless], [lease])
    ).toEqual([
      fill(copy.INTENTION_GAP_NONE, { name: 'Demo Auto Credit' }),
      fill(copy.INTENTION_GAP_NONE, { name: copy.NAMELESS_DEBT }),
      fill(copy.LEASE_GAP_NONE, { name: 'Demo Leasing' }),
    ]);
  });
});
