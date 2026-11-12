/**
 * What the filer entered under each law, for the totals on the exemptions page. Only adds and
 * counts: a total over a law's limit is the same as one under it (3g1 spec §5.4, C-LIMITS b).
 */
import { parseAmount } from '../../utils/parseAmount';
import type { ExemptionLaw } from '../../types/api';
import type { ClaimRow } from './exemptionGaps';

export type LawTotal = {
  label: string;
  dollars: number;
  fairMarketCount: number;
  /** The catalog law's own limit sentence ('' when it names none); null for a typed law */
  limitText: string | null;
};

/** One entry per law used: catalog laws in list order, then typed laws in first-use order */
export function lawTotals(claims: ClaimRow[], laws: ExemptionLaw[]): LawTotal[] {
  const catalog = new Map<string, LawTotal>();
  const typed = new Map<string, LawTotal>();

  const add = (total: LawTotal, row: ClaimRow) => {
    if (row.amount_kind === 'dollars') total.dollars += parseAmount(row.amount) ?? 0;
    if (row.amount_kind === 'fair_market_value') total.fairMarketCount += 1;
  };

  for (const row of claims) {
    if (row.otherLawChosen) {
      const label = row.other_law.trim();
      if (label === '') continue;
      let total = typed.get(label);
      if (!total) {
        total = { label, dollars: 0, fairMarketCount: 0, limitText: null };
        typed.set(label, total);
      }
      add(total, row);
      continue;
    }
    const law = laws.find((candidate) => candidate.key === row.law);
    if (!law) continue;
    let total = catalog.get(law.key);
    if (!total) {
      total = { label: law.citation, dollars: 0, fairMarketCount: 0, limitText: law.limit_text };
      catalog.set(law.key, total);
    }
    add(total, row);
  }

  const inListOrder = laws.flatMap((law) => {
    const total = catalog.get(law.key);
    return total ? [total] : [];
  });
  return [...inListOrder, ...typed.values()];
}
