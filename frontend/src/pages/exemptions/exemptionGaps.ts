/**
 * The exemptions page's copy of the server's `exemption_gaps` (apps/intake/exemptions.py), for
 * Continue. Same order, same sentences (pinned by test_exemption_copy.py), plus one page-only
 * case: a claim row with no property chosen, just added or cleared by the filer (P20). A stored
 * claim whose property was gone when the page opened is gone, as the server says.
 */
import {
  EXEMPTION_GAP_AMOUNT,
  EXEMPTION_GAP_AMOUNT_KIND,
  EXEMPTION_GAP_CHOOSE_ITEM,
  EXEMPTION_GAP_DESCRIPTION,
  EXEMPTION_GAP_ITEM_GONE,
  EXEMPTION_GAP_LAW,
  EXEMPTION_GAP_LAW_CHANGED,
  EXEMPTION_GAP_LINE_1,
  EXEMPTION_GAP_LINE_3,
  EXEMPTION_GAP_LINE_3_1,
  EXEMPTION_GAP_NO_CLAIMS,
  EXEMPTION_GAP_NO_ITEMS,
} from '../../constants/copy';
import { amountError, parseAmount } from '../../utils/parseAmount';
import type { ExemptionAmountKind, ExemptionItem, Exemptions } from '../../types/api';

/** A claim as the page holds it: `_key` stays in the browser, amounts are what was typed */
export type ClaimRow = {
  _key: string;
  id: number | null;
  asset: number | null;
  law: string | null;
  otherLawChosen: boolean;
  other_law: string;
  amount_kind: ExemptionAmountKind | null;
  amount: string;
  short_description: string;
  /**
   * The stored property was gone when the page opened (the claim came back with no property,
   * or one not on the list). Cleared once the filer picks or clears the property, so a property
   * the filer cleared is asked for like a new row's, never called gone.
   */
  itemGone: boolean;
};

/** The server's bound on a claim's amount: DecimalField(12, 2), at or above 0 */
export const CLAIM_AMOUNT_MAX_DIGITS = 12;

/** What is wrong with a dollar amount the server would refuse, or undefined (blank is a gap, not this) */
export function claimAmountError(row: ClaimRow): string | undefined {
  if (row.amount_kind !== 'dollars') return undefined;
  return amountError(parseAmount(row.amount), CLAIM_AMOUNT_MAX_DIGITS);
}

type Answers = Pick<Exemptions, 'line_1' | 'line_3' | 'line_3_1' | 'no_claims'>;

// split/join, not replace: replace reads $&, $' and $` in the filer's own words as patterns
const fillName = (template: string, name: string) => template.split('{name}').join(name);

function claimGap(
  row: ClaimRow,
  item: ExemptionItem | undefined,
  lawKeys: ReadonlySet<string>
): string | null {
  if (!item) return row.itemGone ? EXEMPTION_GAP_ITEM_GONE : EXEMPTION_GAP_CHOOSE_ITEM;
  const { name } = item;
  const typedLaw = row.otherLawChosen && row.other_law.trim() !== '';
  if (row.law === null && !typedLaw) return fillName(EXEMPTION_GAP_LAW, name);
  if (row.law !== null && !lawKeys.has(row.law)) return fillName(EXEMPTION_GAP_LAW_CHANGED, name);
  if (row.amount_kind === null) return fillName(EXEMPTION_GAP_AMOUNT_KIND, name);
  if (row.amount_kind === 'dollars' && row.amount.trim() === '') {
    return fillName(EXEMPTION_GAP_AMOUNT, name);
  }
  if (!item.description_fits && row.short_description.trim() === '') {
    return fillName(EXEMPTION_GAP_DESCRIPTION, name);
  }
  return null;
}

/** The first thing the page still lacks, in the server's words, or null */
export function firstExemptionGap(
  answers: Answers,
  claims: ClaimRow[],
  items: ExemptionItem[],
  lawKeys: ReadonlySet<string>
): string | null {
  if (answers.line_1 === null) return EXEMPTION_GAP_LINE_1;
  if (claims.length === 0 && !answers.no_claims) {
    return items.length > 0 ? EXEMPTION_GAP_NO_CLAIMS : EXEMPTION_GAP_NO_ITEMS;
  }
  const position = new Map(items.map((item, index) => [item.id, index]));
  const byId = new Map(items.map((item) => [item.id, item]));
  // A/B order of the property, then the order added; a claim with no live property goes last
  const ordered = claims
    .map((row, index) => ({ row, index }))
    .sort(
      (a, b) =>
        (position.get(a.row.asset ?? -1) ?? items.length) -
          (position.get(b.row.asset ?? -1) ?? items.length) || a.index - b.index
    );
  for (const { row } of ordered) {
    const gap = claimGap(row, byId.get(row.asset ?? -1), lawKeys);
    if (gap !== null) return gap;
  }
  if (answers.line_3 === null) return EXEMPTION_GAP_LINE_3;
  if (answers.line_3 === 'yes' && answers.line_3_1 === null) return EXEMPTION_GAP_LINE_3_1;
  return null;
}
