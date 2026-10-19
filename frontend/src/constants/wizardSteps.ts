/**
 * The intake wizard's steps, in order. A refusal names the step that fixes it by its key, and
 * `/intake?step=<key>` opens that step.
 */
export const WIZARD_STEPS = [
  { number: 1, label: 'Your Information', key: 'debtor_info' },
  { number: 2, label: 'Income', key: 'income_info' },
  { number: 3, label: 'Expenses', key: 'expense_info' },
  { number: 4, label: 'Assets', key: 'assets' },
  { number: 5, label: 'Amounts Owed', key: 'debts' },
  { number: 6, label: 'Contracts & Leases', key: 'contracts' },
  { number: 7, label: 'Codebtors', key: 'codebtors' },
  { number: 8, label: 'Review & Results', key: 'review' },
];
