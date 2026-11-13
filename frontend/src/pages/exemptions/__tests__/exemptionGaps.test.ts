/**
 * The page's copy of the server's exemption gaps (3g1 spec §5.5, P6, P14, P20). Business intent:
 * Continue stays held on exactly the answers Schedule C would refuse, in the server's words and
 * order, and a claim the filer has only just added is never called "gone".
 */
import { describe, expect, it } from 'vitest';
import { firstExemptionGap, type ClaimRow } from '../exemptionGaps';
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
  EXEMPTIONS_NOT_CLAIMING_BUTTON,
} from '../../../constants/copy';
import type { ExemptionItem } from '../../../types/api';

const CIVIC: ExemptionItem = {
  id: 1,
  name: 'Honda Civic 2015',
  line_label: '3.1',
  value: '6500.00',
  description_fits: true,
};
const CHASE: ExemptionItem = {
  id: 2,
  name: 'JPMorgan Chase',
  line_label: '17.1',
  value: '800.00',
  description_fits: true,
};
const LAWS: ReadonlySet<string> = new Set(['il_735_5_12_1001_b', 'il_735_5_12_1001_c']);

const DONE = { line_1: 'federal', line_3: 'no', line_3_1: null, no_claims: false } as const;

function row(overrides: Partial<ClaimRow> = {}): ClaimRow {
  return {
    _key: 'k1',
    id: 10,
    asset: 1,
    law: 'il_735_5_12_1001_c',
    otherLawChosen: false,
    other_law: '',
    amount_kind: 'dollars',
    amount: '3600',
    short_description: '',
    itemGone: false,
    ...overrides,
  };
}

const gap = (
  answers: Parameters<typeof firstExemptionGap>[0],
  claims: ClaimRow[],
  items: ExemptionItem[] = [CIVIC, CHASE]
) => firstExemptionGap(answers, claims, items, LAWS);

describe('firstExemptionGap', () => {
  it('asks line 1 first, before anything else is missing', () => {
    expect(gap({ ...DONE, line_1: null, line_3: null }, [])).toBe(EXEMPTION_GAP_LINE_1);
  });

  it('asks for a claim or the not-claiming press when there are none', () => {
    expect(gap(DONE, [])).toBe(EXEMPTION_GAP_NO_CLAIMS);
  });

  it('asks only for the press when there is no property to claim', () => {
    expect(gap(DONE, [], [])).toBe(EXEMPTION_GAP_NO_ITEMS);
  });

  it('is satisfied by the not-claiming press alone', () => {
    expect(gap({ ...DONE, no_claims: true }, [])).toBeNull();
  });

  it('says a saved claim whose property left the list is gone', () => {
    expect(gap(DONE, [row({ asset: 99, itemGone: true })])).toBe(EXEMPTION_GAP_ITEM_GONE);
    expect(gap(DONE, [row({ asset: null, itemGone: true })])).toBe(EXEMPTION_GAP_ITEM_GONE);
  });

  it('asks a saved claim whose property the filer cleared to choose one, never calling it gone', () => {
    expect(gap(DONE, [row({ asset: null })])).toBe(EXEMPTION_GAP_CHOOSE_ITEM);
  });

  it('asks a new row to choose its property, never calling it gone', () => {
    expect(gap(DONE, [row({ id: null, asset: null })])).toBe(EXEMPTION_GAP_CHOOSE_ITEM);
    expect(gap(DONE, [row({ id: null, asset: 99 })])).toBe(EXEMPTION_GAP_CHOOSE_ITEM);
  });

  it('asks for a law when none is chosen', () => {
    expect(gap(DONE, [row({ law: null })])).toBe(
      EXEMPTION_GAP_LAW.replace('{name}', 'Honda Civic 2015')
    );
  });

  it('asks for a law when the typed law is blank', () => {
    expect(gap(DONE, [row({ law: null, otherLawChosen: true, other_law: '  ' })])).toBe(
      EXEMPTION_GAP_LAW.replace('{name}', 'Honda Civic 2015')
    );
  });

  it('accepts a typed law', () => {
    expect(
      gap(DONE, [row({ law: null, otherLawChosen: true, other_law: '735 ILCS 5/12-1001(a)' })])
    ).toBeNull();
  });

  it('says so when the chosen law is no longer on the list', () => {
    expect(gap(DONE, [row({ law: 'il_gone' })])).toBe(
      EXEMPTION_GAP_LAW_CHANGED.replace('{name}', 'Honda Civic 2015')
    );
  });

  it('asks for the kind of amount', () => {
    expect(gap(DONE, [row({ amount_kind: null })])).toBe(
      EXEMPTION_GAP_AMOUNT_KIND.replace('{name}', 'Honda Civic 2015')
    );
  });

  it('asks for the dollar figure when dollars has a blank box', () => {
    expect(gap(DONE, [row({ amount: '' })])).toBe(
      EXEMPTION_GAP_AMOUNT.replace('{name}', 'Honda Civic 2015')
    );
  });

  it('needs no figure for fair market value', () => {
    expect(gap(DONE, [row({ amount_kind: 'fair_market_value', amount: '' })])).toBeNull();
  });

  it('asks for a shorter description when the name does not fit', () => {
    const long = { ...CIVIC, description_fits: false };
    expect(gap(DONE, [row()], [long, CHASE])).toBe(
      EXEMPTION_GAP_DESCRIPTION.replace('{name}', 'Honda Civic 2015')
    );
    expect(gap(DONE, [row({ short_description: 'Civic' })], [long, CHASE])).toBeNull();
  });

  it('asks line 3, and line 3-1 under Yes', () => {
    expect(gap({ ...DONE, no_claims: true, line_3: null }, [])).toBe(EXEMPTION_GAP_LINE_3);
    expect(gap({ ...DONE, no_claims: true, line_3: 'yes' }, [])).toBe(EXEMPTION_GAP_LINE_3_1);
    expect(gap({ ...DONE, no_claims: true, line_3: 'yes', line_3_1: 'no' }, [])).toBeNull();
  });

  it('names claims in the order of their properties on the list, not the order added', () => {
    const second = row({ _key: 'a', id: 11, asset: 2, law: null });
    const first = row({ _key: 'b', id: 12, asset: 1, law: null });
    expect(gap(DONE, [second, first])).toBe(
      EXEMPTION_GAP_LAW.replace('{name}', 'Honda Civic 2015')
    );
  });

  it('names two claims on one property in the order they are listed', () => {
    const lawMissing = row({ _key: 'a', id: 11, law: null });
    const kindMissing = row({ _key: 'b', id: 12, amount_kind: null });
    expect(gap(DONE, [lawMissing, kindMissing])).toBe(
      EXEMPTION_GAP_LAW.replace('{name}', 'Honda Civic 2015')
    );
  });

  it('puts an item name in its sentence as typed, symbols and all', () => {
    const odd = { ...CIVIC, name: "Tools $& $' $` more" };
    expect(gap(DONE, [row({ law: null })], [odd, CHASE])).toBe(
      "Choose the law for Tools $& $' $` more."
    );
  });

  it('quotes the not-claiming button in the words the button shows', () => {
    // A filer told to press a button must find a button with those words
    const quoted = `“${EXEMPTIONS_NOT_CLAIMING_BUTTON}.”`;
    expect(EXEMPTION_GAP_NO_CLAIMS).toContain(quoted);
    expect(EXEMPTION_GAP_NO_ITEMS).toContain(quoted);
  });

  it('is null for a finished page', () => {
    expect(gap(DONE, [row(), row({ _key: 'k2', id: 11, asset: 2 })])).toBeNull();
  });
});
