import type { ExpenseInfo } from '../../../../types/api';

// The words migration 0047 stored as the Specify text of a total saved before lines 6a-6c and
// 15a-15b were asked (pinned to the migration by test_expense_frontend_copy.py)
export const LEGACY_TOTAL_WORDS = {
  utilities_specify: 'Utilities (combined)',
  insurance_specify: 'Insurance (combined)',
} as const;

const GROUPS = {
  utilities: {
    words: LEGACY_TOTAL_WORDS.utilities_specify,
    specify: 'utilities_specify',
    other: 'utilities',
    lines: ['electricity_heat_gas', 'water_sewer_garbage', 'phone_internet_cable'],
  },
  insurance: {
    words: LEGACY_TOTAL_WORDS.insurance_specify,
    specify: 'insurance_specify',
    other: 'insurance_not_deducted',
    lines: ['life_insurance', 'health_insurance'],
  },
} as const;

/**
 * Whether a group still holds a total saved before the split: its Specify text is exactly the
 * stored words, its Other amount is above $0 and none of its new lines has an amount. Read from
 * the step's live state, so the first keystroke in the words, or an amount on a new line, ends it.
 */
export function legacyTotalShown(
  data: Partial<ExpenseInfo>,
  group: 'utilities' | 'insurance'
): boolean {
  const g = GROUPS[group];
  return (
    data[g.specify] === g.words &&
    (data[g.other] ?? 0) > 0 &&
    g.lines.every((line) => !((data[line] ?? 0) > 0))
  );
}
