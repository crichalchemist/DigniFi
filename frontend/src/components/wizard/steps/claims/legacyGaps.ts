import { CLAIM_GAP_LEGACY_OTHER, CLAIM_GAP_LEGACY_VEHICLE } from '../../../../constants/copy';
import type { LegacyField, LegacyPayments } from '../../../../types/api';
import { fill } from './claimNames';
import { formatFigure } from './linkedPayments';
import type { LinkedSums } from './linkedPayments';

export interface LegacyGap {
  field: LegacyField;
  sentence: string;
}

const toCents = (dollars: number) => Math.round(dollars * 100);

/**
 * The stored figures the links don't cover (3c4 R6, R15), the car payment first: the server's
 * legacy gap, in the server's words. Each is shown with Remove and is no gap on Continue (B46).
 */
export function legacyGaps(legacy: LegacyPayments | undefined, sums: LinkedSums): LegacyGap[] {
  const checks: [LegacyField, string, number][] = [
    ['vehicle_payment', CLAIM_GAP_LEGACY_VEHICLE, sums.vehicleTotal],
    ['other_property_mortgages', CLAIM_GAP_LEGACY_OTHER, sums.otherRealProperty],
  ];
  const gaps: LegacyGap[] = [];
  for (const [field, template, linked] of checks) {
    const stored = legacy?.[field];
    if (stored == null) continue;
    const typed = Number(stored);
    if (toCents(typed) <= toCents(linked)) continue;
    gaps.push({
      field,
      sentence: fill(template, { typed: formatFigure(typed), linked: formatFigure(linked) }),
    });
  }
  return gaps;
}
