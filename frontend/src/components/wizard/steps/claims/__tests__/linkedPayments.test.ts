import { describe, it, expect } from 'vitest';
import raw from '../linkedPaymentCases.json?raw';
import { linkedSums, formatFigure } from '../linkedPayments';
import type { AssetInfo, DebtInfo, ExecutoryContract } from '../../../../../types/api';

interface CaseAsset {
  line: string;
  lives_here: 'yes' | 'no' | null;
}
interface CaseDebt {
  secured: boolean;
  asset: number;
  payment: string | null;
  home_payment_line: 'first' | 'additional' | null;
}
interface CaseContract {
  contract_type: string;
  lease_kind: string | null;
  asset: number;
  payment: string | null;
}
interface Case {
  name: string;
  assets: CaseAsset[];
  debts: CaseDebt[];
  contracts: CaseContract[];
  expect: {
    allLinked: string;
    vehicleTotal: string;
    otherRealProperty: string;
    firstMortgage: string;
  };
}

// The same table backend/apps/intake/tests/test_linked_payments.py runs against the server.
const cases: Case[] = JSON.parse(raw);

const payment = (value: string | null) => (value === null ? null : Number(value));

function assetsOf(list: CaseAsset[]): Partial<AssetInfo>[] {
  return list.map((a, i) => ({
    id: i + 1,
    ab_line: a.line,
    details: { lives_here: a.lives_here },
  }));
}

function sumsOf(c: Case) {
  const debts = c.debts.map(
    (d) =>
      ({
        is_secured: d.secured,
        secured_by: d.asset + 1,
        monthly_payment: payment(d.payment),
        home_payment_line: d.home_payment_line,
      }) as unknown as Partial<DebtInfo>
  );
  const contracts = c.contracts.map(
    (k) =>
      ({
        contract_type: k.contract_type,
        lease_kind: k.lease_kind,
        vehicle_asset: k.asset + 1,
        monthly_payment: payment(k.payment),
      }) as unknown as Partial<ExecutoryContract>
  );
  return linkedSums(debts, contracts, assetsOf(c.assets));
}

describe('the browser adds linked payments as the server does', () => {
  it('reads the whole shared case table', () => {
    expect(cases.length).toBeGreaterThanOrEqual(16);
  });

  it.each(cases)('$name matches the server', (c) => {
    const sums = sumsOf(c);
    expect(formatFigure(sums.allLinked)).toBe(c.expect.allLinked);
    expect(formatFigure(sums.vehicleTotal)).toBe(c.expect.vehicleTotal);
    expect(formatFigure(sums.otherRealProperty)).toBe(c.expect.otherRealProperty);
    expect(formatFigure(sums.firstMortgage)).toBe(c.expect.firstMortgage);
  });

  it("counts a scanned draft's payment", () => {
    const sums = linkedSums(
      [{ is_secured: true, secured_by: 1, monthly_payment: 350, is_draft: true }],
      [],
      [{ id: 1, ab_line: '3' }]
    );
    expect(sums.allLinked).toBe(350);
  });

  it('counts a link to a removed row as no link', () => {
    const sums = linkedSums(
      [{ is_secured: true, secured_by: 99, monthly_payment: 350 }],
      [],
      [{ id: 1, ab_line: '3' }]
    );
    expect(sums.allLinked).toBe(0);
  });

  it('adds cents without drift', () => {
    const debt = (monthly_payment: number): Partial<DebtInfo> => ({
      is_secured: true,
      secured_by: 1,
      monthly_payment,
    });
    const sums = linkedSums([debt(0.1), debt(0.2), debt(0.3)], [], [{ id: 1, ab_line: '3' }]);
    expect(sums.allLinked).toBe(0.6);
    expect(formatFigure(sums.allLinked)).toBe('0.60');
  });
});
