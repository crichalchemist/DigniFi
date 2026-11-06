/**
 * The lines of Schedule A/B, in the form's order: a copy of LINES in the backend's
 * apps/intake/asset_lines.py, pinned by test_asset_lines_frontend_copy.py. A line's words live in
 * formText.ts. A capacity is the form's slots, not a limit: rows past it go on an attached sheet.
 */

export type AssetLineShape =
  | 'place'
  | 'vehicle'
  | 'vehicle_no_mileage'
  | 'item'
  | 'item_question'
  | 'cash'
  | 'named'
  | 'named_share'
  | 'insurance'
  | 'labelled'
  | 'shared_box'
  | 'gate';

export interface AssetLine {
  key: string;
  part: number;
  shape: AssetLineShape;
  capacity: number;
  kinds: readonly (readonly [string, number])[];
  gate: string | null;
}

export const AB_PARTS = [1, 2, 3, 4, 5, 6, 7] as const;

export const ASSET_LINES: readonly AssetLine[] = [
  { key: '1', part: 1, shape: 'place', capacity: 3, kinds: [], gate: null },
  { key: '3', part: 2, shape: 'vehicle', capacity: 4, kinds: [], gate: null },
  { key: '4', part: 2, shape: 'vehicle_no_mileage', capacity: 2, kinds: [], gate: null },
  { key: '6', part: 3, shape: 'item', capacity: 1, kinds: [], gate: null },
  { key: '7', part: 3, shape: 'item', capacity: 1, kinds: [], gate: null },
  { key: '8', part: 3, shape: 'item', capacity: 1, kinds: [], gate: null },
  { key: '9', part: 3, shape: 'item', capacity: 1, kinds: [], gate: null },
  { key: '10', part: 3, shape: 'item', capacity: 1, kinds: [], gate: null },
  { key: '11', part: 3, shape: 'item', capacity: 1, kinds: [], gate: null },
  { key: '12', part: 3, shape: 'item', capacity: 1, kinds: [], gate: null },
  { key: '13', part: 3, shape: 'item', capacity: 1, kinds: [], gate: null },
  { key: '14', part: 3, shape: 'item', capacity: 1, kinds: [], gate: null },
  { key: '16', part: 4, shape: 'cash', capacity: 1, kinds: [], gate: null },
  {
    key: '17',
    part: 4,
    shape: 'labelled',
    capacity: 1,
    kinds: [
      ['checking', 2],
      ['savings', 2],
      ['cd', 1],
      ['other', 4],
    ],
    gate: null,
  },
  { key: '18', part: 4, shape: 'named', capacity: 3, kinds: [], gate: null },
  { key: '19', part: 4, shape: 'named_share', capacity: 3, kinds: [], gate: null },
  { key: '20', part: 4, shape: 'named', capacity: 3, kinds: [], gate: null },
  {
    key: '21',
    part: 4,
    shape: 'labelled',
    capacity: 1,
    kinds: [
      ['401k', 1],
      ['pension', 1],
      ['ira', 1],
      ['retirement', 1],
      ['keogh', 1],
      ['additional', 2],
    ],
    gate: null,
  },
  {
    key: '22',
    part: 4,
    shape: 'labelled',
    capacity: 1,
    kinds: [
      ['electric', 1],
      ['gas', 1],
      ['heating_oil', 1],
      ['security_deposit', 1],
      ['prepaid_rent', 1],
      ['telephone', 1],
      ['water', 1],
      ['rented_furniture', 1],
      ['other', 1],
    ],
    gate: null,
  },
  { key: '23', part: 4, shape: 'named', capacity: 3, kinds: [], gate: null },
  { key: '24', part: 4, shape: 'named', capacity: 3, kinds: [], gate: null },
  { key: '25', part: 4, shape: 'item', capacity: 1, kinds: [], gate: null },
  { key: '26', part: 4, shape: 'item', capacity: 1, kinds: [], gate: null },
  { key: '27', part: 4, shape: 'item', capacity: 1, kinds: [], gate: null },
  {
    key: '28',
    part: 4,
    shape: 'shared_box',
    capacity: 1,
    kinds: [
      ['federal', 1],
      ['state', 1],
      ['local', 1],
    ],
    gate: null,
  },
  {
    key: '29',
    part: 4,
    shape: 'shared_box',
    capacity: 1,
    kinds: [
      ['alimony', 1],
      ['maintenance', 1],
      ['support', 1],
      ['divorce_settlement', 1],
      ['property_settlement', 1],
    ],
    gate: null,
  },
  { key: '30', part: 4, shape: 'item', capacity: 1, kinds: [], gate: null },
  { key: '31', part: 4, shape: 'insurance', capacity: 3, kinds: [], gate: null },
  { key: '32', part: 4, shape: 'item', capacity: 1, kinds: [], gate: null },
  { key: '33', part: 4, shape: 'item', capacity: 1, kinds: [], gate: null },
  { key: '34', part: 4, shape: 'item', capacity: 1, kinds: [], gate: null },
  { key: '35', part: 4, shape: 'item', capacity: 1, kinds: [], gate: null },
  { key: '37', part: 5, shape: 'gate', capacity: 1, kinds: [], gate: null },
  { key: '38', part: 5, shape: 'item', capacity: 1, kinds: [], gate: '37' },
  { key: '39', part: 5, shape: 'item', capacity: 1, kinds: [], gate: '37' },
  { key: '40', part: 5, shape: 'item', capacity: 1, kinds: [], gate: '37' },
  { key: '41', part: 5, shape: 'item', capacity: 1, kinds: [], gate: '37' },
  { key: '42', part: 5, shape: 'named_share', capacity: 3, kinds: [], gate: '37' },
  { key: '43', part: 5, shape: 'item_question', capacity: 1, kinds: [], gate: '37' },
  { key: '44', part: 5, shape: 'named', capacity: 6, kinds: [], gate: '37' },
  { key: '46', part: 6, shape: 'gate', capacity: 1, kinds: [], gate: null },
  { key: '47', part: 6, shape: 'item', capacity: 1, kinds: [], gate: '46' },
  { key: '48', part: 6, shape: 'item', capacity: 1, kinds: [], gate: '46' },
  { key: '49', part: 6, shape: 'item', capacity: 1, kinds: [], gate: '46' },
  { key: '50', part: 6, shape: 'item', capacity: 1, kinds: [], gate: '46' },
  { key: '51', part: 6, shape: 'item', capacity: 1, kinds: [], gate: '46' },
  { key: '53', part: 7, shape: 'shared_box', capacity: 3, kinds: [], gate: null },
];
