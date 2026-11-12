/**
 * Totals by law (3g1 spec §5.4). Business intent: the filer sees what they entered under each law,
 * beside the law's own limit, and a total over a limit is never treated differently from one under it.
 */
import { describe, expect, it } from 'vitest';
import { lawTotals } from '../lawTotals';
import type { ClaimRow } from '../exemptionGaps';
import type { ExemptionLaw } from '../../../types/api';

const LAWS: ExemptionLaw[] = [
  { key: 'a', citation: '1 ILCS 1/a', jurisdiction: 'illinois', limit_text: 'Up to $4,000.' },
  { key: 'b', citation: '1 ILCS 1/b', jurisdiction: 'illinois', limit_text: '' },
  { key: 'c', citation: '1 U.S.C. § 1', jurisdiction: 'federal', limit_text: 'Up to $9.' },
];

let counter = 0;
const claim = (overrides: Partial<ClaimRow>): ClaimRow => ({
  _key: `new-${counter++}`,
  id: null,
  asset: 1,
  law: null,
  otherLawChosen: false,
  other_law: '',
  amount_kind: 'dollars',
  amount: '',
  short_description: '',
  ...overrides,
});

describe('lawTotals', () => {
  it('adds each law’s dollars and counts its 100% rows, in list order, typed laws last', () => {
    const totals = lawTotals(
      [
        claim({ otherLawChosen: true, other_law: ' My Law ', amount: '10' }),
        claim({ law: 'c', amount: '1.50' }),
        claim({ law: 'a', amount: '100.25' }),
        claim({ law: 'a', amount: '50' }),
        claim({ law: 'a', amount_kind: 'fair_market_value' }),
        claim({ otherLawChosen: true, other_law: 'My Law', amount: '5' }),
        claim({ otherLawChosen: true, other_law: 'Another', amount_kind: 'fair_market_value' }),
      ],
      LAWS
    );
    expect(totals).toEqual([
      { label: '1 ILCS 1/a', dollars: 150.25, fairMarketCount: 1, limitText: 'Up to $4,000.' },
      { label: '1 U.S.C. § 1', dollars: 1.5, fairMarketCount: 0, limitText: 'Up to $9.' },
      { label: 'My Law', dollars: 15, fairMarketCount: 0, limitText: null },
      { label: 'Another', dollars: 0, fairMarketCount: 1, limitText: null },
    ]);
  });

  it('leaves a refused amount out, so it can never lower or raise a total', () => {
    const totals = lawTotals(
      [claim({ law: 'a', amount: '7' }), claim({ law: 'a', amount: '-5' })],
      LAWS
    );
    expect(totals).toEqual([
      { label: '1 ILCS 1/a', dollars: 7, fairMarketCount: 0, limitText: 'Up to $4,000.' },
    ]);
  });

  it('counts a blank dollar box as nothing', () => {
    const totals = lawTotals(
      [claim({ law: 'b', amount: '' }), claim({ law: 'b', amount: '7' })],
      LAWS
    );
    expect(totals).toEqual([
      { label: '1 ILCS 1/b', dollars: 7, fairMarketCount: 0, limitText: '' },
    ]);
  });
});
