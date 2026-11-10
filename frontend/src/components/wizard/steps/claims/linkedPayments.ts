import type { AssetInfo, DebtInfo, ExecutoryContract } from '../../../../types/api';

/**
 * The browser's copy of the server's `linked_payments` sums (3c4 R1, narrowed by R8): the sums
 * only, never Schedule J's slots. The browser counts a scanned draft's payment, as Review shows it
 * (R8); the server counts confirmed debts only.
 */
export interface LinkedSums {
  allLinked: number;
  vehicleTotal: number;
  otherRealProperty: number;
  firstMortgage: number;
}

const toCents = (amount: number | null | undefined) => Math.round((amount ?? 0) * 100);

/** A figure as the filer reads it: 1200 is "1,200.00" */
export function formatFigure(dollars: number): string {
  return dollars.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function linkedSums(
  debts: Partial<DebtInfo>[],
  contracts: Partial<ExecutoryContract>[],
  assets: Partial<AssetInfo>[]
): LinkedSums {
  const held = new Map<number, Partial<AssetInfo>>();
  for (const asset of assets) {
    if (asset.id !== undefined) held.set(asset.id, asset);
  }
  const isHome = (asset: Partial<AssetInfo>) =>
    (asset.ab_line === '1' || asset.ab_line === '4') && asset.details?.lives_here === 'yes';
  const isVehicle = (asset: Partial<AssetInfo>) =>
    (asset.ab_line === '3' || asset.ab_line === '4') && !isHome(asset);

  let all = 0;
  let vehicle = 0;
  let otherReal = 0;
  let first = 0;

  for (const debt of debts) {
    const asset = debt.secured_by == null ? undefined : held.get(debt.secured_by);
    if (!debt.is_secured || !asset) continue;
    const cents = toCents(debt.monthly_payment);
    all += cents;
    if (isHome(asset)) {
      if (debt.home_payment_line !== 'additional') first += cents;
    } else if (asset.ab_line === '1') {
      otherReal += cents;
    } else if (isVehicle(asset)) {
      vehicle += cents;
    }
  }

  for (const contract of contracts) {
    const asset = contract.vehicle_asset == null ? undefined : held.get(contract.vehicle_asset);
    if (contract.contract_type !== 'lease' || contract.lease_kind !== 'vehicle' || !asset) continue;
    const cents = toCents(contract.monthly_payment);
    all += cents;
    if (isVehicle(asset)) vehicle += cents;
  }

  return {
    allLinked: all / 100,
    vehicleTotal: vehicle / 100,
    otherRealProperty: otherReal / 100,
    firstMortgage: first / 100,
  };
}
